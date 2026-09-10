from __future__ import annotations

from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

from torch.optim import AdamW

from Engines.cluster.discovery import canonical_hostname, classify_transport, collect_peer_candidates, hostname_matches, listen_for_beacons
from Engines.cluster.local_sgd import architecture_hash, state_hash, train_local_window
from Engines.cluster.protocol import ProtocolError, recv_frame, send_frame
from Engines.cluster.status import write_cluster_status
from Engines.cluster.weights import compute_delta, decode_model_state, encode_model_state
from Engines.trainer.core.model import build_model_from_config
from Engines.trainer.core.batch_tuner import auto_tune_training_config, effective_batch_size
from Engines.trainer.telemetry.metrics import write_metrics




def worker_training_config(model, incoming_training_cfg: dict, device: str):
    tuned, report = auto_tune_training_config(model, incoming_training_cfg, device)
    if effective_batch_size(tuned) != effective_batch_size(incoming_training_cfg):
        raise RuntimeError("worker batch autotune changed effective batch contract")
    return tuned, report


def worker_optimizer_for_stage(model, optimizer, active_stage, incoming_stage, stage_cfg):
    if optimizer is not None and active_stage == incoming_stage:
        return optimizer, active_stage
    optimizer = AdamW(
        model.parameters(),
        lr=float(stage_cfg["learning_rate"]),
        weight_decay=float(stage_cfg["weight_decay"]),
    )
    return optimizer, incoming_stage

def _write_status(path: Path | None, **fields) -> None:
    if path is not None:
        write_cluster_status(path, **fields)




def _resolve_ipv4_with_timeout(host: str, port: int, timeout_s: float) -> tuple[str, int]:
    """Resolve a hostname with a hard deadline and no leaked resolver threads.

    CPython's ``socket.getaddrinfo`` has no portable per-call timeout. V3.3 used
    a daemon thread around it initially, but a timed-out DNS call leaves that
    thread blocked in the platform resolver and can stall interpreter shutdown.
    Run the resolver in a short-lived child Python process instead; a subprocess
    timeout can be terminated cleanly by ``subprocess.run`` on every supported
    platform.

    ``localhost`` is a deterministic loopback identity and does not need DNS.
    Bypass subprocess startup for it so very small connect timeouts remain
    reliable on Windows, where process startup can exceed the network timeout.
    """
    if str(host).strip().rstrip(".").casefold() == "localhost":
        return "127.0.0.1", int(port)

    try:
        socket.inet_aton(host)
        return host, int(port)
    except OSError:
        pass

    timeout_s = max(0.01, float(timeout_s))
    resolver_code = (
        "import socket,sys;"
        "h=sys.argv[1];p=int(sys.argv[2]);"
        "r=socket.getaddrinfo(h,p,socket.AF_INET,socket.SOCK_STREAM);"
        "print(r[0][4][0])"
    )
    creationflags = 0
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            [sys.executable, "-S", "-c", resolver_code, str(host), str(int(port))],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"hostname resolution timed out: {host}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise OSError(f"hostname did not resolve: {host}{suffix}")
    resolved = (result.stdout or "").strip().splitlines()
    if not resolved:
        raise OSError(f"hostname did not resolve: {host}")
    return str(resolved[-1].strip()), int(port)

def _connect_and_handshake(
    peer: dict,
    *,
    cluster_cfg: dict,
    model_cfg: dict,
    software_version: str,
    device: str,
    hostname: str,
):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_timeout = float(cluster_cfg.get("connect_timeout_seconds", 3.0))
    s.settimeout(connect_timeout)
    try:
        host = str(peer["host"])
        port = int(peer.get("port", cluster_cfg["tcp_port"]))
        target = _resolve_ipv4_with_timeout(host, port, connect_timeout)
        s.connect(target)
        # Report the transport of the actual connected endpoint rather than the
        # discovery label (e.g. a hostname may resolve to LAN or Tailscale).
        connected_host = str(s.getpeername()[0])
        peer["connected_host"] = connected_host
        peer["transport"] = classify_transport(connected_host)
        send_frame(
            s,
            {
                "type": "HELLO",
                "cluster_id": str(cluster_cfg["cluster_id"]),
                "node_id": canonical_hostname(hostname) or hostname,
                "hostname": hostname,
                "role_intent": "worker",
                "software_version": software_version,
                "architecture_hash": architecture_hash(model_cfg),
                "device": device,
            },
        )
        reply, payload = recv_frame(s, 64 * 1024)
        if payload:
            raise ProtocolError("handshake reply payload must be empty")
        if reply.get("type") == "REJECT":
            raise ProtocolError(f"coordinator rejected worker: {reply.get('reason', 'unknown')}")
        if reply.get("type") != "WELCOME":
            raise ProtocolError("coordinator WELCOME required")
        if reply.get("cluster_id") != cluster_cfg["cluster_id"]:
            raise ProtocolError("WELCOME cluster mismatch")
        if reply.get("architecture_hash") != architecture_hash(model_cfg):
            raise ProtocolError("WELCOME architecture mismatch")
        preferred = cluster_cfg.get("preferred_coordinator_hostname")
        if preferred and not hostname_matches(reply.get("coordinator_hostname", ""), preferred):
            raise ProtocolError("WELCOME coordinator identity mismatch")
        freshness = float(cluster_cfg.get("session_freshness_seconds", 30.0))
        if freshness <= 0:
            raise ValueError("session_freshness_seconds must be positive")
        s.settimeout(freshness)
        return s, reply
    except Exception:
        s.close()
        raise


def _validate_session_fence(header: dict, welcome: dict, cluster_cfg: dict) -> None:
    if header.get("cluster_id") != cluster_cfg["cluster_id"]:
        raise ProtocolError("command cluster mismatch")
    if int(header.get("epoch", -1)) != int(welcome["epoch"]):
        raise ProtocolError("command epoch mismatch")
    if header.get("session_id") != welcome["session_id"]:
        raise ProtocolError("command session mismatch")


def _validate_command_fence(header: dict, welcome: dict, cluster_cfg: dict, model_cfg: dict) -> None:
    _validate_session_fence(header, welcome, cluster_cfg)
    if header.get("architecture_hash") != architecture_hash(model_cfg):
        raise ProtocolError("command architecture mismatch")


def _worker_session_loop(
    sock,
    welcome: dict,
    *,
    cluster_cfg: dict,
    model_cfg: dict,
    device: str,
    status_path: Path | None,
    metrics_path: Path | None,
    peer: dict,
    stop_event: threading.Event,
):
    model = build_model_from_config(model_cfg)
    model.to(device)
    optimizer = None
    scaler = None
    active_stage = None
    active_training_key = None
    local_training_cfg = None
    heartbeat_steps = max(1, int(cluster_cfg.get("heartbeat_steps", 10)))
    max_payload = int(cluster_cfg["max_payload_bytes"])

    _write_status(
        status_path,
        role="WORKER",
        control_state="READY",
        cluster_id=str(welcome.get("cluster_id", cluster_cfg.get("cluster_id", ""))),
        coordinator_hostname=str(welcome.get("coordinator_hostname", cluster_cfg.get("preferred_coordinator_hostname", "-"))),
        coordinator_instance_id=str(welcome.get("coordinator_instance_id", "-")),
        peer=peer["host"],
        transport=peer.get("transport", "UNKNOWN"),
        epoch=int(welcome["epoch"]),
        worker_session_id=welcome["session_id"],
        session_id=welcome["session_id"],
        round="-",
        fallback=False,
        last_merge="-",
        canonical_step=int(welcome.get("canonical_step", 0)),
        assignment_steps=0,
        assignment_examples=0,
        round_total_steps=0,
        round_total_examples=0,
    )

    while not stop_event.is_set():
        header, payload = recv_frame(sock, max_payload)
        if header.get("type") == "STOP":
            _validate_session_fence(header, welcome, cluster_cfg)
            return "stop"
        if header.get("type") == "KEEPALIVE":
            _validate_session_fence(header, welcome, cluster_cfg)
            if payload:
                raise ProtocolError("KEEPALIVE payload must be empty")
            _write_status(
                status_path,
                role="WORKER",
                control_state="READY",
                cluster_id=str(welcome.get("cluster_id", cluster_cfg.get("cluster_id", ""))),
                coordinator_hostname=str(welcome.get("coordinator_hostname", cluster_cfg.get("preferred_coordinator_hostname", "-"))),
                coordinator_instance_id=str(welcome.get("coordinator_instance_id", "-")),
                peer=peer["host"],
                transport=peer.get("transport", "UNKNOWN"),
                epoch=int(welcome["epoch"]),
                worker_session_id=welcome["session_id"],
                session_id=welcome["session_id"],
                round="-",
                fallback=False,
                last_merge="-",
                canonical_step=int(header.get("canonical_step", welcome.get("canonical_step", 0))),
                local_window_step=0,
                assignment_steps=0,
                assignment_examples=0,
                round_total_steps=0,
                round_total_examples=0,
            )
            continue
        if header.get("type") != "TRAIN_ROUND":
            raise ProtocolError(f"unknown cluster command: {header.get('type')}")
        _validate_command_fence(header, welcome, cluster_cfg, model_cfg)

        parent = decode_model_state(payload)
        expected_parent_hash = str(header["parent_hash"])
        actual_parent_hash = state_hash(parent)
        if actual_parent_hash != expected_parent_hash:
            raise ProtocolError("canonical parent hash mismatch after decode")
        model.load_state_dict(parent, strict=True)
        model.to(device)
        incoming_training_cfg = header["training_cfg"]
        training_key = (
            int(incoming_training_cfg["micro_batch_size"]),
            int(incoming_training_cfg["gradient_accumulation_steps"]),
            int(incoming_training_cfg["sequence_length"]),
        )
        if local_training_cfg is None or training_key != active_training_key:
            local_training_cfg, batch_tune_report = worker_training_config(
                model, incoming_training_cfg, device
            )
            active_training_key = training_key
            print(
                "batch_autotune role=WORKER "
                f"micro={local_training_cfg['micro_batch_size']} "
                f"accum={local_training_cfg['gradient_accumulation_steps']} "
                f"effective={effective_batch_size(local_training_cfg)} "
                f"fallback={str(bool(batch_tune_report.get('fallback', False))).lower()}",
                flush=True,
            )
        previous_stage = active_stage
        optimizer, active_stage = worker_optimizer_for_stage(
            model, optimizer, active_stage, str(header["stage"]), header["stage_cfg"]
        )
        if previous_stage is not None and active_stage != previous_stage:
            scaler = None

        started = time.monotonic()
        round_id = str(header["round_id"])
        canonical_step = int(header["canonical_step"])
        example_start = int(header["example_start"])
        local_examples = int(header["local_examples"])
        assignment_examples = int(header.get("assignment_examples", local_examples))
        assignment_steps = int(header.get("assignment_steps", max(1, (assignment_examples + effective_batch_size(incoming_training_cfg) - 1) // effective_batch_size(incoming_training_cfg))))
        round_total_steps = int(header.get("round_total_steps", 0) or 0)
        round_total_examples = int(header.get("round_total_examples", 0) or 0)

        def progress(local_step, consumed, loss):
            elapsed = max(1e-9, time.monotonic() - started)
            local_sps = local_step / elapsed
            if metrics_path is not None:
                write_metrics(
                    metrics_path,
                    {
                        "status": "TRAINING",
                        "stage": header["stage"],
                        "stage_step": canonical_step,
                        "stage_examples": int(header.get("canonical_examples", 0)),
                        "stage_target_examples": int(header.get("stage_target_examples", 0)),
                        "global_examples": int(header.get("global_examples", 0)),
                        "loss": round(loss, 6),
                        "steps_per_second": round(local_sps, 6),
                        "local_window_step": int(local_step),
                        "local_window_examples": int(consumed),
                        "local_window_target_examples": local_examples,
                        "micro_batch_size": int(local_training_cfg["micro_batch_size"]),
                        "gradient_accumulation_steps": int(
                            local_training_cfg["gradient_accumulation_steps"]
                        ),
                        "effective_batch": effective_batch_size(local_training_cfg),
                        "device": device,
                    },
                )
            if local_step % heartbeat_steps == 0 or consumed >= local_examples:
                send_frame(
                    sock,
                    {
                        "type": "ROUND_PROGRESS",
                        "cluster_id": cluster_cfg["cluster_id"],
                        "epoch": int(welcome["epoch"]),
                        "session_id": welcome["session_id"],
                        "round_id": round_id,
                        "local_step": int(local_step),
                        "examples": int(consumed),
                        "loss": float(loss),
                        "steps_per_second": float(local_sps),
                    },
                )
                _write_status(
                    status_path,
                    role="WORKER",
                    control_state="TRAINING",
                    cluster_id=str(welcome.get("cluster_id", cluster_cfg.get("cluster_id", ""))),
                    coordinator_hostname=str(welcome.get("coordinator_hostname", cluster_cfg.get("preferred_coordinator_hostname", "-"))),
                    coordinator_instance_id=str(welcome.get("coordinator_instance_id", "-")),
                    peer=peer["host"],
                    transport=peer.get("transport", "UNKNOWN"),
                    epoch=int(welcome["epoch"]),
                    worker_session_id=welcome["session_id"],
                    session_id=welcome["session_id"],
                    round=round_id,
                    fallback=False,
                    last_merge="-",
                    canonical_step=canonical_step,
                    local_window_step=int(local_step),
                    assignment_steps=assignment_steps,
                    assignment_examples=assignment_examples,
                    round_total_steps=round_total_steps,
                    round_total_examples=round_total_examples,
                )

        result = train_local_window(
            model,
            stage=header["stage"],
            example_start=example_start,
            local_examples=local_examples,
            model_cfg=model_cfg,
            training_cfg=local_training_cfg,
            stage_cfg=header["stage_cfg"],
            device=device,
            optimizer=optimizer,
            scaler=scaler,
            progress_cb=progress,
        )
        optimizer = result["optimizer"]
        scaler = result["scaler"]
        elapsed = max(1e-9, time.monotonic() - started)
        delta = compute_delta(parent, result["state"])
        send_frame(
            sock,
            {
                "type": "ROUND_RESULT",
                "cluster_id": cluster_cfg["cluster_id"],
                "epoch": int(welcome["epoch"]),
                "session_id": welcome["session_id"],
                "round_id": round_id,
                "parent_hash": expected_parent_hash,
                "architecture_hash": header["architecture_hash"],
                "examples": int(result["examples"]),
                "steps": int(result["steps"]),
                "loss": float(result["loss"]),
                "steps_per_second": float(result["steps"] / elapsed),
                "wire_kind": "MODEL_DELTA",
                "wire_dtype": str(cluster_cfg.get("wire_update_dtype", "float16")),
                "micro_batch_size": int(local_training_cfg["micro_batch_size"]),
                "gradient_accumulation_steps": int(local_training_cfg["gradient_accumulation_steps"]),
                "effective_batch": effective_batch_size(local_training_cfg),
            },
            encode_model_state(
                delta, wire_dtype=str(cluster_cfg.get("wire_update_dtype", "float16"))
            ),
        )
        _write_status(
            status_path,
            role="WORKER",
            control_state="READY",
            cluster_id=str(welcome.get("cluster_id", cluster_cfg.get("cluster_id", ""))),
            coordinator_hostname=str(welcome.get("coordinator_hostname", cluster_cfg.get("preferred_coordinator_hostname", "-"))),
            coordinator_instance_id=str(welcome.get("coordinator_instance_id", "-")),
            peer=peer["host"],
            transport=peer.get("transport", "UNKNOWN"),
            epoch=int(welcome["epoch"]),
            worker_session_id=welcome["session_id"],
            session_id=welcome["session_id"],
            round=round_id,
            fallback=False,
            last_merge="-",
            canonical_step=canonical_step,
            local_window_step=int(result["steps"]),
            assignment_steps=assignment_steps,
            assignment_examples=assignment_examples,
            round_total_steps=round_total_steps,
            round_total_examples=round_total_examples,
        )
    return "stop"


def worker_service(
    cluster_cfg: dict,
    model_cfg: dict,
    software_version: str,
    device: str,
    *,
    status_path: Path | None = None,
    metrics_path: Path | None = None,
    stop_event: threading.Event | None = None,
    hostname: str | None = None,
):
    stop_event = stop_event or threading.Event()
    hostname = hostname or socket.gethostname()
    cached_peer = None
    backoff = float(cluster_cfg.get("reconnect_min_seconds", 1.0))
    backoff_max = float(cluster_cfg.get("reconnect_max_seconds", 8.0))

    while not stop_event.is_set():
        _write_status(
            status_path,
            role="WORKER",
            control_state="DISCOVERING",
            cluster_id=str(cluster_cfg.get("cluster_id", "")),
            coordinator_hostname=str(cluster_cfg.get("preferred_coordinator_hostname", "-")),
            coordinator_instance_id="-",
            worker_session_id="-",
            peer=(cached_peer or {}).get("host", "none"),
            transport="DISCONNECTED",
            epoch=0,
            session_id="-",
            round="-",
            fallback=False,
            last_merge="-",
        )
        beacon_peers = listen_for_beacons(
            timeout_s=float(cluster_cfg.get("discovery_timeout_seconds", 1.0)),
            port=int(cluster_cfg.get("udp_discovery_port", 48570)),
            expected_cluster_id=str(cluster_cfg["cluster_id"]),
        ) if int(cluster_cfg.get("udp_discovery_port", 48570)) > 0 else []
        candidates = collect_peer_candidates(
            cluster_cfg, beacon_peers=beacon_peers, cached_peer=cached_peer
        )
        # Candidates are already ordered LAN > Tailscale > hostname. Try every
        # route in that order so a stale concrete/static address cannot suppress
        # a working preferred-hostname fallback.
        attempt_candidates = candidates
        last_error = None
        for peer in attempt_candidates:
            if stop_event.is_set():
                return 0
            try:
                _write_status(
                    status_path,
                    role="WORKER",
                    control_state="CONNECTING",
                    cluster_id=str(cluster_cfg.get("cluster_id", "")),
                    coordinator_hostname=str(cluster_cfg.get("preferred_coordinator_hostname", "-")),
                    coordinator_instance_id="-",
                    worker_session_id="-",
                    peer=peer["host"],
                    transport=peer.get("transport", "UNKNOWN"),
                    epoch=0,
                    session_id="-",
                    round="-",
                    fallback=False,
                    last_merge="-",
                )
                sock, welcome = _connect_and_handshake(
                    peer,
                    cluster_cfg=cluster_cfg,
                    model_cfg=model_cfg,
                    software_version=software_version,
                    device=device,
                    hostname=hostname,
                )
                cached_peer = dict(peer)
                backoff = float(cluster_cfg.get("reconnect_min_seconds", 1.0))
                try:
                    outcome = _worker_session_loop(
                        sock,
                        welcome,
                        cluster_cfg=cluster_cfg,
                        model_cfg=model_cfg,
                        device=device,
                        status_path=status_path,
                        metrics_path=metrics_path,
                        peer=peer,
                        stop_event=stop_event,
                    )
                    if outcome == "stop":
                        return 0
                finally:
                    sock.close()
            except Exception as exc:
                last_error = exc
                continue

        _write_status(
            status_path,
            role="WORKER",
            control_state="RECONNECTING",
            cluster_id=str(cluster_cfg.get("cluster_id", "")),
            coordinator_hostname=str(cluster_cfg.get("preferred_coordinator_hostname", "-")),
            coordinator_instance_id="-",
            worker_session_id="-",
            peer=(cached_peer or {}).get("host", "none"),
            transport="DISCONNECTED",
            epoch=0,
            session_id="-",
            round="-",
            fallback=False,
            last_merge="-",
            error=str(last_error)[:240] if last_error else "no coordinator route available",
        )
        stop_event.wait(backoff)
        backoff = min(backoff_max, max(backoff * 2.0, backoff + 0.01))
    return 0


# Compatibility wrapper for V3.2 call sites until orchestrator migration is complete.
def worker_loop(
    host: str,
    port: int,
    model_cfg: dict,
    device: str,
    max_payload: int,
    connect_timeout: float = 5.0,
    status_path: Path | None = None,
    metrics_path: Path | None = None,
):
    cfg = {
        "cluster_id": "quotesnap-main",
        "tcp_port": int(port),
        "udp_discovery_port": 0,
        "discovery_timeout_seconds": 0.0,
        "connect_timeout_seconds": float(connect_timeout),
        "reconnect_min_seconds": 1.0,
        "reconnect_max_seconds": 8.0,
        "round_timeout_seconds": 900.0,
        "heartbeat_steps": 10,
        "max_payload_bytes": int(max_payload),
        "preferred_coordinator_hostname": host,
        "static_peers": [{"host": host, "port": int(port)}],
        "wire_update_dtype": "float16",
    }
    return worker_service(
        cfg,
        model_cfg,
        "3.3.0",
        device,
        status_path=status_path,
        metrics_path=metrics_path,
    )
