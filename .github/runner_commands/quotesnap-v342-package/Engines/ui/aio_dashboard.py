from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import ctypes

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Engines.cluster.discovery import hostname_matches
from Engines.cluster.identity import FROZEN_NODE_HOSTNAME_ENV, LocalNodeIdentity, resolve_local_node_identity
from Engines.cluster.root_ownership import ensure_root_ownership

APP_VERSION = "3.4.2"
APP_TITLE = "QuoteSnap AI Trainer V3.4.2 Adaptive Multi-Worker Cluster AIO"

METRICS = ROOT / "State" / "training_metrics.json"
CLUSTER = ROOT / "State" / "cluster_status.json"
CLUSTER_CONFIG = ROOT / "Config" / "cluster.json"
LOGS = ROOT / "Logs"
WORKER = ROOT / "Engines" / "orchestrator" / "aio_orchestrator.py"

UI_INTERVAL = 0.05
METRICS_INTERVAL = 0.05
GPU_INTERVAL = 0.5
HEALTH_INTERVAL = 1.0
IDLE_SLEEP = 0.005
BOX_WIDTH = 104

C = {
    "reset": "\033[0m",
    "cyan": "\033[96m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "magenta": "\033[95m",
    "gray": "\033[90m",
    "white": "\033[97m",
}
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
TERMINAL_MODE = "ansi"


class StreamPump(threading.Thread):
    def __init__(self, stream):
        super().__init__(daemon=True)
        self.stream = stream
        self.items = queue.Queue()

    def run(self):
        try:
            for line in self.stream:
                self.items.put(line)
        finally:
            self.items.put(None)

    def drain(self):
        out = []
        while True:
            try:
                item = self.items.get_nowait()
            except queue.Empty:
                break
            if item is not None:
                out.append(item)
        return out


class Cadence:
    def __init__(self, *, ui, metrics, gpu, health, now=None):
        base = time.monotonic() if now is None else float(now)
        self.intervals = {"ui": ui, "metrics": metrics, "gpu": gpu, "health": health}
        self.next = {k: base for k in self.intervals}

    def due(self, name, now=None):
        now = time.monotonic() if now is None else float(now)
        return now + 1e-12 >= self.next[name]

    def mark(self, name, now=None):
        now = time.monotonic() if now is None else float(now)
        self.next[name] = now + self.intervals[name]


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def clear() -> None:
    """Deprecated compatibility hook. Rendering no longer clears per frame."""
    return None


def _enable_windows_vt() -> bool:
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if handle in (0, -1) or not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


def _win32_home() -> bool:
    if os.name != "nt":
        return False
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        # COORD packs X and Y into the low/high 16-bit words. (0,0) == 0.
        return bool(kernel32.SetConsoleCursorPosition(handle, 0))
    except Exception:
        return False


def prepare_terminal() -> str:
    """Prepare a stable in-place renderer without emitting unsupported ANSI."""
    global TERMINAL_MODE
    if os.name == "nt" and not _enable_windows_vt():
        TERMINAL_MODE = "win32"
        os.system("cls")
        _win32_home()
        return TERMINAL_MODE
    TERMINAL_MODE = "ansi"
    sys.stdout.write("\x1b[2J\x1b[H\x1b[?25l")
    sys.stdout.flush()
    return TERMINAL_MODE


def restore_terminal() -> None:
    if TERMINAL_MODE == "ansi":
        sys.stdout.write("\x1b[?25h\n")
    else:
        sys.stdout.write("\n")
    sys.stdout.flush()


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_metrics():
    return _load_json(METRICS)


def load_cluster():
    return _load_json(CLUSTER)



def build_child_environment(cluster_cfg: dict) -> tuple[dict, LocalNodeIdentity]:
    identity = resolve_local_node_identity(cluster_cfg.get("preferred_coordinator_hostname"))
    env = os.environ.copy()
    env[FROZEN_NODE_HOSTNAME_ENV] = identity.hostname
    return env, identity


def gpu_stats():
    if not shutil.which("nvidia-smi"):
        return {}
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
        vals = [x.strip() for x in out.splitlines()[0].split(",")]
        return {
            "name": vals[0],
            "used": vals[1],
            "total": vals[2],
            "util": vals[3],
            "temp": vals[4],
            "power": vals[5],
        }
    except Exception:
        return {}


def disk_health():
    try:
        usage = shutil.disk_usage(ROOT)
        return {"free_gb": round(usage.free / 1024**3, 1)}
    except Exception:
        return {}


def fmt_seconds(s):
    s = max(0, int(s or 0))
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def fmt_human_seconds(s):
    s = max(0, int(s or 0))
    days, rem = divmod(s, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def _bar(pct, width=32):
    pct = max(0.0, min(100.0, float(pct or 0.0)))
    fill = int(width * pct / 100.0)
    return "█" * fill + "░" * (width - fill)


def _fit(text: str, width: int = BOX_WIDTH) -> str:
    text = str(text)
    if len(text) > width:
        if width <= 1:
            return text[:width]
        text = text[: width - 1] + "…"
    return text.ljust(width)


def _line(text: str = "", color: str = "white", *, center: bool = False) -> str:
    if center:
        raw = str(text)
        if len(raw) > BOX_WIDTH:
            raw = raw[: BOX_WIDTH - 1] + "…"
        payload = raw.center(BOX_WIDTH)
    else:
        payload = _fit(text)
    return C["cyan"] + "║" + C[color] + payload + C["cyan"] + "║" + C["reset"]


def _border(left: str, fill: str, right: str) -> str:
    return C["cyan"] + left + fill * BOX_WIDTH + right + C["reset"]


def _role_display(role: str) -> tuple[str, str]:
    role = str(role or "LOCAL").upper()
    if role == "COORDINATOR":
        return "PRIMARY COORDINATOR", "green"
    if role == "WORKER":
        return "GPU WORKER", "cyan"
    return role, "yellow"


def _short(value, width=12):
    value = str(value or "-")
    if value == "-" or len(value) <= width:
        return value
    if width < 7:
        return value[:width]
    left = max(3, (width - 1) // 2)
    right = width - 1 - left
    return value[:left] + "…" + value[-right:]


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _loss_text(value):
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value if value not in (None, "") else "--")


def _node_label(node_id, hostname):
    key = str(node_id or "").lower()
    if key == "doonchyscomputi":
        return "MAIN"
    if key == "msi":
        return "MSI"
    host = str(hostname or node_id or "-")
    if host.upper() == "DESKTOP-V9SCI9V":
        return "OLD-PC"
    return host[:14]


def _frame_shell(title_line, role_line, body_lines):
    return "\n".join([
        _border("╔", "═", "╗"),
        _line(title_line, "white", center=True),
        _border("╠", "═", "╣"),
        _line(role_line, "green", center=True),
        *body_lines,
        _border("╚", "═", "╝"),
    ])


def _gpu_lines(gpu):
    if not gpu:
        return [_line("GPU telemetry unavailable", "yellow")]
    return [
        _line(f"GPU {gpu.get('name', '-')} ", "magenta"),
        _line(
            f"GPU {gpu.get('util', '-')}%   VRAM {gpu.get('used', '-')}/{gpu.get('total', '-')} MiB   "
            f"Temp {gpu.get('temp', '-')}C   Power {gpu.get('power', '-')}W",
            "white",
        ),
    ]


def _global_values(state):
    stage = state.get("stage", "DETECTING")
    status = state.get("status", "STARTING")
    step = _safe_int(state.get("stage_step", 0))
    examples = _safe_int(state.get("stage_examples", 0))
    target = _safe_int(state.get("stage_target_examples", 0))
    pct = 100.0 * examples / max(1, target)
    loss = _loss_text(state.get("loss", "--"))
    sps = _safe_float(state.get("steps_per_second", 0.0))
    eff = max(1, _safe_int(state.get("effective_batch", 128), 128))
    return stage, status, step, examples, target, pct, loss, sps, eff


def _build_coordinator_frame(state, gpu, cluster, health, log_name):
    stage, status, step, examples, target, pct, loss, local_sps, eff = _global_values(state)
    workers = list(cluster.get("workers", []) or [])
    sync = dict(cluster.get("cluster_sync", {}) or {})
    sync_status = str(sync.get("status", "WAITING")).upper()
    sync_color = "green" if sync_status == "VERIFIED" else ("yellow" if sync_status == "WAITING" else "red")
    fallback = bool(cluster.get("fallback", False))
    epoch = cluster.get("epoch", "-")
    round_id = str(cluster.get("round", "-"))
    canonical = _safe_int(cluster.get("canonical_step", step), step)
    instance_id = _short(cluster.get("coordinator_instance_id", "-"), 14)
    transport = str(cluster.get("transport_summary", "LOCAL"))
    cluster_sps = _safe_float(cluster.get("cluster_steps_per_second", 0.0))
    if cluster_sps <= 0:
        cluster_sps = local_sps + sum(_safe_float(w.get("steps_per_second", 0.0)) for w in workers)
    eta = ((target - examples) / (cluster_sps * eff)) if cluster_sps > 0 and target > examples else 0
    coord = dict(cluster.get("coordinator", {}) or {})
    coord_assigned = _safe_int(coord.get("assigned_steps", 0))
    coord_progress = _safe_int(coord.get("local_window_step", state.get("local_window_step", 0)))
    coord_sps = _safe_float(coord.get("steps_per_second", local_sps))
    round_total_steps = _safe_int(cluster.get("round_total_steps", 0))
    if round_total_steps <= 0:
        round_total_steps = coord_assigned + sum(_safe_int(w.get("assigned_steps", 0)) for w in workers)
    round_total_examples = _safe_int(cluster.get("round_total_examples", 0))
    round_progress = coord_progress + sum(_safe_int(w.get("local_window_step", 0)) for w in workers)
    round_pct = 100.0 * round_progress / max(1, round_total_steps)
    expected = _safe_int(cluster.get("expected_worker_count", sync.get("workers_expected", 0)))
    active = len(workers)
    healthy = sync_status == "VERIFIED" and not fallback
    title_health = "HEALTHY" if healthy else ("WAITING" if sync_status == "WAITING" else "ATTENTION")
    body = [
        _line(f"ROLE VERIFIED   |   Machine {cluster.get('local_hostname', '-')}   |   Epoch {epoch}   |   Link {transport}", "green" if healthy else "yellow"),
        _border("╠", "═", "╣"),
        _line(f"{stage} TRAINING   {pct:.4f}%   |   Canonical Step {canonical:,}", "white"),
        _line(_bar(pct, 58), "magenta"),
        _line(f"Examples {examples:,} / {target:,}   |   Loss {loss}", "white"),
        _line(f"Cluster Speed {cluster_sps:.2f} steps/s   |   ETA {fmt_human_seconds(eta)}", "white"),
        _border("╠", "═", "╣"),
        _line(f"CURRENT ROUND  {round_id}   |   {cluster.get('control_state', status)}", "cyan"),
        _line(f"Coordinator ID {instance_id}   |   Budget {round_total_steps:,} steps / {round_total_examples:,} examples", "white"),
        _line("NODE           ROLE      WORK          SPEED       STATE       SESSION", "gray"),
        _line(f"{'OLD-PC':<14} {'COORD':<9} {coord_progress:>4}/{max(1,coord_assigned):<7} {coord_sps:>7.2f}/s   {str(cluster.get('control_state','-'))[:11]:<11} {'--':<12}", "magenta"),
    ]
    for w in workers:
        label = _node_label(w.get("node_id"), w.get("hostname"))
        progress = _safe_int(w.get("local_window_step", 0))
        assigned = _safe_int(w.get("assigned_steps", 0))
        wsps = _safe_float(w.get("steps_per_second", 0.0))
        state_name = str(w.get("state", "-"))[:11]
        sid = _short(w.get("session_id", "-"), 12)
        body.append(_line(f"{label:<14} {'WORKER':<9} {progress:>4}/{max(1,assigned):<7} {wsps:>7.2f}/s   {state_name:<11} {sid:<12}", "cyan"))
    body.extend([
        _line(f"Round Progress {round_progress:,}/{max(1,round_total_steps):,}   {_bar(round_pct, 36)}   {round_pct:5.1f}%", "white"),
        _border("╠", "═", "╣"),
        _line("ADAPTIVE BALANCING   |   LIVE THROUGHPUT" if cluster.get("adaptive_round_balancing", False) else "ROUND ALLOCATION", "green"),
    ])
    allocations = [("OLD-PC", coord_assigned)] + [(_node_label(w.get("node_id"), w.get("hostname")), _safe_int(w.get("assigned_steps",0))) for w in workers]
    for label, assigned in allocations:
        share = 100.0 * assigned / max(1, round_total_steps)
        body.append(_line(f"{label:<14} {assigned:>4} steps   {share:5.1f}%   {_bar(share, 28)}", "white"))
    body.extend([
        _border("╠", "═", "╣"),
        *_gpu_lines(gpu),
        _border("╠", "═", "╣"),
        _line(f"CLUSTER SYNC  {sync_status}   |   Workers {active}/{expected}   |   Sessions {active} unique/{expected} expected", sync_color),
        _line(
            f"Epoch {'MATCH' if sync.get('epoch_match') else 'CHECK'}   |   Round {'MATCH' if sync.get('round_match') else 'CHECK'}   |   "
            f"Canonical {'MATCH' if sync.get('canonical_match') else 'CHECK'}   |   Software {'MATCH' if sync.get('software_match') else 'CHECK'}",
            sync_color,
        ),
        _line("EVENTS  All systems nominal" if healthy else ("EVENTS  Fallback mode active" if fallback else f"EVENTS  Cluster sync {sync_status.lower()}"), "green" if healthy else ("red" if fallback else "yellow")),
        _border("╠", "═", "╣"),
        _line(f"Last merge {cluster.get('last_merge','-')}   |   Free {health.get('free_gb','-')} GB   |   Log {log_name}", "gray"),
        _line("BASE → CPT → SFT → SAFETY → PREF → BEST", "gray"),
    ])
    return _frame_shell(f"QUOTESNAP AI TRAINER  V3.4.2   |   {title_health}", "PRIMARY COORDINATOR", body)


def _build_worker_frame(state, gpu, cluster, health, log_name):
    stage, status, step, examples, target, pct, loss, sps, eff = _global_values(state)
    local_step = _safe_int(cluster.get("local_window_step", state.get("local_window_step", 0)))
    assigned_steps = _safe_int(cluster.get("assignment_steps", 0))
    assigned_examples = _safe_int(cluster.get("assignment_examples", state.get("local_window_target_examples", 0)))
    if assigned_steps <= 0 and assigned_examples > 0:
        assigned_steps = max(1, (assigned_examples + eff - 1) // eff)
    if assigned_examples <= 0 and assigned_steps > 0:
        assigned_examples = assigned_steps * eff
    local_examples = _safe_int(state.get("local_window_examples", local_step * eff))
    assign_pct = 100.0 * local_step / max(1, assigned_steps)
    round_eta = (max(0, assigned_steps - local_step) / sps) if sps > 0 else 0
    round_total_steps = _safe_int(cluster.get("round_total_steps", 0))
    share = 100.0 * assigned_steps / max(1, round_total_steps) if round_total_steps else 0.0
    coordinator = str(cluster.get("coordinator_hostname") or cluster.get("configured_primary") or "-")
    peer = str(cluster.get("peer", "none"))
    transport = str(cluster.get("transport", "DISCONNECTED"))
    control_state = str(cluster.get("control_state", status)).upper()
    fallback = bool(cluster.get("fallback", False))
    connected = transport.upper() not in {"DISCONNECTED", "LOCAL", "UNKNOWN"} and control_state not in {"DISCOVERING", "CONNECTING", "RECONNECTING"}
    health_label = "WORKER HEALTHY" if connected and not fallback else ("RECONNECTING" if control_state in {"DISCOVERING", "CONNECTING", "RECONNECTING"} else "ATTENTION")
    link_color = "green" if connected and not fallback else ("yellow" if not fallback else "red")
    worker_session = str(cluster.get("worker_session_id") or cluster.get("session_id") or "-")
    coord_instance = _short(cluster.get("coordinator_instance_id", "-"),14)
    local_name = _node_label(cluster.get("node_id"), cluster.get("local_hostname"))
    body = [
        _line(f"WORKER ROLE VERIFIED   |   {local_name}   |   Epoch {cluster.get('epoch','-')}   |   {transport}", "green" if connected else "yellow"),
        _border("╠", "═", "╣"),
        _line(f"CURRENT ASSIGNMENT   |   Round {cluster.get('round','-')}", "cyan"),
        _line(f"Assigned {assigned_steps:,} steps • {assigned_examples:,} examples", "white"),
        _line(f"Progress {local_step:,} / {max(1,assigned_steps):,}   {_bar(assign_pct, 46)}   {assign_pct:5.1f}%", "white"),
        _line(f"Local speed {sps:.2f} steps/s   |   Round ETA {fmt_human_seconds(round_eta)}   |   Local loss {loss}", "white"),
        _line(f"Contribution {local_examples:,} / {assigned_examples:,} examples", "white"),
        _border("╠", "═", "╣"),
        _line("GLOBAL TRAINING", "cyan"),
        _line(f"Canonical { _safe_int(cluster.get('canonical_step', step), step):,}   |   Examples {examples:,} / {target:,}   |   {pct:.4f}%", "white"),
        _line(f"Stage {stage}   |   Coordinator {coordinator}   |   Cluster {cluster.get('cluster_id','-')}", "white"),
        _border("╠", "═", "╣"),
        _line("ADAPTIVE ALLOCATION", "green"),
        _line(f"My share {assigned_steps:,} / {round_total_steps:,} steps   {share:5.1f}%   {_bar(share, 36)}" if round_total_steps else "My share awaiting round assignment", "white"),
        _line(f"Measured throughput {sps:.2f} steps/s", "white"),
        _border("╠", "═", "╣"),
        *_gpu_lines(gpu),
        _border("╠", "═", "╣"),
        _line(f"COORDINATOR LINK   |   {'CONNECTED' if connected else control_state}", link_color),
        _line(f"Coordinator {coordinator}   |   Peer {peer}   |   Coordinator ID {coord_instance}", "white"),
        _line(f"Epoch {cluster.get('epoch','-')}   |   My session {worker_session}   |   Fallback {'ON' if fallback else 'OFF'}", "white"),
        _line("Next action: finish assignment → submit delta → wait for canonical merge" if assigned_steps else "Next action: wait for coordinator assignment", "gray"),
        _line("EVENTS  All systems nominal" if connected and not fallback else f"EVENTS  {control_state.lower()}", link_color),
        _border("╠", "═", "╣"),
        _line(f"Free {health.get('free_gb','-')} GB   |   Log {log_name}", "gray"),
        _line("BASE → CPT → SFT → SAFETY → PREF → BEST", "gray"),
    ]
    return _frame_shell(f"QUOTESNAP AI TRAINER  V3.4.2   |   {health_label}", "GPU WORKER", body)


def _build_starting_frame(state, gpu, cluster, health, log_name):
    role, color = _role_display(cluster.get("role", "LOCAL"))
    body = [
        _line(f"Machine {cluster.get('local_hostname','-')}   |   Expected {cluster.get('expected_role','-')}", color),
        _border("╠", "═", "╣"),
        _line(f"State {cluster.get('control_state', state.get('status','STARTING'))}", "yellow"),
        *_gpu_lines(gpu),
        _border("╠", "═", "╣"),
        _line(f"Free {health.get('free_gb','-')} GB   |   Log {log_name}", "gray"),
    ]
    return _frame_shell(APP_TITLE, f"THIS NODE: {role}", body)


def build_frame(state, gpu, cluster, health, log_name) -> str:
    role = str(cluster.get("role", "LOCAL")).upper()
    if role == "COORDINATOR":
        return _build_coordinator_frame(state, gpu, cluster, health, log_name)
    if role == "WORKER":
        return _build_worker_frame(state, gpu, cluster, health, log_name)
    return _build_starting_frame(state, gpu, cluster, health, log_name)


def render(state, gpu, cluster, health, log_name):
    frame = build_frame(state, gpu, cluster, health, log_name)
    if TERMINAL_MODE == "win32":
        _win32_home()
        sys.stdout.write(strip_ansi(frame))
    else:
        # One cursor move + one buffered write. Never clear the terminal between frames.
        sys.stdout.write("\x1b[H" + frame)
    sys.stdout.flush()


def parse_line(line, state):
    if line.startswith("aio_stage="):
        m = re.search(r"aio_stage=(\w+)", line)
        if m:
            state["stage"] = m.group(1)
            state["status"] = "TRAINING"
    m = re.search(r"step=(\d+)\s+stage=(\w+)\s+examples=(\d+)\s+loss=([0-9eE+.\-]+)", line)
    if m:
        state.update(
            {
                "stage_step": int(m.group(1)),
                "stage": m.group(2),
                "stage_examples": int(m.group(3)),
                "loss": float(m.group(4)),
                "status": "TRAINING",
            }
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        if not WORKER.exists():
            raise SystemExit("worker missing")
        c = Cadence(
            ui=UI_INTERVAL,
            metrics=METRICS_INTERVAL,
            gpu=GPU_INTERVAL,
            health=HEALTH_INTERVAL,
            now=0,
        )
        if not c.due("ui", 0):
            raise SystemExit("cadence self-test failed")
        print("V3_4_AIO_DASHBOARD_SELFTEST_PASS")
        return 0

    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"training_{time.strftime('%Y%m%d_%H%M%S')}.log"
    cluster_cfg = _load_json(CLUSTER_CONFIG)
    child_env, frozen_identity = build_child_environment(cluster_cfg)
    ensure_root_ownership(
        ROOT, node_id=frozen_identity.node_id, hostname=frozen_identity.hostname
    )
    proc = subprocess.Popen(
        [sys.executable, "-u", str(WORKER)],
        cwd=ROOT,
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pump = StreamPump(proc.stdout)
    pump.start()
    cadence = Cadence(
        ui=UI_INTERVAL,
        metrics=METRICS_INTERVAL,
        gpu=GPU_INTERVAL,
        health=HEALTH_INTERVAL,
    )
    state = {"status": "STARTING", "stage": "DETECTING"}
    gpu = {}
    cluster = {
        "role": "LOCAL",
        "control_state": "STARTING",
        "local_hostname": frozen_identity.hostname,
        "node_id": frozen_identity.node_id,
        "configured_primary": frozen_identity.configured_primary,
        "authority_match": frozen_identity.authority_match,
        "expected_role": "COORDINATOR" if frozen_identity.authority_match else "WORKER",
    }
    health = {}
    prepare_terminal()
    try:
        with log.open("w", encoding="utf-8") as lf:
            while True:
                for line in pump.drain():
                    lf.write(line)
                    lf.flush()
                    parse_line(line, state)
                now = time.monotonic()
                if cadence.due("metrics", now):
                    m = load_metrics()
                    if m:
                        state.update(m)
                    cluster = load_cluster() or cluster
                    cadence.mark("metrics", now)
                if cadence.due("gpu", now):
                    gpu = gpu_stats()
                    cadence.mark("gpu", now)
                if cadence.due("health", now):
                    health = disk_health()
                    cadence.mark("health", now)
                if cadence.due("ui", now):
                    render(state, gpu, cluster, health, log.name)
                    cadence.mark("ui", now)
                if proc.poll() is not None:
                    for line in pump.drain():
                        lf.write(line)
                        parse_line(line, state)
                    break
                time.sleep(IDLE_SLEEP)
            rc = proc.wait()
        render(state, gpu, cluster, health, log.name)
    finally:
        restore_terminal()

    if rc == 0:
        print(C["green"] + "V3.4 AIO training flow exited successfully." + C["reset"])
    else:
        print(C["red"] + f"V3.4 AIO exited with code {rc}. Log: {log}" + C["reset"])
    input("Press Enter to close...")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
