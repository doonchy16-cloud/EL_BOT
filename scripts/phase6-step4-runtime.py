#!/usr/bin/env python3
"""ASCII-path launcher for the canonical Unicode Step-4 runtime facade."""
from __future__ import annotations
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "↔️" / "⚡"
loader = SourceFileLoader("_el_step4_runtime_launcher", str(TARGET))
spec = spec_from_loader("_el_step4_runtime_launcher", loader)
if spec is None:
    raise RuntimeError("Step-4 runtime module unavailable")
module = module_from_spec(spec)
sys.modules["_el_step4_runtime_launcher"] = module
loader.exec_module(module)

if __name__ == "__main__":
    raise SystemExit(module.main())
