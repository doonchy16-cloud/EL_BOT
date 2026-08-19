#!/usr/bin/env python3
"""Prove Forgey G2 from the built Windows package, not from the source runtime."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str], *, cwd: Path, env: dict[str, str], stdin: str | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        input=stdin,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"command failed {result.returncode}: {result.stderr[-1200:]}")
    return result


def parse_one_json(stdout: str) -> dict:
    text = stdout.strip()
    if not text.startswith("{") or not text.endswith("}"):
        raise RuntimeError(f"expected one JSON object, got: {text[:400]!r}")
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", default=str(ROOT / "dist" / "win-unpacked" / "resources" / "app"))
    parser.add_argument("--output", default=str(ROOT / "dist" / "phase6-package-forgey-proof.json"))
    args = parser.parse_args()

    app_root = Path(args.app_root).resolve()
    packaged_python = app_root / "python" / "python.exe"
    runtime = app_root / (chr(0x2194) + chr(0xFE0F)) / chr(0x26A1)
    registry = app_root / "data" / "phase6-step3" / "generation-registry.json"
    status_script = app_root / "scripts" / "phase6-step4-status.py"
    admin_script = app_root / "scripts" / "phase6-step4-admin-action.py"
    architecture_manifest = app_root / "architecture" / "phase6_step4_runtime_console_manifest.json"
    required = [packaged_python, runtime, registry, status_script, admin_script, architecture_manifest]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("packaged Phase-6 runtime files missing: " + ", ".join(missing))

    env = dict(os.environ)
    env.pop("EL_PYTHON", None)
    env["PYTHONIOENCODING"] = "utf-8"
    env["EL_FORGEY_REGISTRY"] = str(registry)

    torch = run(
        [str(packaged_python), "-c", "import sys,torch;assert sys.version_info[:2]==(3,12);assert torch.__version__.startswith('2.13.0');print(torch.__version__)"],
        cwd=app_root,
        env=env,
        timeout=30,
    ).stdout.strip()

    forward = parse_one_json(run(
        [str(packaged_python), str(runtime), chr(0x1F500)],
        cwd=app_root,
        env=env,
        stdin="2\nvehicle powered by pedals with two wheels",
    ).stdout)
    bicycle = chr(0x1F6B2)
    reverse = parse_one_json(run(
        [str(packaged_python), str(runtime), chr(0x1F500)],
        cwd=app_root,
        env=env,
        stdin="1\n" + bicycle,
    ).stdout)

    fm = dict(forward.get("metrics") or {})
    rm = dict(reverse.get("metrics") or {})
    if forward.get("winner") != bicycle:
        raise AssertionError(f"packaged forward mismatch: {forward.get('winner')!r}")
    if str(reverse.get("winner") or "").strip().rstrip(".!?").casefold() != "bicycle":
        raise AssertionError(f"packaged reverse mismatch: {reverse.get('winner')!r}")
    for metrics in (fm, rm):
        if metrics.get("forgey_primary_released") is not True:
            raise AssertionError("packaged Forgey primary did not release")
        if metrics.get("forgey_generation") != "G2":
            raise AssertionError("packaged selected generation is not G2")
        if int(metrics.get("provider_calls", -1)) != 0:
            raise AssertionError("packaged successful Forgey inference called provider")
        if float(metrics.get("roundtrip", 0) or 0) != 1.0:
            raise AssertionError("packaged Forgey round-trip failed")

    status = parse_one_json(run(
        [str(packaged_python), str(status_script), "--registry", str(registry), "--validate"],
        cwd=app_root,
        env=env,
        timeout=60,
    ).stdout)
    reg = dict(status.get("registry") or {})
    model = dict(status.get("model") or {})
    diagnostics = dict(status.get("diagnostics") or {})
    if reg.get("selected_generation") != "G2" or reg.get("hashes_verified") is not True:
        raise AssertionError("packaged registry/hash proof failed")
    if model.get("loadable") is not True or int(model.get("trainable_parameters") or 0) != 1788672:
        raise AssertionError("packaged model load/parameter proof failed")
    if int(model.get("model_file_bytes") or 0) <= 0 or int(model.get("tokenizer_file_bytes") or 0) <= 0:
        raise AssertionError("packaged model/tokenizer size proof failed")
    if diagnostics.get("passed") is not True or int(diagnostics.get("count") or 0) != 44:
        raise AssertionError("packaged diagnostics not 44/44")

    evidence = {
        "schema_version": 1,
        "phase": 6,
        "step": 5,
        "app_root": str(app_root),
        "embedded_python": True,
        "embedded_torch": torch,
        "registry": str(registry.relative_to(app_root)).replace("\\", "/"),
        "selected_generation": "G2",
        "registry_hashes_verified": True,
        "trainable_parameters": int(model["trainable_parameters"]),
        "model_file_bytes": int(model["model_file_bytes"]),
        "tokenizer_file_bytes": int(model["tokenizer_file_bytes"]),
        "forward_winner": forward["winner"],
        "reverse_winner": reverse["winner"],
        "forward_provider_calls": int(fm["provider_calls"]),
        "reverse_provider_calls": int(rm["provider_calls"]),
        "forward_roundtrip": float(fm["roundtrip"]),
        "reverse_roundtrip": float(rm["roundtrip"]),
        "diagnostics": "44/44",
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PHASE6_STEP5_PACKAGE_FORGEY_OK selected=G2 provider=0 torch=" + torch + " diagnostics=44/44")


if __name__ == "__main__":
    main()
