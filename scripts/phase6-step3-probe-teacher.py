#!/usr/bin/env python3
"""Diagnostic-only Step-3 Qwen semantic probe.

This script never writes replay/training truth. It only measures which bounded,
independently anchorable paraphrases the existing structured teacher adapter can
resolve so the frozen Step-3 lesson set can be chosen from real evidence.
"""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


PROBES = (
    ("fox", "orange wild animal with a bushy tail"),
    ("laptop", "portable computer with a keyboard and screen"),
    ("chair", "seat with four legs and a back"),
    ("toothbrush", "plastic brush used for cleaning teeth"),
    ("fire engine", "emergency truck used by firefighters"),
    ("credit card", "card used to pay for purchases"),
    ("robot", "machine designed to carry out tasks automatically"),
    ("dog", "domestic animal that barks"),
    ("bicycle", "vehicle powered by pedals with two wheels"),
    ("key", "small metal object that opens a lock"),
)


def main() -> None:
    adapter = load("_p6s3_probe_adapter", ROOT / "🔌" / "🧠")
    connector = adapter.build_current_intelligence_connector()
    resolved = 0
    for concept, source in PROBES:
        result = connector.invoke_internal("🦙", {"source": source})
        payload = result.payload if isinstance(result.payload, dict) else {}
        is_resolved = bool(result.called and result.ok and payload.get("resolvable") is True)
        resolved += int(is_resolved)
        print(
            "TEACHER_PROBE "
            f"concept={concept!r} source={source!r} called={result.called} ok={result.ok} "
            f"resolved={is_resolved} definition={str(payload.get('definition',''))!r} "
            f"confidence={payload.get('confidence',None)!r} error={result.error_code!r}",
            flush=True,
        )
    print(f"PHASE6_STEP3_TEACHER_PROBE resolved={resolved}/{len(PROBES)} truth_written=0", flush=True)


if __name__ == "__main__":
    main()
