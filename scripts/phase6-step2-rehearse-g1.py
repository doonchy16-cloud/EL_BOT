#!/usr/bin/env python3
"""Rehearse G1 on trusted non-benchmark probes while retaining broad replay.

This is still Phase-6 Step 2 bootstrap training. It uses only the deterministic
curriculum already admitted by 🧠/🌱; there is no provider/teacher or self-output
learning path here.
"""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import random
import sys

import torch
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "architecture" / "phase6_step2_frozen_benchmark.json"


def load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", default=str(ROOT / "data" / "phase6-step2"))
    parser.add_argument("--steps", type=int, default=240)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=620260819)
    args = parser.parse_args()

    artifact = Path(args.artifact_dir).resolve()
    tokenizer_path = artifact / "tokenizer.json"
    checkpoint_path = artifact / "forgey-insta-g1.pt"
    proof_path = artifact / "training-proof.json"
    if not tokenizer_path.is_file() or not checkpoint_path.is_file() or not proof_path.is_file():
        raise RuntimeError("broad G1 artifacts must exist before rehearsal")

    tokenizer_module = load("_p6s2_rehearse_tokenizer", ROOT / "📚" / "✂️")
    curriculum_module = load("_p6s2_rehearse_curriculum", ROOT / "🧠" / "🌱")
    model_module = load("_p6s2_rehearse_model", ROOT / "🧠" / "🤖")
    trainer_module = load("_p6s2_rehearse_trainer", ROOT / "scripts" / "phase6-step2-train-g1.py")

    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path)
    model, metadata = model_module.ForgeyInstaTransformer.load_checkpoint(checkpoint_path, map_location="cpu")
    device = torch.device("cpu")
    model.to(device)
    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))

    curriculum, _ = curriculum_module.build_bootstrap_curriculum(BENCHMARK)
    benchmark_payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    benchmark_items = tuple(benchmark_payload["examples"])
    forbidden_keys = {(str(item["direction"]), str(item["source"])) for item in benchmark_items}
    if any(example.key in forbidden_keys for example in curriculum):
        raise RuntimeError("frozen benchmark leaked into rehearsal curriculum")

    smoke_expected = {
        ("ABC_TO_EL", "bicycle"): "🚲",
        ("ABC_TO_EL", "rocket"): "🚀",
        ("ABC_TO_EL", "camera"): "📷",
        ("ABC_TO_EL", "key"): "🔑",
        ("EL_TO_ABC", "🚲"): "bicycle",
        ("EL_TO_ABC", "🚀"): "rocket",
        ("EL_TO_ABC", "📷"): "camera",
        ("EL_TO_ABC", "🔑"): "key",
    }

    encoded_by_key = {}
    replay_rows = []
    replay_weights = []
    for example in curriculum:
        encoded = trainer_module.encode_example(tokenizer, example.direction, example.source, example.target, model.config.max_context)
        if encoded is None:
            continue
        replay_rows.append(encoded)
        replay_weights.append(max(1, int(example.weight)))
        expected = smoke_expected.get(example.key)
        if expected is not None and example.target.casefold() == expected.casefold():
            current = encoded_by_key.get(example.key)
            if current is None or int(example.weight) > current[0]:
                encoded_by_key[example.key] = (int(example.weight), encoded)

    missing = tuple(key for key in smoke_expected if key not in encoded_by_key)
    if missing:
        raise RuntimeError(f"trusted rehearsal probes absent from curriculum: {missing}")
    smoke_rows = [encoded_by_key[key][1] for key in smoke_expected]
    if not replay_rows:
        raise RuntimeError("broad replay set is empty")

    benchmark_rows = []
    for item in benchmark_items:
        encoded = trainer_module.encode_example(tokenizer, str(item["direction"]), str(item["source"]), str(item["target"]), model.config.max_context)
        if encoded is None:
            raise RuntimeError(f"frozen benchmark exceeds context during rehearsal: {item['id']}")
        benchmark_rows.append(encoded)

    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    pre_benchmark = trainer_module.token_loss(model, benchmark_rows, tokenizer.pad_id, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(0.9, 0.98), weight_decay=0.01)
    rng = random.Random(args.seed)
    losses: list[float] = []
    model.train()
    smoke_batch = max(8, int(args.batch_size) // 2)
    replay_batch = max(1, int(args.batch_size) - smoke_batch)

    for step in range(int(args.steps)):
        selected_smoke = [smoke_rows[index] for index in rng.choices(range(len(smoke_rows)), k=smoke_batch)]
        selected_replay = [replay_rows[index] for index in rng.choices(range(len(replay_rows)), weights=replay_weights, k=replay_batch)]
        rows = selected_smoke + selected_replay
        rng.shuffle(rows)
        source, decoder, labels = trainer_module.collate(rows, tokenizer.pad_id, device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(source, decoder)
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1), ignore_index=-100)
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite rehearsal loss at step {step + 1}")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        losses.append(float(loss.item()))
        if (step + 1) % 60 == 0 or step == 0:
            print(f"G1_REHEARSE step={step + 1}/{args.steps} loss={losses[-1]:.6f}", flush=True)

    model.eval()
    post_benchmark = trainer_module.token_loss(model, benchmark_rows, tokenizer.pad_id, device)
    smoke_predictions = []
    for (direction, source), expected in smoke_expected.items():
        prediction = model.greedy_generate(tokenizer, direction, source, max_new_tokens=24, device=device)
        smoke_predictions.append({
            "direction": direction,
            "source": source,
            "expected": expected,
            "prediction": prediction,
            "exact": prediction.casefold() == expected.casefold(),
        })

    previous_steps = int(metadata.get("training_steps") or proof.get("g1", {}).get("training_steps") or 0)
    metadata.update({
        "generation": "G1",
        "training_steps": previous_steps + int(args.steps),
        "broad_training_steps": previous_steps,
        "rehearsal_steps": int(args.steps),
        "rehearsal_seed": int(args.seed),
    })
    model.save_checkpoint(checkpoint_path, metadata=metadata)
    checkpoint_sha = file_sha256(checkpoint_path)

    window = min(30, max(5, len(losses) // 5))
    rehearsal_early = sum(losses[:window]) / window
    rehearsal_late = sum(losses[-window:]) / window
    g0_benchmark = float(proof["g0"]["frozen_benchmark_loss"])
    g1 = proof["g1"]
    g1.update({
        "training_steps": previous_steps + int(args.steps),
        "broad_training_steps": previous_steps,
        "rehearsal_steps": int(args.steps),
        "rehearsal_seed": int(args.seed),
        "pre_rehearsal_benchmark_loss": pre_benchmark,
        "rehearsal_early_loss": rehearsal_early,
        "rehearsal_late_loss": rehearsal_late,
        "frozen_benchmark_loss": post_benchmark,
        "benchmark_loss_ratio_to_g0": post_benchmark / g0_benchmark if g0_benchmark else None,
        "checkpoint_sha256": checkpoint_sha,
        "smoke_exact_count": sum(1 for item in smoke_predictions if item["exact"]),
        "smoke_total": len(smoke_predictions),
        "smoke_predictions": smoke_predictions,
    })
    proof["g1"] = g1
    proof["rehearsal"] = {
        "truth_source": "trusted deterministic Step-2 curriculum only",
        "provider_generated_truth_count": 0,
        "unverified_self_output_truth_count": 0,
        "benchmark_source_overlap_count": 0,
        "steps": int(args.steps),
        "batch_size": int(args.batch_size),
        "smoke_examples_per_batch": smoke_batch,
        "broad_replay_examples_per_batch": replay_batch,
    }
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "PHASE6_STEP2_REHEARSED "
        f"benchmark={pre_benchmark:.4f}->{post_benchmark:.4f} "
        f"rehearsal={rehearsal_early:.4f}->{rehearsal_late:.4f} "
        f"smoke={g1['smoke_exact_count']}/{g1['smoke_total']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
