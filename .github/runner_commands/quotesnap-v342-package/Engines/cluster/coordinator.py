from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass, field

from Engines.cluster.discovery import canonical_hostname, classify_transport
from Engines.cluster.protocol import ProtocolError, recv_frame, send_frame


@dataclass
class WorkerSession:
    conn: socket.socket
    addr: tuple
    max_payload: int
    cluster_id: str = ""
    session_id: str = ""
    epoch: int = 0
    node_id: str = ""
    hostname: str = ""
    transport: str = "UNKNOWN"
    architecture_hash: str = ""
    software_version: str = ""
    device: str = ""
    alive: bool = True
    last_seen_monotonic: float = field(default_factory=time.monotonic)
    last_error: str = ""
    remote_steps_per_second: float = 0.0
    state: str = "READY"
    active_round_id: str = "-"
    local_window_step: int = 0
    assigned_steps: int = 0
    assigned_examples: int = 0
    round_total_steps: int = 0
    round_total_examples: int = 0
    canonical_step: int = 0
    _send_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def touch(self) -> None:
        self.last_seen_monotonic = time.monotonic()

    def send(self, header: dict, payload: bytes = b"") -> None:
        if not self.alive:
            raise ProtocolError("worker session is closed")
        with self._send_lock:
            send_frame(self.conn, header, payload)
        self.touch()

    def recv(self, max_payload: int | None = None):
        if not self.alive:
            raise ProtocolError("worker session is closed")
        result = recv_frame(self.conn, max_payload or self.max_payload)
        self.touch()
        return result

    def close(self, reason: str = "") -> None:
        self.alive = False
        if reason:
            self.last_error = reason
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass


class WorkerRegistry:
    """Thread-safe registry of at most one live session per stable worker node."""

    def __init__(self):
        self._lock = threading.RLock()
        self._sessions: dict[str, WorkerSession] = {}

    @staticmethod
    def _key(node_id: str) -> str:
        key = canonical_hostname(str(node_id))
        if not key:
            raise ValueError("worker node_id is required")
        return key

    def admit(self, session: WorkerSession) -> WorkerSession | None:
        key = self._key(session.node_id)
        with self._lock:
            previous = self._sessions.get(key)
            self._sessions[key] = session
        if previous is not None and previous is not session:
            previous.close("superseded by reconnect")
        return previous

    def remove(self, node_id: str, session_id: str) -> WorkerSession | None:
        key = self._key(node_id)
        with self._lock:
            current = self._sessions.get(key)
            if current is None or current.session_id != str(session_id):
                return None
            return self._sessions.pop(key)

    def get(self, node_id: str) -> WorkerSession | None:
        key = self._key(node_id)
        with self._lock:
            session = self._sessions.get(key)
            if session is None or not session.alive:
                return None
            return session

    def snapshot(self) -> list[WorkerSession]:
        with self._lock:
            items = [
                (key, session)
                for key, session in self._sessions.items()
                if session.alive
            ]
        items.sort(key=lambda item: item[0])
        return [session for _, session in items]

    def close_all(self, reason: str = "") -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.close(reason)


def open_worker_listener(host: str, port: int, timeout_s: float):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(4)
    s.settimeout(timeout_s)
    return s


def accept_worker_hello(
    listener,
    max_payload: int,
    *,
    handshake_timeout: float,
) -> tuple[WorkerSession, dict]:
    conn, addr = listener.accept()
    conn.settimeout(handshake_timeout)
    session = WorkerSession(
        conn=conn,
        addr=addr,
        max_payload=max_payload,
        transport=classify_transport(addr[0]),
    )
    try:
        header, payload = recv_frame(conn, 64 * 1024)
        if payload:
            raise ProtocolError("HELLO payload must be empty")
        if header.get("type") != "HELLO":
            raise ProtocolError("worker HELLO required")
        return session, header
    except Exception:
        session.close("handshake failed")
        raise


def reject_worker(session: WorkerSession, reason: str) -> None:
    try:
        session.send({"type": "REJECT", "reason": str(reason)[:240]})
    finally:
        session.close(reason)


def welcome_worker(session: WorkerSession, context: dict) -> None:
    session.cluster_id = str(context["cluster_id"])
    session.session_id = str(context["session_id"])
    session.epoch = int(context["epoch"])
    session.node_id = str(context["node_id"])
    session.hostname = str(context["hostname"])
    session.architecture_hash = str(context["architecture_hash"])
    session.software_version = str(context.get("worker_software_version", ""))
    session.device = str(context.get("device", ""))
    session.conn.settimeout(float(context.get("session_socket_timeout", 900.0)))
    session.send(
        {
            "type": "WELCOME",
            "cluster_id": session.cluster_id,
            "coordinator_id": str(context["coordinator_id"]),
            "coordinator_hostname": str(context["coordinator_hostname"]),
            "coordinator_instance_id": str(context.get("coordinator_instance_id", "-")),
            "session_id": session.session_id,
            "epoch": session.epoch,
            "software_version": str(context["software_version"]),
            "architecture_hash": session.architecture_hash,
            "canonical_stage": str(context.get("canonical_stage", "-")),
            "canonical_step": int(context.get("canonical_step", 0)),
            "canonical_checkpoint_hash": str(
                context.get("canonical_checkpoint_hash", "")
            ),
        }
    )


# Compatibility wrapper for older loopback tests. V3.3 production admission is
# performed by CoordinatorControlPlane so authority/fencing cannot be bypassed.
def accept_worker(listener, max_payload: int):
    session, header = accept_worker_hello(
        listener, max_payload, handshake_timeout=5.0
    )
    session.node_id = str(header.get("node_id", header.get("device", "worker")))
    session.hostname = str(header.get("hostname", session.node_id))
    session.conn.settimeout(900.0)
    session.send({"type": "WELCOME", "protocol": 2, "session_id": "legacy", "epoch": 0})
    return session


def _validate_round_frame(session: WorkerSession, header: dict, *, cluster_id: str, round_id: str) -> None:
    if header.get("cluster_id") != cluster_id:
        raise ProtocolError("worker cluster mismatch")
    if int(header.get("epoch", -1)) != int(session.epoch):
        raise ProtocolError("worker epoch mismatch")
    if header.get("session_id") != session.session_id:
        raise ProtocolError("worker session mismatch")
    if header.get("round_id") != round_id:
        raise ProtocolError("worker round mismatch")


def run_remote_round(
    session: WorkerSession,
    *,
    cluster_id: str,
    round_id: str,
    stage: str,
    canonical_step: int,
    example_start: int,
    local_examples: int,
    parent_state: dict,
    model_cfg: dict,
    training_cfg: dict,
    stage_cfg: dict,
    round_timeout_seconds: float,
    canonical_examples: int = 0,
    global_examples: int = 0,
    stage_target_examples: int = 0,
    round_total_steps: int = 0,
    round_total_examples: int = 0,
):
    from Engines.cluster.local_sgd import architecture_hash, state_hash
    from Engines.cluster.weights import decode_model_state, encode_model_state

    parent_hash = state_hash(parent_state)
    arch_hash = architecture_hash(model_cfg)
    if session.architecture_hash and session.architecture_hash != arch_hash:
        raise ProtocolError("worker session architecture mismatch")
    deadline = time.monotonic() + float(round_timeout_seconds)
    session.state = "TRAINING"
    session.active_round_id = str(round_id)
    session.local_window_step = 0
    effective_batch = max(1, int(training_cfg.get("micro_batch_size", 1)) * int(training_cfg.get("gradient_accumulation_steps", 1)))
    session.assigned_examples = int(local_examples)
    session.assigned_steps = max(1, (int(local_examples) + effective_batch - 1) // effective_batch)
    session.round_total_steps = int(round_total_steps or 0)
    session.round_total_examples = int(round_total_examples or 0)
    session.canonical_step = int(canonical_step)
    session.send(
        {
            "type": "TRAIN_ROUND",
            "cluster_id": cluster_id,
            "epoch": int(session.epoch),
            "session_id": session.session_id,
            "round_id": round_id,
            "stage": stage,
            "canonical_step": int(canonical_step),
            "canonical_examples": int(canonical_examples),
            "global_examples": int(global_examples),
            "stage_target_examples": int(stage_target_examples),
            "assignment_steps": int(session.assigned_steps),
            "assignment_examples": int(session.assigned_examples),
            "round_total_steps": int(session.round_total_steps),
            "round_total_examples": int(session.round_total_examples),
            "example_start": int(example_start),
            "local_examples": int(local_examples),
            "parent_hash": parent_hash,
            "architecture_hash": arch_hash,
            "training_cfg": training_cfg,
            "stage_cfg": stage_cfg,
            "wire_kind": "CANONICAL_PARENT",
            "wire_dtype": "float32",
        },
        encode_model_state(parent_state, wire_dtype="float32"),
    )

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"remote round timed out: {round_id}")
        session.conn.settimeout(remaining)
        header, payload = session.recv(session.max_payload)
        _validate_round_frame(session, header, cluster_id=cluster_id, round_id=round_id)
        frame_type = header.get("type")
        if frame_type == "ROUND_PROGRESS":
            if payload:
                raise ProtocolError("ROUND_PROGRESS payload must be empty")
            session.remote_steps_per_second = float(header.get("steps_per_second", 0.0))
            session.local_window_step = int(header.get("local_step", session.local_window_step))
            session.state = "TRAINING"
            session.active_round_id = str(round_id)
            continue
        if frame_type != "ROUND_RESULT":
            raise ProtocolError(f"unexpected worker frame: {frame_type}")
        if header.get("parent_hash") != parent_hash:
            raise ProtocolError("worker parent mismatch")
        if header.get("architecture_hash") != arch_hash:
            raise ProtocolError("worker architecture mismatch")
        if int(header.get("examples", -1)) != int(local_examples):
            raise ProtocolError("worker example count mismatch")
        if header.get("wire_kind") != "MODEL_DELTA":
            raise ProtocolError("worker result must contain MODEL_DELTA")
        delta = decode_model_state(payload)
        session.remote_steps_per_second = float(header.get("steps_per_second", 0.0))
        session.local_window_step = int(header.get("steps", session.local_window_step))
        session.state = "READY"
        session.active_round_id = str(round_id)
        return header, delta
