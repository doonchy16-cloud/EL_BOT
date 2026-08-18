#!/usr/bin/env python3
"""Load a saved Forgey Insta G1 artifact and perform provider-free local inference."""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import sys

import torch

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", default=str(ROOT / "data" / "phase6-step2"))
    parser.add_argument("--direction", required=True, choices=("ABC_TO_EL", "EL_TO_ABC"))
    parser.add_argument("--text", required=True)
    parser.add_argument("--expected", default="")
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    artifact = Path(args.artifact_dir)
    tokenizer_module = load("_p6s2_infer_tokenizer", ROOT / "📚" / "✂️")
    model_module = load("_p6s2_infer_model", ROOT / "🧠" / "🤖")
    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(artifact / "tokenizer.json")
    model, metadata = model_module.ForgeyInstaTransformer.load_checkpoint(artifact / "forgey-insta-g1.pt", map_location="cpu")
    report = model.parameter_report()
    if model.config.vocab_size != tokenizer.vocab_size:
        raise RuntimeError("checkpoint/tokenizer vocabulary mismatch")
    prediction = model.greedy_generate(tokenizer, args.direction, args.text, max_new_tokens=32, device="cpu")
    if not prediction:
        raise RuntimeError("local G1 inference produced an empty candidate")

    exact = prediction.casefold() == args.expected.casefold() if args.expected else None
    evidence = {
        "schema_version": 1,
        "phase": 6,
        "step": 2,
        "kind": "local-g1-inference",
        "torch_version": str(torch.__version__),
        "direction": args.direction,
        "source": args.text,
        "prediction": prediction,
        "expected": args.expected or None,
        "exact": exact,
        "generation": metadata.get("generation"),
        "checkpoint_training_steps": metadata.get("training_steps"),
        "trainable_parameters": report.trainable_parameters,
        "provider_calls": 0,
    }
    target = Path(args.evidence)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"FORGEY_INSTA_LOCAL direction={args.direction} source={args.text!r} prediction={prediction!r} exact={exact}",
        flush=True,
    )


if __name__ == "__main__":
    main()
