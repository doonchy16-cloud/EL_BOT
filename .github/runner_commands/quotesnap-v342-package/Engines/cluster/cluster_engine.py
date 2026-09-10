from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import time

import torch

from Engines.cluster.coordinator import run_remote_round
from Engines.cluster.local_sgd import (
    architecture_hash,
    state_hash,
    train_local_window,
    validate_worker_delta,
)
from Engines.cluster.sharding import split_contiguous_counts, split_contiguous_round
from Engines.cluster.status import write_cluster_status
from Engines.cluster.weights import apply_weighted_delta_set, apply_weighted_deltas, compute_delta
from Engines.trainer.checkpoints.manager import save_checkpoint, sha256_file
from Engines.trainer.core.training_loop import crossed_checkpoint_milestones
from Engines.trainer.core.batch_tuner import auto_tune_training_config, effective_batch_size
from Engines.trainer.telemetry.metrics import write_metrics


@dataclass(frozen=True)
class ParticipantPlan:
    node_id: str
    example_start: int
    example_count: int
    is_coordinator: bool = False


@dataclass(frozen=True)
class RoundPlan:
    round_base: int
    participants: tuple[ParticipantPlan, ...]

    @property
    def total_count(self) -> int:
        return sum(p.example_count for p in self.participants)

    @property
    def coordinator(self) -> ParticipantPlan:
        return self.participants[0]

    @property
    def workers(self) -> tuple[ParticipantPlan, ...]:
        return tuple(p for p in self.participants if not p.is_coordinator)

    # V3.3 compatibility properties used by existing tests/callers.
    @property
    def coordinator_start(self) -> int:
        return self.coordinator.example_start

    @property
    def coordinator_count(self) -> int:
        return self.coordinator.example_count

    @property
    def worker_start(self) -> int:
        return self.workers[0].example_start if self.workers else self.coordinator_start + self.coordinator_count

    @property
    def worker_count(self) -> int:
        return self.workers[0].example_count if self.workers else 0


def allocate_adaptive_step_targets(
    *,
    node_ids: list[str] | tuple[str, ...],
    steps_per_second: dict[str, float],
    base_steps: int,
    min_ratio: float = 0.5,
    max_ratio: float = 2.0,
) -> dict[str, int]:
    nodes = [str(node_id) for node_id in node_ids]
    if not nodes:
        raise ValueError("at least one participant is required")
    if int(base_steps) <= 0:
        raise ValueError("base_steps must be positive")
    speeds = {node: float(steps_per_second.get(node, 0.0)) for node in nodes}
    if any(speed <= 0.0 for speed in speeds.values()):
        return {node: int(base_steps) for node in nodes}

    total_steps = int(base_steps) * len(nodes)
    min_steps = max(1, int(round(int(base_steps) * float(min_ratio))))
    max_steps = max(min_steps, int(round(int(base_steps) * float(max_ratio))))
    if min_steps * len(nodes) > total_steps or max_steps * len(nodes) < total_steps:
        raise ValueError("adaptive bounds cannot satisfy global round budget")

    targets = {node: min_steps for node in nodes}
    order = {node: index for index, node in enumerate(nodes)}
    remaining = total_steps - sum(targets.values())
    while remaining > 0:
        candidates = [node for node in nodes if targets[node] < max_steps]
        if not candidates:
            raise RuntimeError("adaptive allocator exhausted capacity")
        node = min(candidates, key=lambda item: (targets[item] / speeds[item], order[item]))
        targets[node] += 1
        remaining -= 1
    return targets


def plan_round(
    *,
    round_base: int,
    remaining: int,
    per_node_window: int,
    per_node_windows: dict[str, int] | None = None,
    has_worker: bool | None = None,
    worker_node_ids: list[str] | tuple[str, ...] | None = None,
    coordinator_node_id: str = "PRIMARY",
) -> RoundPlan:
    if remaining <= 0:
        raise ValueError("round requires positive remaining examples")
    if per_node_window <= 0:
        raise ValueError("per-node window must be positive")
    if worker_node_ids is None:
        worker_ids = ["WORKER"] if has_worker else []
    else:
        worker_ids = sorted({str(node_id) for node_id in worker_node_ids}, key=lambda value: value.lower())
    node_ids = [str(coordinator_node_id), *worker_ids]
    windows = {str(key).lower(): int(value) for key, value in (per_node_windows or {}).items()}
    counts: list[int] = []
    left = int(remaining)
    for node_id in node_ids:
        window = windows.get(str(node_id).lower(), int(per_node_window))
        if window <= 0:
            raise ValueError("per-node windows must be positive")
        count = min(window, left)
        if count <= 0:
            break
        counts.append(count)
        left -= count
    starts = split_contiguous_counts(int(round_base), counts)
    participants = tuple(
        ParticipantPlan(
            node_id=node_ids[index],
            example_start=starts[index],
            example_count=counts[index],
            is_coordinator=(index == 0),
        )
        for index in range(len(counts))
    )
    return RoundPlan(round_base=int(round_base), participants=participants)


def _cpu_state(model):
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def _restore_scaler(device: str, scaler_state: dict | None):
    if device != "cuda":
        return None
    amp_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    if amp_dtype != torch.float16:
        return None
    scaler = torch.amp.GradScaler("cuda", enabled=True)
    if scaler_state:
        scaler.load_state_dict(scaler_state)
    return scaler


def _canonical_step(control_plane) -> int:
    try:
        snapshot = control_plane.snapshot()
        return int(snapshot.get("canonical_step", 0))
    except Exception:
        canonical = getattr(control_plane, "canonical", None)
        if canonical:
            try:
                return int(canonical[-1][1])
            except Exception:
                pass
        return 0


def _current_sessions(control_plane) -> list:
    if hasattr(control_plane, "current_sessions"):
        sessions = list(control_plane.current_sessions())
    else:
        session = control_plane.current_session()
        sessions = [session] if session is not None else []
    sessions = [session for session in sessions if session is not None]
    sessions.sort(key=lambda session: str(getattr(session, "node_id", getattr(session, "hostname", ""))).lower())
    return sessions


def _status(
    path,
    *,
    control_plane,
    control_state: str,
    round_id: str,
    fallback: bool,
    last_merge: str,
    coordinator_assigned_steps: int = 0,
    coordinator_local_step: int = 0,
    coordinator_steps_per_second: float = 0.0,
    round_total_steps: int = 0,
    round_total_examples: int = 0,
    adaptive_round_balancing: bool = False,
    error: str = "",
):
    try:
        control_snapshot = control_plane.snapshot()
    except Exception:
        control_snapshot = {}
    workers = list(control_snapshot.get("workers", []))
    canonical_step = _canonical_step(control_plane)
    sync = dict(control_snapshot.get("cluster_sync", {}) or {})
    if workers:
        sync["round_match"] = all(str(worker.get("round", "-")) == str(round_id) for worker in workers)
        sync["canonical_match"] = all(int(worker.get("canonical_step", -1)) == int(canonical_step) for worker in workers)
    else:
        sync["round_match"] = False
        sync["canonical_match"] = False
    base_ok = all(bool(sync.get(key, False)) for key in (
        "worker_count_match", "sessions_unique", "epoch_match", "cluster_match", "software_match", "heartbeats_fresh"
    ))
    sync["status"] = "VERIFIED" if base_ok and sync["round_match"] and sync["canonical_match"] and not fallback else (
        "WAITING" if len(workers) < int(control_snapshot.get("expected_worker_count", 0) or 0) else "DEGRADED"
    )
    transports = sorted({str(worker.get("transport", "UNKNOWN")) for worker in workers})
    transport_summary = transports[0] if len(transports) == 1 else ("MIXED" if transports else "LOCAL")
    cluster_speed = max(0.0, float(coordinator_steps_per_second or 0.0)) + sum(
        max(0.0, float(worker.get("steps_per_second", 0.0) or 0.0)) for worker in workers
    )
    write_cluster_status(
        path,
        role="COORDINATOR",
        control_state=control_state,
        cluster_id=str(control_snapshot.get("cluster_id", getattr(control_plane, "cluster_id", ""))),
        coordinator_hostname=str(control_snapshot.get("coordinator_hostname", getattr(control_plane, "hostname", "-"))),
        coordinator_instance_id=str(control_snapshot.get("coordinator_instance_id", getattr(control_plane, "coordinator_instance_id", "-"))),
        software_version=str(control_snapshot.get("software_version", getattr(control_plane, "software_version", ""))),
        expected_worker_count=int(control_snapshot.get("expected_worker_count", 0) or 0),
        transport_summary=transport_summary,
        epoch=int(getattr(control_plane, "epoch", 0)),
        canonical_step=canonical_step,
        round=round_id,
        fallback=bool(fallback),
        last_merge=last_merge,
        workers=workers,
        coordinator={
            "hostname": str(getattr(control_plane, "hostname", "COORDINATOR")),
            "assigned_steps": int(coordinator_assigned_steps or 0),
            "local_window_step": int(coordinator_local_step or 0),
            "steps_per_second": round(float(coordinator_steps_per_second or 0.0), 4),
        },
        round_total_steps=int(round_total_steps or 0),
        round_total_examples=int(round_total_examples or 0),
        adaptive_round_balancing=bool(adaptive_round_balancing),
        cluster_steps_per_second=round(cluster_speed, 4),
        cluster_sync=sync,
        error=str(error)[:240] if error else "",
    )


def _cluster_metadata(
    *,
    control_plane,
    round_id: str,
    parent_hash: str,
    participants: list[str],
    merge_strategy: str,
    coordinator_examples: int,
    worker_examples: int,
    cluster_cfg: dict,
    worker_examples_by_node: dict[str, int] | None = None,
    failed_workers: list[str] | None = None,
    committed_examples: int | None = None,
    error: str = "",
) -> dict:
    worker_examples_by_node = dict(worker_examples_by_node or {})
    failed_workers = list(failed_workers or [])
    if committed_examples is None:
        committed_examples = int(coordinator_examples) + int(worker_examples)
    return {
        "cluster_id": str(getattr(control_plane, "cluster_id", cluster_cfg.get("cluster_id", ""))),
        "epoch": int(getattr(control_plane, "epoch", 0)),
        "round_id": str(round_id),
        "parent_sha256": str(parent_hash),
        "participants": list(participants),
        "merge_strategy": str(merge_strategy),
        "coordinator_examples": int(coordinator_examples),
        "worker_examples": int(worker_examples),
        "worker_examples_by_node": worker_examples_by_node,
        "failed_workers": failed_workers,
        "committed_examples": int(committed_examples),
        "software_version": str(cluster_cfg.get("software_version", "3.3.0")),
        "error": str(error)[:240] if error else "",
    }

def run_cluster_stage(
    *,
    model,
    optimizer,
    scaler_state,
    model_cfg,
    stage,
    stage_target_examples,
    start_stage_step,
    start_stage_examples,
    start_global_examples,
    training_cfg,
    stage_cfg,
    output_dir,
    metrics_path,
    cluster_status_path,
    device,
    cluster_cfg,
    control_plane,
):
    local_training_cfg, batch_tune_report = auto_tune_training_config(
        model, training_cfg, device
    )
    effective = effective_batch_size(training_cfg)
    if effective_batch_size(local_training_cfg) != effective:
        raise RuntimeError("local batch autotune changed effective batch contract")
    print(
        "batch_autotune role=COORDINATOR "
        f"micro={local_training_cfg['micro_batch_size']} "
        f"accum={local_training_cfg['gradient_accumulation_steps']} "
        f"effective={effective} fallback={str(bool(batch_tune_report.get('fallback', False))).lower()}",
        flush=True,
    )
    window_steps = int(cluster_cfg["sync_window_steps"])
    per_node_window = effective * window_steps
    stage_step = int(start_stage_step)
    stage_examples = int(start_stage_examples)
    global_examples = int(start_global_examples)
    arch_hash = architecture_hash(model_cfg)
    round_num = 0
    last_checkpoint = None
    last_checkpoint_hash = ""
    last_saved_step = None
    satisfied_checkpoint_milestones: set[int] = set()
    scaler = _restore_scaler(device, scaler_state)
    last_provenance = None
    coordinator_name = str(getattr(control_plane, "hostname", "COORDINATOR"))
    coordinator_steps_per_second = 0.0

    control_plane.update_canonical(
        stage=stage, step=stage_step, checkpoint_hash=last_checkpoint_hash
    )

    while stage_examples < stage_target_examples:
        round_num += 1
        remaining = stage_target_examples - stage_examples
        sessions = _current_sessions(control_plane)
        session_by_node = {
            str(getattr(session, "node_id", getattr(session, "hostname", ""))).lower(): session
            for session in sessions
        }
        participant_node_ids = [coordinator_name, *sorted(session_by_node)]
        per_node_windows = None
        if bool(cluster_cfg.get("adaptive_round_balancing", False)) and session_by_node:
            speed_map = {coordinator_name: float(coordinator_steps_per_second)}
            speed_map.update(
                {
                    node_id: float(getattr(worker_session, "remote_steps_per_second", 0.0))
                    for node_id, worker_session in session_by_node.items()
                }
            )
            step_targets = allocate_adaptive_step_targets(
                node_ids=participant_node_ids,
                steps_per_second=speed_map,
                base_steps=window_steps,
                min_ratio=float(cluster_cfg.get("adaptive_min_window_ratio", 0.5)),
                max_ratio=float(cluster_cfg.get("adaptive_max_window_ratio", 2.0)),
            )
            per_node_windows = {
                node_id: int(step_count) * effective
                for node_id, step_count in step_targets.items()
            }
        plan = plan_round(
            round_base=stage_examples,
            remaining=remaining,
            per_node_window=per_node_window,
            per_node_windows=per_node_windows,
            worker_node_ids=list(session_by_node),
            coordinator_node_id=coordinator_name,
        )
        assigned_sessions = [
            session_by_node[participant.node_id.lower()]
            for participant in plan.workers
            if participant.node_id.lower() in session_by_node
        ]
        round_id = f"{stage}-{stage_step:09d}-{round_num:06d}"
        round_total_examples = int(plan.total_count)
        round_total_steps = max(1, (round_total_examples + effective - 1) // effective)
        coordinator_assigned_steps = max(1, (int(plan.coordinator_count) + effective - 1) // effective)
        worker_plans = {participant.node_id.lower(): participant for participant in plan.workers}
        for worker_session in assigned_sessions:
            key = str(getattr(worker_session, "node_id", worker_session.hostname)).lower()
            worker_plan = worker_plans[key]
            worker_session.assigned_examples = int(worker_plan.example_count)
            worker_session.assigned_steps = max(1, (int(worker_plan.example_count) + effective - 1) // effective)
            worker_session.round_total_examples = round_total_examples
            worker_session.round_total_steps = round_total_steps
            worker_session.canonical_step = int(stage_step)
            worker_session.active_round_id = str(round_id)
        parent_state = _cpu_state(model)
        parent_hash = state_hash(parent_state)
        started = time.monotonic()

        def local_progress(local_step, consumed, loss):
            elapsed = max(1e-9, time.monotonic() - started)
            write_metrics(
                metrics_path,
                {
                    "status": "TRAINING",
                    "stage": stage,
                    # Canonical progress advances only after a validated round commit.
                    "stage_step": stage_step,
                    "stage_examples": stage_examples,
                    "stage_target_examples": stage_target_examples,
                    "global_examples": global_examples,
                    "loss": round(loss, 6),
                    "steps_per_second": round(local_step / elapsed, 6),
                    "local_window_step": int(local_step),
                    "local_window_examples": int(consumed),
                    "local_window_target_examples": int(plan.coordinator_count),
                    "micro_batch_size": int(local_training_cfg["micro_batch_size"]),
                    "gradient_accumulation_steps": int(
                        local_training_cfg["gradient_accumulation_steps"]
                    ),
                    "effective_batch": effective,
                    "device": device,
                },
            )
            if assigned_sessions and local_step % max(1, int(cluster_cfg.get("heartbeat_steps", 10))) == 0:
                _status(
                    cluster_status_path,
                    control_plane=control_plane,
                    control_state="ROUND_TRAINING",
                    round_id=round_id,
                    fallback=False,
                    last_merge="-",
                    coordinator_assigned_steps=coordinator_assigned_steps,
                    coordinator_local_step=int(local_step),
                    coordinator_steps_per_second=float(local_step / elapsed),
                    round_total_steps=round_total_steps,
                    round_total_examples=round_total_examples,
                    adaptive_round_balancing=bool(cluster_cfg.get("adaptive_round_balancing", False)),
                )

        if assigned_sessions and plan.workers:
            _status(
                cluster_status_path,
                control_plane=control_plane,
                control_state="ROUND_TRAINING",
                round_id=round_id,
                fallback=False,
                last_merge="-",
                coordinator_assigned_steps=coordinator_assigned_steps,
                coordinator_local_step=0,
                coordinator_steps_per_second=coordinator_steps_per_second,
                round_total_steps=round_total_steps,
                round_total_examples=round_total_examples,
                adaptive_round_balancing=bool(cluster_cfg.get("adaptive_round_balancing", False)),
            )
            pool = ThreadPoolExecutor(max_workers=len(assigned_sessions))
            futures = {}
            for worker_session in assigned_sessions:
                key = str(getattr(worker_session, "node_id", worker_session.hostname)).lower()
                worker_plan = worker_plans[key]
                futures[key] = pool.submit(
                    run_remote_round,
                    worker_session,
                    cluster_id=str(cluster_cfg["cluster_id"]),
                    round_id=round_id,
                    stage=stage,
                    canonical_step=stage_step,
                    canonical_examples=stage_examples,
                    global_examples=global_examples,
                    stage_target_examples=stage_target_examples,
                    round_total_steps=round_total_steps,
                    round_total_examples=round_total_examples,
                    example_start=worker_plan.example_start,
                    local_examples=worker_plan.example_count,
                    parent_state=parent_state,
                    model_cfg=model_cfg,
                    training_cfg=training_cfg,
                    stage_cfg=stage_cfg,
                    round_timeout_seconds=float(cluster_cfg["round_timeout_seconds"]),
                )
            try:
                local_started = time.monotonic()
                local = train_local_window(
                    model,
                    stage=stage,
                    example_start=plan.coordinator_start,
                    local_examples=plan.coordinator_count,
                    model_cfg=model_cfg,
                    training_cfg=local_training_cfg,
                    stage_cfg=stage_cfg,
                    device=device,
                    optimizer=optimizer,
                    scaler=scaler,
                    progress_cb=local_progress,
                )
                local_elapsed = max(1e-9, time.monotonic() - local_started)
                coordinator_steps_per_second = float(local.get("steps", 0)) / local_elapsed
                optimizer = local["optimizer"]
                scaler = local["scaler"]
                local_state = local["state"]
                local_delta = compute_delta(parent_state, local_state)

                successful = {}
                failed_workers = []
                errors = []
                for participant in plan.workers:
                    key = participant.node_id.lower()
                    worker_session = session_by_node[key]
                    future = futures[key]
                    try:
                        meta, remote_delta = future.result(
                            timeout=float(cluster_cfg["round_timeout_seconds"]) + 1.0
                        )
                        validate_worker_delta(
                            meta,
                            expected_round_id=round_id,
                            expected_parent_hash=parent_hash,
                            expected_architecture_hash=arch_hash,
                            expected_cluster_id=str(cluster_cfg["cluster_id"]),
                            expected_epoch=worker_session.epoch,
                            expected_session_id=worker_session.session_id,
                            remote_delta=remote_delta,
                            parent_state=parent_state,
                            max_delta_norm_factor=float(
                                cluster_cfg.get("max_worker_delta_norm_factor", 100.0)
                            ),
                        )
                        successful[key] = (worker_session, participant, remote_delta)
                    except Exception as exc:
                        failed_workers.append(participant.node_id)
                        errors.append(f"{participant.node_id}: {exc}")
                        try:
                            control_plane.invalidate(worker_session, str(exc))
                        except Exception:
                            pass

                # Canonical accounting is contiguous. Commit only the successful
                # worker prefix after the coordinator. A later worker result after
                # a failed earlier range is intentionally discarded so the next
                # round can safely resume at the first uncommitted example.
                committed_workers = []
                for participant in plan.workers:
                    key = participant.node_id.lower()
                    if key not in successful:
                        break
                    committed_workers.append(successful[key])

                deltas = [local_delta]
                counts = [plan.coordinator_count]
                participants = [coordinator_name]
                worker_examples_by_node = {}
                for worker_session, participant, remote_delta in committed_workers:
                    deltas.append(remote_delta)
                    counts.append(participant.example_count)
                    participants.append(worker_session.hostname)
                    worker_examples_by_node[participant.node_id.lower()] = participant.example_count

                merged = apply_weighted_delta_set(parent_state, deltas, counts)
                model.load_state_dict(merged, strict=True)
                model.to(device)
                used = sum(counts)
                worker_used = used - plan.coordinator_count
                merge_strategy = "weighted_delta_average" if worker_used else "local_only"
                error = "; ".join(errors)
                last_merge = time.strftime("%H:%M:%S") if worker_used else "-"
                _status(
                    cluster_status_path,
                    control_plane=control_plane,
                    control_state=("READY" if worker_used else "DEGRADED_WAITING_FOR_WORKER"),
                    round_id=round_id,
                    fallback=(worker_used == 0),
                    last_merge=last_merge,
                    coordinator_assigned_steps=coordinator_assigned_steps,
                    coordinator_local_step=coordinator_assigned_steps,
                    coordinator_steps_per_second=coordinator_steps_per_second,
                    round_total_steps=round_total_steps,
                    round_total_examples=round_total_examples,
                    adaptive_round_balancing=bool(cluster_cfg.get("adaptive_round_balancing", False)),
                    error=error,
                )
            except Exception:
                for worker_session in assigned_sessions:
                    try:
                        control_plane.invalidate(worker_session, "coordinator local round failed")
                    except Exception:
                        pass
                raise
            finally:
                for key, future in futures.items():
                    if not future.done():
                        worker_session = session_by_node[key]
                        try:
                            control_plane.invalidate(worker_session, "remote round cancellation")
                        except Exception:
                            pass
                        future.cancel()
                pool.shutdown(wait=True, cancel_futures=True)
        else:
            _status(
                cluster_status_path,
                control_plane=control_plane,
                control_state="WAITING_FOR_WORKER",
                round_id=round_id,
                fallback=True,
                last_merge="-",
                coordinator_assigned_steps=coordinator_assigned_steps,
                coordinator_local_step=0,
                coordinator_steps_per_second=coordinator_steps_per_second,
                round_total_steps=round_total_steps,
                round_total_examples=round_total_examples,
                adaptive_round_balancing=bool(cluster_cfg.get("adaptive_round_balancing", False)),
            )
            local_started = time.monotonic()
            local = train_local_window(
                model,
                stage=stage,
                example_start=plan.coordinator_start,
                local_examples=plan.coordinator_count,
                model_cfg=model_cfg,
                training_cfg=local_training_cfg,
                stage_cfg=stage_cfg,
                device=device,
                optimizer=optimizer,
                scaler=scaler,
                progress_cb=local_progress,
            )
            local_elapsed = max(1e-9, time.monotonic() - local_started)
            coordinator_steps_per_second = float(local.get("steps", 0)) / local_elapsed
            optimizer = local["optimizer"]
            scaler = local["scaler"]
            model.load_state_dict(local["state"], strict=True)
            model.to(device)
            used = plan.coordinator_count
            worker_used = 0
            worker_examples_by_node = {}
            failed_workers = []
            merge_strategy = "local_only"
            participants = [coordinator_name]
            error = ""

        previous_stage_step = stage_step
        stage_step += max(1, (used + effective - 1) // effective)
        stage_examples += used
        global_examples += used
        last_provenance = _cluster_metadata(
            control_plane=control_plane,
            round_id=round_id,
            parent_hash=parent_hash,
            participants=participants,
            merge_strategy=merge_strategy,
            coordinator_examples=plan.coordinator_count,
            worker_examples=worker_used,
            worker_examples_by_node=worker_examples_by_node,
            failed_workers=failed_workers,
            committed_examples=used,
            cluster_cfg=cluster_cfg,
            error=error,
        )
        control_plane.update_canonical(
            stage=stage, step=stage_step, checkpoint_hash=last_checkpoint_hash
        )
        # Publish the committed canonical counters separately from in-window work.
        write_metrics(
            metrics_path,
            {
                "status": "TRAINING",
                "stage": stage,
                "stage_step": stage_step,
                "stage_examples": stage_examples,
                "stage_target_examples": stage_target_examples,
                "global_examples": global_examples,
                "loss": round(float(local.get("loss", 0.0)), 6),
                "steps_per_second": round(
                    float(local.get("steps", 0)) / max(1e-9, time.monotonic() - started),
                    6,
                ),
                "local_window_step": 0,
                "local_window_examples": 0,
                "local_window_target_examples": 0,
                "micro_batch_size": int(local_training_cfg["micro_batch_size"]),
                "gradient_accumulation_steps": int(
                    local_training_cfg["gradient_accumulation_steps"]
                ),
                "effective_batch": effective,
                "device": device,
            },
        )

        crossed_milestones = crossed_checkpoint_milestones(
            previous_stage_step,
            stage_step,
            int(training_cfg["save_every_steps"]),
            satisfied_checkpoint_milestones,
        )
        if crossed_milestones:
            last_checkpoint = save_checkpoint(
                model,
                optimizer,
                model_cfg,
                stage,
                stage_step,
                stage_examples,
                global_examples,
                Path(output_dir),
                int(training_cfg["max_checkpoint_retries"]),
                scaler=scaler,
                extra_metadata={
                    "cluster": last_provenance,
                    "checkpoint_milestones_crossed": crossed_milestones,
                },
            )
            last_saved_step = stage_step
            satisfied_checkpoint_milestones.update(crossed_milestones)
            last_checkpoint_hash = sha256_file(last_checkpoint)
            control_plane.update_canonical(
                stage=stage, step=stage_step, checkpoint_hash=last_checkpoint_hash
            )

    if last_provenance is None:
        last_provenance = _cluster_metadata(
            control_plane=control_plane,
            round_id=f"{stage}-{stage_step:09d}-FINAL",
            parent_hash=state_hash(_cpu_state(model)),
            participants=[coordinator_name],
            merge_strategy="local_only",
            coordinator_examples=0,
            worker_examples=0,
            cluster_cfg=cluster_cfg,
        )
    if last_checkpoint is None or last_saved_step != stage_step:
        last_checkpoint = save_checkpoint(
            model,
            optimizer,
            model_cfg,
            stage,
            stage_step,
            stage_examples,
            global_examples,
            Path(output_dir),
            int(training_cfg["max_checkpoint_retries"]),
            scaler=scaler,
            extra_metadata={"cluster": last_provenance},
        )
        last_checkpoint_hash = sha256_file(last_checkpoint)
        control_plane.update_canonical(
            stage=stage, step=stage_step, checkpoint_hash=last_checkpoint_hash
        )
    return last_checkpoint
