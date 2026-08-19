#!/usr/bin/env python3
"""Fresh-process provider-free Forgey Insta native vision inference."""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import base64
import json
import sys

import torch

ROOT = Path(__file__).resolve().parent.parent


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path)); spec = spec_from_loader(name, loader)
    if spec is None: raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec); sys.modules[name] = module; loader.exec_module(module); return module


def resolve_generation(args):
    if bool(args.artifact_dir) == bool(args.registry):
        raise ValueError("provide exactly one of --artifact-dir or --registry")
    if args.artifact_dir:
        root = Path(args.artifact_dir).resolve()
        return "G1", root / "forgey-insta-g1.pt", root / "tokenizer.json", None
    registry_path = Path(args.registry).resolve()
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    selected = str(payload.get("production_generation") or "")
    record = dict((payload.get("generations") or {}).get(selected) or {})
    if not selected or not record: raise RuntimeError("selected generation missing")
    model_path = Path(str(record.get("model_path") or ""))
    tokenizer_path = Path(str(record.get("tokenizer_path") or ""))
    if not model_path.is_absolute(): model_path = (registry_path.parent.parent.parent / model_path).resolve() if str(model_path).startswith("data/") else (Path.cwd() / model_path).resolve()
    if not tokenizer_path.is_absolute(): tokenizer_path = (registry_path.parent.parent.parent / tokenizer_path).resolve() if str(tokenizer_path).startswith("data/") else (Path.cwd() / tokenizer_path).resolve()
    return selected, model_path, tokenizer_path, record


def image_bytes(args, vision):
    if args.fixture_concept:
        tensor = vision.render_concept(args.fixture_concept, args.fixture_seed)
        return vision.encode_png(tensor), "fixture:" + args.fixture_concept
    if args.image_file:
        return Path(args.image_file).read_bytes(), str(Path(args.image_file))
    value = str(args.image_base64 or "").strip()
    if not value: raise ValueError("vision input missing")
    if value.startswith("data:"):
        marker = ";base64,"; at = value.find(marker)
        if at < 0: raise ValueError("image data URL is not base64")
        value = value[at + len(marker):]
    return base64.b64decode(value, validate=True), "base64"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--direction", choices=("IMAGE_TO_EL", "IMAGE_TO_ABC"), required=True)
    parser.add_argument("--fixture-concept", default="")
    parser.add_argument("--fixture-seed", type=int, default=9000)
    parser.add_argument("--image-file", default="")
    parser.add_argument("--image-base64", default="")
    parser.add_argument("--expected", default="")
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    tokenizer_module = load("_p6vision_tokenizer", ROOT / "📚" / "✂️")
    model_module = load("_p6vision_model", ROOT / "🧠" / "🤖")
    vision = load("_p6vision_pixels", ROOT / "🧠" / "👁️")
    generation, model_path, tokenizer_path, record = resolve_generation(args)
    if not model_path.is_file() or not tokenizer_path.is_file(): raise FileNotFoundError("Forgey vision model/tokenizer missing")
    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path)
    model, metadata = model_module.ForgeyInstaTransformer.load_checkpoint(model_path, map_location="cpu")
    if not model.config.vision_enabled: raise RuntimeError("selected Forgey generation is not vision-enabled")
    if model.config.vocab_size != tokenizer.vocab_size: raise RuntimeError("vision checkpoint/tokenizer vocabulary mismatch")
    if str(metadata.get("generation")) != generation: raise RuntimeError("vision generation metadata mismatch")

    raw, source = image_bytes(args, vision)
    image = vision.decode_png(raw)
    prediction, confidence = model.greedy_generate_image(tokenizer, args.direction, image, max_new_tokens=24, device="cpu", return_confidence=True)
    if not prediction: raise RuntimeError("native vision produced empty output")
    exact = prediction.casefold() == args.expected.casefold() if args.expected else None
    report = model.parameter_report()
    evidence = {
        "schema_version": 1,
        "phase": 6,
        "kind": "forgey-native-vision-inference",
        "generation": generation,
        "direction": args.direction,
        "source": source,
        "image_sha256": sha256(raw).hexdigest(),
        "prediction": prediction,
        "expected": args.expected or None,
        "exact": exact,
        "confidence": float(confidence),
        "provider_calls": 0,
        "vision_enabled": bool(model.config.vision_enabled),
        "vision_image_size": int(model.config.vision_image_size),
        "vision_patch_size": int(model.config.vision_patch_size),
        "vision_parameters": int(report.vision_parameters),
        "trainable_parameters": int(report.trainable_parameters),
        "torch_version": str(torch.__version__),
        "registry_model_sha256": (record or {}).get("model_sha256"),
    }
    target = Path(args.evidence); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"FORGEY_NATIVE_VISION generation={generation} direction={args.direction} prediction={prediction!r} confidence={confidence:.4f} exact={exact} provider=0", flush=True)


if __name__ == "__main__": main()
