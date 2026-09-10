from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import threading
import time
import uuid

from Engines.cluster.coordinator import (
    WorkerRegistry,
    WorkerSession,
    accept_worker_hello,
    open_worker_listener,
    reject_worker,
    welcome_worker,
)
from Engines.cluster.discovery import broadcast_beacon, canonical_hostname, hostname_matches
from Engines.cluster.local_sgd import architecture_hash
from Engines.cluster.protocol import VERSION


def _next_epoch(path: Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        current = int(data.get("epoch", 0))
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError):
        current = 0
    epoch = current + 1
    tmp = path.with_name(path.name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps({"epoch": epoch}, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return epoch


class CoordinatorControlPlane:
    def __init__(
        self,
        cluster_cfg: dict,
        model_cfg: dict,
        software_version: str,
        state_dir: Path,
        *,
        hostname: str | None = None,
    ):
        self.cluster_cfg = dict(cluster_cfg)
        self.model_cfg = dict(model_cfg)
        self.software_version = str(software_version)
        self.state_dir = Path(state_dir)
        self.hostname = hostname or socket.gethostname()
        self.cluster_id = str(cluster_cfg.get("cluster_id", "quotesnap-main"))
        self.architecture_hash = architecture_hash(model_cfg)
        self.epoch = 0
        self.coordinator_instance_id = "-"
        self.tcp_port = int(cluster_cfg.get("tcp_port", 48571))
        self._listener = None
        self._stop = threading.Event()
        self._accept_thread: threading.Thread | None = None
        self._beacon_thread: threading.Thread | None = None
        self._keepalive_thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._registry = WorkerRegistry()
        self._last_error = ""
        self._canonical = {
            "stage": "-",
            "step": 0,
            "checkpoint_hash": "",
        }

    def start(self) -> None:
        if self._listener is not None:
            return
        self.epoch = _next_epoch(self.state_dir / "cluster_epoch.json")
        self.coordinator_instance_id = uuid.uuid4().hex
        self._stop.clear()
        self._listener = open_worker_listener(
            "0.0.0.0",
            self.tcp_port,
            float(self.cluster_cfg.get("listener_poll_seconds", 0.5)),
        )
        self.tcp_port = int(self._listener.getsockname()[1])
        self._accept_thread = threading.Thread(
            target=self._accept_loop,
            name="quotesnap-cluster-accept",
            daemon=True,
        )
        self._accept_thread.start()
        keepalive_interval = float(self.cluster_cfg.get("session_keepalive_seconds", 5.0))
        if keepalive_interval > 0:
            self._keepalive_thread = threading.Thread(
                target=self._keepalive_loop,
                name="quotesnap-cluster-keepalive",
                daemon=True,
            )
            self._keepalive_thread.start()
        discovery_port = int(self.cluster_cfg.get("udp_discovery_port", 48570))
        if discovery_port > 0:
            self._beacon_thread = threading.Thread(
                target=broadcast_beacon,
                kwargs={
                    "stop_event": self._stop,
                    "tcp_port": self.tcp_port,
                    "interval_s": float(
                        self.cluster_cfg.get("beacon_interval_seconds", 1.0)
                    ),
                    "port": discovery_port,
                    "cluster_id": self.cluster_id,
                    "coordinator_hostname": self.hostname,
                    "epoch": self.epoch,
                    "protocol": VERSION,
                },
                name="quotesnap-cluster-beacon",
                daemon=True,
            )
            self._beacon_thread.start()

    def stop(self) -> None:
        self._stop.set()
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.close()
            except Exception:
                pass
        self._registry.close_all("coordinator shutdown")
        for thread in (self._accept_thread, self._beacon_thread, self._keepalive_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=2.0)

    def update_canonical(
        self,
        *,
        stage: str,
        step: int,
        checkpoint_hash: str = "",
    ) -> None:
        with self._lock:
            self._canonical = {
                "stage": str(stage),
                "step": int(step),
                "checkpoint_hash": str(checkpoint_hash or ""),
            }

    def current_sessions(self) -> list[WorkerSession]:
        return self._registry.snapshot()

    def current_session(self) -> WorkerSession | None:
        sessions = self.current_sessions()
        return sessions[0] if sessions else None

    def invalidate(self, session: WorkerSession, reason: str) -> None:
        self._registry.remove(session.node_id, session.session_id)
        with self._lock:
            self._last_error = str(reason)
        session.close(reason)

    def snapshot(self) -> dict:
        sessions = self.current_sessions()
        now = time.monotonic()
        workers = [
            {
                "cluster_id": str(worker.cluster_id),
                "node_id": str(worker.node_id),
                "hostname": str(worker.hostname),
                "session_id": str(worker.session_id),
                "epoch": int(worker.epoch),
                "peer": f"{worker.addr[0]}:{worker.addr[1]}",
                "transport": str(worker.transport),
                "software_version": str(worker.software_version),
                "state": str(getattr(worker, "state", "READY")),
                "round": str(getattr(worker, "active_round_id", "-") or "-"),
                "canonical_step": int(getattr(worker, "canonical_step", 0) or 0),
                "local_window_step": int(getattr(worker, "local_window_step", 0) or 0),
                "assigned_steps": int(getattr(worker, "assigned_steps", 0) or 0),
                "assigned_examples": int(getattr(worker, "assigned_examples", 0) or 0),
                "round_total_steps": int(getattr(worker, "round_total_steps", 0) or 0),
                "round_total_examples": int(getattr(worker, "round_total_examples", 0) or 0),
                "steps_per_second": round(float(getattr(worker, "remote_steps_per_second", 0.0) or 0.0), 4),
                "last_heartbeat_age_seconds": round(max(0.0, now - float(worker.last_seen_monotonic)), 3),
            }
            for worker in sessions
        ]
        expected_workers = max(0, int(self.cluster_cfg.get("expected_worker_count", 2)))
        session_ids = [str(worker.get("session_id", "")) for worker in workers if worker.get("session_id")]
        freshness_limit = max(0.1, float(self.cluster_cfg.get("session_freshness_seconds", 30.0)))
        cluster_sync = {
            "workers_active": len(workers),
            "workers_expected": expected_workers,
            "worker_count_match": len(workers) == expected_workers,
            "sessions_unique": len(session_ids) == len(set(session_ids)) == len(workers),
            "epoch_match": all(int(worker.get("epoch", -1)) == int(self.epoch) for worker in workers),
            "cluster_match": all(str(worker.get("cluster_id", "")) == self.cluster_id for worker in workers),
            "software_match": all(str(worker.get("software_version", "")) == self.software_version for worker in workers),
            "heartbeats_fresh": all(float(worker.get("last_heartbeat_age_seconds", freshness_limit + 1.0)) <= freshness_limit for worker in workers),
        }
        healthy = (
            cluster_sync["worker_count_match"]
            and cluster_sync["sessions_unique"]
            and cluster_sync["epoch_match"]
            and cluster_sync["cluster_match"]
            and cluster_sync["software_match"]
            and cluster_sync["heartbeats_fresh"]
        )
        cluster_sync["status"] = "VERIFIED" if healthy else ("WAITING" if len(workers) < expected_workers else "DEGRADED")
        with self._lock:
            return {
                "cluster_id": self.cluster_id,
                "epoch": self.epoch,
                "coordinator_hostname": self.hostname,
                "coordinator_instance_id": self.coordinator_instance_id,
                "software_version": self.software_version,
                "tcp_port": self.tcp_port,
                "expected_worker_count": expected_workers,
                "workers": workers,
                "cluster_sync": cluster_sync,
                "canonical_stage": self._canonical["stage"],
                "canonical_step": self._canonical["step"],
                "last_error": self._last_error,
            }

    def _keepalive_loop(self) -> None:
        interval = max(0.02, float(self.cluster_cfg.get("session_keepalive_seconds", 5.0)))
        while not self._stop.wait(interval):
            with self._lock:
                canonical_step = int(self._canonical["step"])
            for session in self.current_sessions():
                if str(getattr(session, "state", "READY")).upper() != "READY":
                    continue
                try:
                    session.send(
                        {
                            "type": "KEEPALIVE",
                            "cluster_id": self.cluster_id,
                            "epoch": int(session.epoch),
                            "session_id": session.session_id,
                            "canonical_step": canonical_step,
                        }
                    )
                except Exception as exc:
                    try:
                        self.invalidate(session, f"keepalive failed: {exc}")
                    except Exception:
                        pass

    def _validate_hello(self, hello: dict) -> str | None:
        if hello.get("cluster_id") != self.cluster_id:
            return "cluster mismatch"
        if hello.get("role_intent") != "worker":
            return "role intent must be worker"
        if hello.get("architecture_hash") != self.architecture_hash:
            return "architecture mismatch"
        if str(hello.get("software_version", "")) != self.software_version:
            return "software version mismatch"
        if not hello.get("node_id") or not hello.get("hostname"):
            return "worker identity missing"
        coordinator_key = canonical_hostname(self.hostname)
        worker_node_key = canonical_hostname(str(hello.get("node_id", "")))
        if (
            (coordinator_key and worker_node_key and coordinator_key == worker_node_key)
            or hostname_matches(str(hello.get("hostname", "")), self.hostname)
        ):
            return "self peer rejected"
        return None

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            listener = self._listener
            if listener is None:
                return
            try:
                session, hello = accept_worker_hello(
                    listener,
                    int(self.cluster_cfg.get("max_payload_bytes", 134217728)),
                    handshake_timeout=float(
                        self.cluster_cfg.get("handshake_timeout_seconds", 5.0)
                    ),
                )
            except (TimeoutError, socket.timeout):
                continue
            except OSError as exc:
                if self._stop.is_set():
                    return
                self._last_error = f"listener error: {exc}"
                time.sleep(0.05)
                continue
            except Exception as exc:
                self._last_error = f"handshake error: {exc}"
                continue

            reason = self._validate_hello(hello)
            if reason:
                reject_worker(session, reason)
                continue

            with self._lock:
                canonical = dict(self._canonical)

            session_id = uuid.uuid4().hex
            context = {
                "cluster_id": self.cluster_id,
                "session_id": session_id,
                "epoch": self.epoch,
                "node_id": str(hello["node_id"]),
                "hostname": str(hello["hostname"]),
                "architecture_hash": self.architecture_hash,
                "worker_software_version": str(hello.get("software_version", "")),
                "device": str(hello.get("device", "")),
                "coordinator_id": self.hostname,
                "coordinator_hostname": self.hostname,
                "coordinator_instance_id": self.coordinator_instance_id,
                "software_version": self.software_version,
                "canonical_stage": canonical["stage"],
                "canonical_step": canonical["step"],
                "canonical_checkpoint_hash": canonical["checkpoint_hash"],
                "session_socket_timeout": float(
                    self.cluster_cfg.get("round_timeout_seconds", 900.0)
                ),
            }
            try:
                welcome_worker(session, context)
            except Exception as exc:
                session.close(f"WELCOME failed: {exc}")
                self._last_error = f"WELCOME failed: {exc}"
                continue
            try:
                self._registry.admit(session)
                with self._lock:
                    self._last_error = ""
            except Exception as exc:
                reject_worker(session, f"worker admission failed: {exc}")
