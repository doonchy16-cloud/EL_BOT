#!/usr/bin/env python3
"""Train Forgey Insta G1's native visual adapter from deterministic pixel truth."""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import sys

import torch

ROOT = Path(__file__).resolve().parent.parent


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path)); spec = spec_from_loader(name, loader)
    if spec is None: raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec); sys.modules[name] = module; loader.exec_module(module); return module


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", default=str(ROOT / "data" / "phase6-step2"))
    parser.add_argument("--steps", type=int, default=360)
    parser.add_argument("--batch-size", type=int, default=28)
    parser.add_argument("--seed", type=int, default=640260818)
    args = parser.parse_args()

    artifact = Path(args.artifact_dir).resolve()
    tokenizer_path = artifact / "tokenizer.json"; checkpoint_path = artifact / "forgey-insta-g1.pt"; proof_path = artifact / "training-proof.json"
    for path in (tokenizer_path, checkpoint_path, proof_path):
        if not path.is_file(): raise FileNotFoundError(f"required G1 artifact missing: {path}")

    tokenizer_module = load("_p6s2vision_tokenizer", ROOT / "📚" / "✂️")
    model_module = load("_p6s2vision_model", ROOT / "🧠" / "🤖")
    vision = load("_p6s2vision_curriculum", ROOT / "🧠" / "👁️")
    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path)
    model, metadata = model_module.ForgeyInstaTransformer.load_checkpoint(checkpoint_path, map_location="cpu")
    if str(metadata.get("generation")) != "G1": raise RuntimeError("native-vision parent is not G1")
    if not model.config.vision_enabled: raise RuntimeError("Forgey G1 visual branch is disabled")
    model.to(torch.device("cpu"))

    before_report = model.parameter_report()
    visual = vision.train_visual_adapter(model, tokenizer, steps=args.steps, batch_size=args.batch_size, seed=args.seed, device="cpu")
    if int(visual["provider_generated_truth_count"]) != 0 or int(visual["unverified_self_output_truth_count"]) != 0:
        raise RuntimeError("native visual curriculum violated truth boundary")
    if int(visual["probe_exact_count"]) != int(visual["probe_total"]):
        raise RuntimeError(f"held-out native visual probes not exact: {visual['probe_exact_count']}/{visual['probe_total']}")
    if float(visual["late_loss"]) > float(visual["early_loss"]) * 0.80:
        raise RuntimeError(f"native visual adapter did not materially learn: {visual['early_loss']}->{visual['late_loss']}")

    text_probes = {
        ("ABC_TO_EL", "rocket"): "🚀",
        ("EL_TO_ABC", "🚀"): "rocket",
        ("ABC_TO_EL", "bicycle"): "🚲",
        ("EL_TO_ABC", "🚲"): "bicycle",
    }
    text_rows = []
    for (direction, source), expected in text_probes.items():
        prediction = model.greedy_generate(tokenizer, direction, source, max_new_tokens=24, device="cpu")
        text_rows.append({"direction": direction, "source": source, "expected": expected, "prediction": prediction, "exact": prediction.casefold() == expected.casefold()})
    if not all(item["exact"] for item in text_rows): raise RuntimeError("native vision adapter regressed protected text probes")

    metadata.update({
        "vision_enabled": True,
        "vision_training_steps": int(args.steps),
        "vision_training_seed": int(args.seed),
        "vision_truth_source": visual["truth_source"],
        "vision_probe_exact": f"{visual['probe_exact_count']}/{visual['probe_total']}",
    })
    model.save_checkpoint(checkpoint_path, metadata=metadata)
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    after_report = model.parameter_report()
    proof["vision"] = {
        **visual,
        "enabled": True,
        "modality": "native pixels",
        "image_size": int(model.config.vision_image_size),
        "patch_size": int(model.config.vision_patch_size),
        "visual_tokens": int(model.config.visual_token_count),
        "vision_parameters": int(after_report.vision_parameters),
        "trainable_parameters": int(after_report.trainable_parameters),
        "protected_text_probes": text_rows,
    }
    proof.setdefault("g1", {})["checkpoint_sha256"] = file_sha256(checkpoint_path)
    proof["g1"]["native_vision_enabled"] = True
    proof["g1"]["native_vision_probe_exact"] = f"{visual['probe_exact_count']}/{visual['probe_total']}"
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if before_report.trainable_parameters != after_report.trainable_parameters:
        raise RuntimeError("visual adapter training changed model graph size")
    print(
        "PHASE6_STEP2_NATIVE_VISION_OK "
        f"params={after_report.trainable_parameters} vision_params={after_report.vision_parameters} "
        f"loss={visual['early_loss']:.4f}->{visual['late_loss']:.4f} probes={visual['probe_exact_count']}/{visual['probe_total']} provider=0",
        flush=True,
    )


if __name__ == "__main__": main()
