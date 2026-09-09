from pathlib import Path
import hashlib
import shutil

ROOT = Path(r"D:\QuoteSnap\AI\V3.3_AIO")
DASH = ROOT / "Engines" / "ui" / "aio_dashboard.py"
ORCH = ROOT / "Engines" / "orchestrator" / "aio_orchestrator.py"
OWNER = ROOT / "Engines" / "cluster" / "root_ownership.py"

OLD = {
    DASH: "8A529D170286B0BA0438897286F86734552EC7CB69D80F0F022114A0876AE5A8",
    ORCH: "1F19677C0CCE9F63B1470335CAFB4BFB7BEC3B9C2CB0177312AEBDE969F2832F",
}
NEW = {
    DASH: "0D1365455E16C1C1868C31212F1E5A920D02BF73BD5FF1FB46EAD16DF13B93C5",
    ORCH: "9C947682F392D4B21308E5DB43AE2FF6453B61375C1A13266EEE95AB4C44930B",
    OWNER: "60731A8F053707A2FF8C8F60030B1D8E902CF9B6B18AC59136CFC211BCE37DA5",
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

for path, expected in OLD.items():
    actual = sha(path)
    if actual not in {expected, NEW[path]}:
        raise SystemExit(f"UNEXPECTED_SOURCE_HASH {path} {actual}")

for path in (DASH, ORCH):
    bak = path.with_suffix(path.suffix + ".pre_shared_root_fix.bak")
    if not bak.exists():
        shutil.copy2(path, bak)

OWNER.write_text('from __future__ import annotations\n\nimport json\nimport os\nfrom pathlib import Path\n\n\nclass RootOwnershipConflict(RuntimeError):\n    pass\n\n\ndef _marker_path(root: Path) -> Path:\n    return Path(root) / "State" / "root_owner.json"\n\n\ndef _read_marker(path: Path) -> dict:\n    try:\n        data = json.loads(path.read_text(encoding="utf-8"))\n    except FileNotFoundError:\n        return {}\n    except Exception as exc:\n        raise RootOwnershipConflict(\n            f"ROOT_OWNERSHIP_CONFLICT: unreadable ownership marker at {path}: {exc}"\n        ) from exc\n    if not isinstance(data, dict) or not data.get("node_id"):\n        raise RootOwnershipConflict(\n            f"ROOT_OWNERSHIP_CONFLICT: invalid ownership marker at {path}"\n        )\n    return data\n\n\ndef ensure_root_ownership(root: Path, *, node_id: str, hostname: str) -> dict:\n    """Bind one physical QuoteSnap runtime root to exactly one machine identity.\n\n    This prevents a worker from launching the trainer directly from a coordinator\'s\n    SMB/shared folder and silently overwriting Logs/State/Checkpoints.\n    """\n    root = Path(root).resolve()\n    node_id = str(node_id or "").strip()\n    hostname = str(hostname or "").strip()\n    if not node_id or not hostname:\n        raise ValueError("node_id and hostname are required for root ownership")\n\n    marker = _marker_path(root)\n    marker.parent.mkdir(parents=True, exist_ok=True)\n    payload = {\n        "version": 1,\n        "node_id": node_id,\n        "hostname": hostname,\n        "root": str(root),\n    }\n\n    encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\\n").encode("utf-8")\n    try:\n        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)\n    except FileExistsError:\n        existing = _read_marker(marker)\n        if str(existing.get("node_id", "")).casefold() != node_id.casefold():\n            raise RootOwnershipConflict(\n                "ROOT_OWNERSHIP_CONFLICT: QuoteSnap root is owned by "\n                f"{existing.get(\'hostname\', existing.get(\'node_id\'))} "\n                f"({existing.get(\'node_id\')}); local node is {hostname} ({node_id}). "\n                "Use a machine-local V3.3_AIO root; never run training from the shared NetworkHub/SMB copy."\n            )\n        return existing\n    else:\n        try:\n            with os.fdopen(fd, "wb") as f:\n                f.write(encoded)\n                f.flush()\n                os.fsync(f.fileno())\n        except Exception:\n            try:\n                marker.unlink()\n            except OSError:\n                pass\n            raise\n        return payload\n', encoding="utf-8", newline="\n")

if sha(ORCH) != NEW[ORCH]:
    s = ORCH.read_text(encoding="utf-8")
    s = s.replace(
        "from Engines.cluster.status import write_cluster_status\n",
        "from Engines.cluster.status import write_cluster_status\nfrom Engines.cluster.root_ownership import ensure_root_ownership\n",
    )
    s = s.replace(
        "    identity = resolve_local_node_identity(preferred_hostname)\n    local_hostname = identity.hostname\n",
        "    identity = resolve_local_node_identity(preferred_hostname)\n    ensure_root_ownership(ROOT, node_id=identity.node_id, hostname=identity.hostname)\n    local_hostname = identity.hostname\n",
    )
    ORCH.write_text(s, encoding="utf-8", newline="\n")

if sha(DASH) != NEW[DASH]:
    s = DASH.read_text(encoding="utf-8")
    s = s.replace("import time\n", "import time\nimport ctypes\n")
    s = s.replace(
        "from Engines.cluster.identity import FROZEN_NODE_HOSTNAME_ENV, LocalNodeIdentity, resolve_local_node_identity\n",
        "from Engines.cluster.identity import FROZEN_NODE_HOSTNAME_ENV, LocalNodeIdentity, resolve_local_node_identity\nfrom Engines.cluster.root_ownership import ensure_root_ownership\n",
    )
    s = s.replace(
        'ANSI_RE = re.compile(r"\\x1b\\[[0-9;?]*[A-Za-z]")\n',
        'ANSI_RE = re.compile(r"\\x1b\\[[0-9;?]*[A-Za-z]")\nTERMINAL_MODE = "ansi"\n',
    )
    old = 'def prepare_terminal() -> None:\n    """Clear once, position at home, and hide the cursor.\n\n    V3.2/V3.3 previously invoked ``cls`` on every 50 ms render. That creates a\n    visible blank frame on Windows. From this point onward redraws only move the\n    cursor home and replace one fixed-size frame in a single buffered write.\n    """\n    sys.stdout.write("\\x1b[2J\\x1b[H\\x1b[?25l")\n    sys.stdout.flush()\n\n\ndef restore_terminal() -> None:\n    sys.stdout.write("\\x1b[?25h\\n")\n    sys.stdout.flush()\n'
    new = 'def _enable_windows_vt() -> bool:\n    if os.name != "nt":\n        return True\n    try:\n        kernel32 = ctypes.windll.kernel32\n        handle = kernel32.GetStdHandle(-11)\n        mode = ctypes.c_uint32()\n        if handle in (0, -1) or not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):\n            return False\n        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))\n    except Exception:\n        return False\n\n\ndef _win32_home() -> bool:\n    if os.name != "nt":\n        return False\n    try:\n        kernel32 = ctypes.windll.kernel32\n        handle = kernel32.GetStdHandle(-11)\n        # COORD packs X and Y into the low/high 16-bit words. (0,0) == 0.\n        return bool(kernel32.SetConsoleCursorPosition(handle, 0))\n    except Exception:\n        return False\n\n\ndef prepare_terminal() -> str:\n    """Prepare a stable in-place renderer without emitting unsupported ANSI."""\n    global TERMINAL_MODE\n    if os.name == "nt" and not _enable_windows_vt():\n        TERMINAL_MODE = "win32"\n        os.system("cls")\n        _win32_home()\n        return TERMINAL_MODE\n    TERMINAL_MODE = "ansi"\n    sys.stdout.write("\\x1b[2J\\x1b[H\\x1b[?25l")\n    sys.stdout.flush()\n    return TERMINAL_MODE\n\n\ndef restore_terminal() -> None:\n    if TERMINAL_MODE == "ansi":\n        sys.stdout.write("\\x1b[?25h\\n")\n    else:\n        sys.stdout.write("\\n")\n    sys.stdout.flush()\n'
    if old not in s:
        raise SystemExit("DASH_PREPARE_BLOCK_NOT_FOUND")
    s = s.replace(old, new)
    s = s.replace('def render(state, gpu, cluster, health, log_name):\n    frame = build_frame(state, gpu, cluster, health, log_name)\n    # One cursor move + one buffered write. Never clear the terminal between frames.\n    sys.stdout.write("\\x1b[H" + frame)\n    sys.stdout.flush()\n', 'def render(state, gpu, cluster, health, log_name):\n    frame = build_frame(state, gpu, cluster, health, log_name)\n    if TERMINAL_MODE == "win32":\n        _win32_home()\n        sys.stdout.write(strip_ansi(frame))\n    else:\n        # One cursor move + one buffered write. Never clear the terminal between frames.\n        sys.stdout.write("\\x1b[H" + frame)\n    sys.stdout.flush()\n')
    s = s.replace('    cluster_cfg = _load_json(CLUSTER_CONFIG)\n    child_env, frozen_identity = build_child_environment(cluster_cfg)\n    proc = subprocess.Popen(\n', '    cluster_cfg = _load_json(CLUSTER_CONFIG)\n    child_env, frozen_identity = build_child_environment(cluster_cfg)\n    ensure_root_ownership(\n        ROOT, node_id=frozen_identity.node_id, hostname=frozen_identity.hostname\n    )\n    proc = subprocess.Popen(\n')
    DASH.write_text(s, encoding="utf-8", newline="\n")

for path, expected in NEW.items():
    actual = sha(path)
    if actual != expected:
        raise SystemExit(f"PATCH_HASH_MISMATCH {path} {actual} expected={expected}")
    print(f"PATCH_HASH_PASS {path.name} {actual}")

print("PATCH_APPLY_PASS")
