#!/usr/bin/env python3
"""Re-align G2's native visual adapter after semantic teacher training."""
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
    parser.add_argument("--step3-artifact", default=str(ROOT / "data" / "phase6-step3"))
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=28)
    parser.add_argument("--seed", type=int, default=640260819)
    args = parser.parse_args()
    step3 = Path(args.step3_artifact).resolve()
    g2_dir = step3 / "generations" / "G2"
    model_path = g2_dir / "forgey-insta-g2.pt"; tokenizer_path = g2_dir / "tokenizer.json"; proof_path = step3 / "g2-training-proof.json"
    for path in (model_path, tokenizer_path, proof_path):
        if not path.is_file(): raise FileNotFoundError(f"required G2 visual input missing: {path}")

    tokenizer_module = load("_p6s3vision_tokenizer", ROOT / "📚" / "✂️")
    model_module = load("_p6s3vision_model", ROOT / "🧠" / "🤖")
    vision = load("_p6s3vision_curriculum", ROOT / "🧠" / "👁️")
    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path)
    model, metadata = model_module.ForgeyInstaTransformer.load_checkpoint(model_path, map_location="cpu")
    if str(metadata.get("generation")) != "G2": raise RuntimeError("native-vision candidate is not G2")
    if not model.config.vision_enabled: raise RuntimeError("G2 native vision branch is disabled")
    model.to(torch.device("cpu"))

    visual = vision.train_visual_adapter(model, tokenizer, steps=args.steps, batch_size=args.batch_size, seed=args.seed, device="cpu")
    if int(visual["provider_generated_truth_count"]) != 0 or int(visual["unverified_self_output_truth_count"]) != 0:
        raise RuntimeError("G2 visual replay violated truth boundary")
    if int(visual["probe_exact_count"]) != int(visual["probe_total"]):
        raise RuntimeError(f"G2 held-out vision probes not exact: {visual['probe_exact_count']}/{visual['probe_total']}")
    if float(visual["late_loss"]) > float(visual["early_loss"]) * 0.82:
        raise RuntimeError(f"G2 visual adapter did not materially learn: {visual['early_loss']}->{visual['late_loss']}")

    protected = {
        ("ABC_TO_EL", "bicycle"): "🚲", ("EL_TO_ABC", "🚲"): "bicycle",
        ("ABC_TO_EL", "rocket"): "🚀", ("EL_TO_ABC", "🚀"): "rocket",
    }
    text_rows = []
    for (direction, source), expected in protected.items():
        prediction = model.greedy_generate(tokenizer, direction, source, max_new_tokens=24, device="cpu")
        text_rows.append({"direction": direction, "source": source, "expected": expected, "prediction": prediction, "exact": prediction.casefold() == expected.casefold()})
    if not all(row["exact"] for row in text_rows): raise RuntimeError("G2 vision refresh regressed protected text inference")

    metadata.update({
        "vision_enabled": True,
        "vision_refresh_steps": int(args.steps),
        "vision_refresh_seed": int(args.seed),
        "vision_truth_source": visual["truth_source"],
        "vision_probe_exact": f"{visual['probe_exact_count']}/{visual['probe_total']}",
    })
    model.save_checkpoint(model_path, metadata=metadata)
    report = model.parameter_report()
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof["vision"] = {
        **visual,
        "enabled": True,
        "modality": "native pixels",
        "image_size": int(model.config.vision_image_size),
        "patch_size": int(model.config.vision_patch_size),
        "visual_tokens": int(model.config.visual_token_count),
        "vision_parameters": int(report.vision_parameters),
        "trainable_parameters": int(report.trainable_parameters),
        "protected_text_probes": text_rows,
    }
    proof.setdefault("baseline_metrics", {})["vision_validation_pass"] = True
    proof["baseline_metrics"]["vision_probe_exact"] = int(visual["probe_total"])
    proof["baseline_metrics"]["vision_probe_total"] = int(visual["probe_total"])
    proof.setdefault("candidate_metrics", {})["vision_validation_pass"] = True
    proof["candidate_metrics"]["vision_probe_exact"] = int(visual["probe_exact_count"])
    proof["candidate_metrics"]["vision_probe_total"] = int(visual["probe_total"])
    proof["artifacts"]["g2_model_sha256"] = file_sha256(model_path)
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "PHASE6_STEP3_NATIVE_VISION_OK "
        f"params={report.trainable_parameters} vision_params={report.vision_parameters} "
        f"loss={visual['early_loss']:.4f}->{visual['late_loss']:.4f} probes={visual['probe_exact_count']}/{visual['probe_total']} provider=0",
        flush=True,
    )


if __name__ == "__main__": main()
