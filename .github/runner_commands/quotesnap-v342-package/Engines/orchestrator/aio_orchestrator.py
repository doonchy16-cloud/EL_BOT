from __future__ import annotations

from pathlib import Path
import argparse
import json
import socket
import sys

import torch
from torch.optim import AdamW

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Engines.cluster.control_plane import CoordinatorControlPlane
from Engines.cluster.discovery import canonical_hostname, hostname_matches, resolve_authoritative_role
from Engines.cluster.identity import resolve_local_node_identity
from Engines.cluster.status import write_cluster_status
from Engines.cluster.root_ownership import ensure_root_ownership
from Engines.cluster.worker import worker_service
from Engines.cluster.cluster_engine import run_cluster_stage
from Engines.continual.core.continual_engine import run_continual
from Engines.continual.evaluation.gate import EvalResult, should_promote
from Engines.continual.lineage.store import LineageStore
from Engines.orchestrator.state_machine import STAGE_ORDER, detect_stage
from Engines.trainer.checkpoints.manager import latest_checkpoint, sha256_file, verify_checkpoint
from Engines.trainer.core.base_engine import run_base
from Engines.trainer.core.model import build_model_from_config, count_params
from Engines.trainer.evaluation.evaluator import evaluate_loss, score_from_loss

CONFIG = ROOT / "Config"
STATE = ROOT / "State"
CHECKPOINTS = ROOT / "Checkpoints"
METRICS = STATE / "training_metrics.json"
CLUSTER_STATUS = STATE / "cluster_status.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def checkpoint_dir(stage):
    return CHECKPOINTS / stage.lower()


def discover_stage_status(stages_cfg):
    status = {}
    for stage in STAGE_ORDER:
        latest = latest_checkpoint(checkpoint_dir(stage))
        if latest:
            _, path, data = latest
            status[stage] = {
                "completed_examples": int(data.get("stage_examples", 0)),
                "stage_step": int(data.get("stage_step", 0)),
                "checkpoint": str(path),
                "global_examples": int(data.get("global_examples", 0)),
            }
        else:
            status[stage] = {
                "completed_examples": 0,
                "stage_step": 0,
                "checkpoint": None,
                "global_examples": 0,
            }
    return status


def latest_prior_checkpoint(stage_status, current_stage):
    idx = STAGE_ORDER.index(current_stage)
    for previous in reversed(STAGE_ORDER[:idx]):
        p = stage_status[previous].get("checkpoint")
        if p:
            return Path(p)
    return None


def construct_or_resume(stage, model_cfg, stage_status):
    current = stage_status[stage]
    current_path = current.get("checkpoint")
    if current_path:
        data = verify_checkpoint(Path(current_path), model_cfg)
        model = build_model_from_config(model_cfg)
        model.load_state_dict(data["model"], strict=True)
        return model, data.get("optimizer"), data.get("scaler"), data
    parent_path = latest_prior_checkpoint(stage_status, stage)
    model = build_model_from_config(model_cfg)
    meta = {"stage_step": 0, "stage_examples": 0, "global_examples": 0}
    if parent_path:
        parent = verify_checkpoint(parent_path, model_cfg)
        model.load_state_dict(parent["model"], strict=True)
        meta["global_examples"] = int(parent.get("global_examples", 0))
    return model, None, None, meta


def resolve_cluster_role(cluster_cfg, *, hostname: str | None = None) -> str:
    if not cluster_cfg.get("enabled", True):
        return "coordinator"
    if hostname is None:
        identity = resolve_local_node_identity(cluster_cfg.get("preferred_coordinator_hostname"))
        hostname = identity.hostname
    return resolve_authoritative_role(
        cluster_cfg.get("role", "auto"),
        hostname,
        cluster_cfg.get("preferred_coordinator_hostname"),
    )


def self_test():
    model_cfg = load_json(CONFIG / "model.json")
    training_cfg = load_json(CONFIG / "training.json")
    stages_cfg = load_json(CONFIG / "stages.json")
    aio_cfg = load_json(CONFIG / "aio.json")
    cluster_cfg = load_json(CONFIG / "cluster.json")
    model = build_model_from_config(model_cfg)
    params = count_params(model)
    if params != int(aio_cfg["expected_parameters"]):
        raise RuntimeError(f"parameter count mismatch: {params}")
    if int(training_cfg["micro_batch_size"]) <= 0:
        raise RuntimeError("invalid micro batch")
    for stage in STAGE_ORDER:
        if stage not in stages_cfg["stages"]:
            raise RuntimeError(f"missing stage config: {stage}")
    if int(cluster_cfg["sync_window_steps"]) <= 0:
        raise RuntimeError("invalid cluster sync window")
    if int(cluster_cfg["max_payload_bytes"]) < 16 * 1024 * 1024:
        raise RuntimeError("cluster payload ceiling too small")
    if cluster_cfg.get("wire_parent_dtype") != "float32":
        raise RuntimeError("V3.4 canonical parent wire must be float32")
    if cluster_cfg.get("wire_update_dtype") != "float16":
        raise RuntimeError("V3.4 worker update wire must be float16")
    if (cluster_cfg.get("role") or "auto").lower() == "auto" and not cluster_cfg.get(
        "preferred_coordinator_hostname"
    ):
        raise RuntimeError("V3.4 auto role requires preferred coordinator hostname")
    print(
        f"V3_4_AIO_PYTHON_SELFTEST_PASS parameters={params} "
        f"cluster_window={cluster_cfg['sync_window_steps']}",
        flush=True,
    )
    return 0


def _evaluate_and_promote(
    final_path, model, model_cfg, training_cfg, stage, stage_cfg, device, lineage
):
    final_data = verify_checkpoint(final_path, model_cfg)
    model.load_state_dict(final_data["model"], strict=True)
    model.to(device)
    validation_loss = evaluate_loss(
        model=model,
        stage=stage,
        vocab_size=model_cfg["vocab_size"],
        seq_len=min(128, model_cfg["max_seq_len"]),
        device=device,
        count=int(training_cfg["eval_examples"]),
        seed=int(training_cfg["seed"]),
    )
    score = score_from_loss(validation_loss)
    candidate = EvalResult(validation_loss, score, score, False)
    parent_node = lineage.best()
    parent_eval = None
    parent_sha = None
    if parent_node:
        parent_sha = parent_node["sha256"]
        parent_eval = EvalResult(
            parent_node["validation_loss"],
            parent_node["policy_score"],
            parent_node["benchmark_score"],
            False,
        )
    promote = should_promote(parent_eval, candidate)
    lineage.register(
        checkpoint=final_path,
        stage=stage,
        parent_sha256=parent_sha,
        dataset_version=stage_cfg["dataset_version"],
        validation_loss=validation_loss,
        policy_score=score,
        benchmark_score=score,
        promotion_state="BEST" if promote else "REJECTED",
    )
    if not promote:
        print(f"aio_status=HOLD stage={stage} candidate failed promotion gate", flush=True)
        return False
    print(f"aio_promoted stage={stage} validation_loss={validation_loss:.6f}", flush=True)
    return True


def _send_worker_stop(control_plane, cluster_cfg):
    if control_plane is None:
        return
    if hasattr(control_plane, "current_sessions"):
        sessions = list(control_plane.current_sessions())
    else:
        session = control_plane.current_session()
        sessions = [session] if session else []
    for session in sessions:
        try:
            session.send(
                {
                    "type": "STOP",
                    "cluster_id": cluster_cfg["cluster_id"],
                    "epoch": int(session.epoch),
                    "session_id": session.session_id,
                }
            )
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--single-stage", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    model_cfg = load_json(CONFIG / "model.json")
    training_cfg = load_json(CONFIG / "training.json")
    stages_cfg = load_json(CONFIG / "stages.json")
    aio_cfg = load_json(CONFIG / "aio.json")
    cluster_cfg = load_json(CONFIG / "cluster.json")
    expected_params = int(aio_cfg["expected_parameters"])

    torch.manual_seed(int(training_cfg["seed"]))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device != "cuda":
        raise RuntimeError("CUDA is required for V3.4 AIO training")

    preferred_hostname = str(cluster_cfg.get("preferred_coordinator_hostname") or "")
    identity = resolve_local_node_identity(preferred_hostname)
    ensure_root_ownership(ROOT, node_id=identity.node_id, hostname=identity.hostname)
    local_hostname = identity.hostname
    role = resolve_cluster_role(cluster_cfg, hostname=local_hostname)
    authority_match = bool(identity.authority_match)
    print(
        "cluster_identity "
        f"observed={local_hostname} "
        f"observed_key={canonical_hostname(local_hostname)} "
        f"configured_primary={preferred_hostname} "
        f"configured_key={canonical_hostname(preferred_hostname)} "
        f"authority_match={str(authority_match).lower()} "
        f"resolved_role={role.upper()}",
        flush=True,
    )
    if role == "worker":
        write_cluster_status(
            CLUSTER_STATUS,
            role="WORKER",
            control_state="DISCOVERING",
            cluster_id=str(cluster_cfg.get("cluster_id", "")),
            coordinator_hostname=preferred_hostname,
            coordinator_instance_id="-",
            worker_session_id="-",
            peer="none",
            transport="DISCONNECTED",
            round="-",
            fallback=False,
            last_merge="-",
            local_hostname=identity.hostname,
            node_id=identity.node_id,
            configured_primary=preferred_hostname,
            authority_match=authority_match,
            expected_role="WORKER",
        )
        print("cluster_role=WORKER authority=preferred_primary", flush=True)
        return worker_service(
            cluster_cfg,
            model_cfg,
            aio_cfg["version"],
            device,
            status_path=CLUSTER_STATUS,
            metrics_path=METRICS,
            hostname=identity.hostname,
        )

    control_plane = None
    if cluster_cfg.get("enabled", True):
        control_plane = CoordinatorControlPlane(
            cluster_cfg, model_cfg, aio_cfg["version"], STATE, hostname=identity.hostname
        )
        control_plane.start()
        snap = control_plane.snapshot()
        write_cluster_status(
            CLUSTER_STATUS,
            role="COORDINATOR",
            control_state="WAITING_FOR_WORKER",
            cluster_id=str(snap.get("cluster_id", cluster_cfg.get("cluster_id", ""))),
            coordinator_hostname=identity.hostname,
            coordinator_instance_id=str(snap.get("coordinator_instance_id", "-")),
            software_version=str(aio_cfg.get("version", "3.4.2")),
            expected_worker_count=int(cluster_cfg.get("expected_worker_count", 2)),
            transport_summary="LOCAL",
            epoch=snap["epoch"],
            round="-",
            fallback=True,
            last_merge="-",
            workers=[],
            coordinator={"hostname": identity.hostname, "assigned_steps": 0, "local_window_step": 0, "steps_per_second": 0.0},
            round_total_steps=0,
            round_total_examples=0,
            adaptive_round_balancing=bool(cluster_cfg.get("adaptive_round_balancing", False)),
            cluster_steps_per_second=0.0,
            cluster_sync=dict(snap.get("cluster_sync", {}) or {}),
            canonical_step=int(snap.get("canonical_step", 0)),
            local_hostname=identity.hostname,
            node_id=identity.node_id,
            configured_primary=preferred_hostname,
            authority_match=authority_match,
            expected_role="COORDINATOR",
        )
        print(
            f"cluster_role=COORDINATOR authority=preferred_primary "
            f"epoch={snap['epoch']} port={snap['tcp_port']}",
            flush=True,
        )

    lineage = LineageStore(STATE / "lineage.json")
    try:
        while True:
            stage_status = discover_stage_status(stages_cfg)
            stage = detect_stage(stage_status, stages_cfg)
            if stage is None:
                print("aio_status=COMPLETE all stages finished", flush=True)
                _send_worker_stop(control_plane, cluster_cfg)
                return 0

            model, optimizer_state, scaler_state, meta = construct_or_resume(
                stage, model_cfg, stage_status
            )
            if count_params(model) != expected_params:
                raise RuntimeError("loaded model parameter count mismatch")
            model.to(device)
            stage_cfg = stages_cfg["stages"][stage]
            stage_target = int(stage_cfg["target_examples"])
            stage_step = int(meta.get("stage_step", 0))
            stage_examples = int(meta.get("stage_examples", 0))
            global_examples = int(meta.get("global_examples", 0))
            print(
                f"aio_stage={stage} resume_step={stage_step} "
                f"stage_examples={stage_examples}/{stage_target}",
                flush=True,
            )

            optimizer = AdamW(
                model.parameters(),
                lr=float(stage_cfg["learning_rate"]),
                weight_decay=float(stage_cfg["weight_decay"]),
            )
            if optimizer_state:
                optimizer.load_state_dict(optimizer_state)

            if control_plane is not None:
                checkpoint_path = stage_status[stage].get("checkpoint")
                checkpoint_hash = (
                    sha256_file(Path(checkpoint_path)) if checkpoint_path else ""
                )
                control_plane.update_canonical(
                    stage=stage, step=stage_step, checkpoint_hash=checkpoint_hash
                )
                final_path = run_cluster_stage(
                    model=model,
                    optimizer=optimizer,
                    scaler_state=scaler_state,
                    model_cfg=model_cfg,
                    stage=stage,
                    stage_target_examples=stage_target,
                    start_stage_step=stage_step,
                    start_stage_examples=stage_examples,
                    start_global_examples=global_examples,
                    training_cfg=training_cfg,
                    stage_cfg=stage_cfg,
                    output_dir=checkpoint_dir(stage),
                    metrics_path=METRICS,
                    cluster_status_path=CLUSTER_STATUS,
                    device=device,
                    cluster_cfg=cluster_cfg,
                    control_plane=control_plane,
                )
            else:
                kwargs = dict(
                    model=model,
                    optimizer=optimizer,
                    model_cfg=model_cfg,
                    stage_target_examples=stage_target,
                    start_stage_step=stage_step,
                    start_stage_examples=stage_examples,
                    start_global_examples=global_examples,
                    training_cfg=training_cfg,
                    stage_cfg=stage_cfg,
                    output_dir=checkpoint_dir(stage),
                    metrics_path=METRICS,
                    device=device,
                )
                final_path = (
                    run_base(**kwargs)
                    if stage == "BASE"
                    else run_continual(stage=stage, **kwargs)
                )

            if not _evaluate_and_promote(
                final_path,
                model,
                model_cfg,
                training_cfg,
                stage,
                stage_cfg,
                device,
                lineage,
            ):
                return 3
            if args.single_stage or not stages_cfg.get("auto_advance", True):
                _send_worker_stop(control_plane, cluster_cfg)
                return 0
    finally:
        if control_plane is not None:
            control_plane.stop()


if __name__ == "__main__":
    raise SystemExit(main())
