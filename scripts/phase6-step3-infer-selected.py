#!/usr/bin/env python3
"""Fresh-process provider-free inference from the registry-selected Forgey generation."""
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
    parser.add_argument("--registry", required=True)
    parser.add_argument("--direction", choices=("ABC_TO_EL", "EL_TO_ABC"), required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--expected", default="")
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    registry_payload = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    selected = str(registry_payload.get("production_generation", ""))
    record = dict(registry_payload.get("generations", {}).get(selected) or {})
    if not selected or not record:
        raise RuntimeError("selected generation missing from registry")

    registry_module = load("_p6s3_infer_registry", ROOT / "🗃️" / "🤖")
    if not registry_module.ForgeyGenerationRegistry(args.registry).verify_generation_hashes(selected):
        raise RuntimeError("selected generation hash verification failed")

    tokenizer_module = load("_p6s3_infer_tokenizer", ROOT / "📚" / "✂️")
    model_module = load("_p6s3_infer_model", ROOT / "🧠" / "🤖")
    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(Path(record["tokenizer_path"]))
    model, metadata = model_module.ForgeyInstaTransformer.load_checkpoint(Path(record["model_path"]), map_location="cpu")
    if model.config.vocab_size != tokenizer.vocab_size:
        raise RuntimeError("selected checkpoint/tokenizer vocabulary mismatch")
    if str(metadata.get("generation")) != selected:
        raise RuntimeError(f"registry selected {selected} but checkpoint metadata is {metadata.get('generation')}")

    prediction = model.greedy_generate(tokenizer, args.direction, args.text, max_new_tokens=32, device="cpu")
    if not prediction:
        raise RuntimeError("selected-generation inference produced empty output")
    exact = prediction.casefold() == args.expected.casefold() if args.expected else None
    evidence = {
        "schema_version": 1,
        "phase": 6,
        "step": 3,
        "kind": "selected-generation-local-inference",
        "torch_version": str(torch.__version__),
        "selected_generation": selected,
        "model_sha256": record["model_sha256"],
        "tokenizer_sha256": record["tokenizer_sha256"],
        "direction": args.direction,
        "source": args.text,
        "prediction": prediction,
        "expected": args.expected or None,
        "exact": exact,
        "provider_calls": 0,
    }
    target = Path(args.evidence)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"FORGEY_INSTA_SELECTED generation={selected} direction={args.direction} source={args.text!r} prediction={prediction!r} exact={exact}",
        flush=True,
    )


if __name__ == "__main__":
    main()
