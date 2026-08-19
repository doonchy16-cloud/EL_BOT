#!/usr/bin/env python3
"""Rehearse G1 on trusted probes and the deterministic native-vision semantic bridge.

This is still Phase-6 Step 2 bootstrap training. It uses only deterministic trusted
truth: the existing Step-2 curriculum plus the independently-known visual concepts
from the native-vision curriculum. There is no provider/teacher or self-output
learning path here. The pixel adapter is trained only after this decoder bridge is
proven exact.
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


def _predict_pairs(model, tokenizer, expected, device):
    rows = []
    for (direction, source), target in expected.items():
        prediction = model.greedy_generate(tokenizer, direction, source, max_new_tokens=24, device=device)
        rows.append({
            "direction": direction,
            "source": source,
            "expected": target,
            "prediction": prediction,
            "exact": prediction.casefold() == target.casefold(),
        })
    return rows


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
    vision_module = load("_p6s2_rehearse_vision", ROOT / "🧠" / "👁️")
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
    bridge_expected = {}
    for item in vision_module.CONCEPTS:
        bridge_expected[("ABC_TO_EL", item.abc)] = item.el
        bridge_expected[("EL_TO_ABC", item.el)] = item.abc
    overlap = tuple(key for key in bridge_expected if key in forbidden_keys)
    if overlap:
        raise RuntimeError(f"native-vision semantic bridge overlaps frozen benchmark: {overlap}")

    encoded_by_key = {}
    replay_rows = []
    replay_weights = []
    required_expected = {**smoke_expected, **bridge_expected}
    for example in curriculum:
        encoded = trainer_module.encode_example(tokenizer, example.direction, example.source, example.target, model.config.max_context)
        if encoded is None:
            continue
        replay_rows.append(encoded)
        replay_weights.append(max(1, int(example.weight)))
        expected = required_expected.get(example.key)
        if expected is not None and example.target.casefold() == expected.casefold():
            current = encoded_by_key.get(example.key)
            if current is None or int(example.weight) > current[0]:
                encoded_by_key[example.key] = (int(example.weight), encoded)

    # Some deterministic visual phrases intentionally normalize official Unicode names
    # (for example "check mark"). They are still independently-known Step-2 truth and
    # may be encoded directly when that exact normalized pair is not present in 🌱.
    for key, expected in required_expected.items():
        if key in encoded_by_key:
            continue
        encoded = trainer_module.encode_example(tokenizer, key[0], key[1], expected, model.config.max_context)
        if encoded is not None:
            encoded_by_key[key] = (1, encoded)

    missing_smoke = tuple(key for key in smoke_expected if key not in encoded_by_key)
    missing_bridge = tuple(key for key in bridge_expected if key not in encoded_by_key)
    if missing_smoke:
        raise RuntimeError(f"trusted rehearsal probes unavailable: {missing_smoke}")
    if missing_bridge:
        raise RuntimeError(f"deterministic visual semantic bridge unavailable: {missing_bridge}")
    if not replay_rows:
        raise RuntimeError("broad replay set is empty")

    smoke_rows = [encoded_by_key[key][1] for key in smoke_expected]
    bridge_rows = [encoded_by_key[key][1] for key in bridge_expected]
    focus_rows = smoke_rows + bridge_rows

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
    requested_steps = max(1, int(args.steps))
    smoke_batch = max(8, int(args.batch_size) // 4)
    bridge_batch = max(12, int(args.batch_size) // 2)
    if smoke_batch + bridge_batch >= int(args.batch_size):
        bridge_batch = max(1, int(args.batch_size) - smoke_batch - 1)
    replay_batch = max(1, int(args.batch_size) - smoke_batch - bridge_batch)

    def train_step(selected_rows):
        source, decoder, labels = trainer_module.collate(selected_rows, tokenizer.pad_id, device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(source, decoder)
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1), ignore_index=-100)
        if not torch.isfinite(loss):
            raise RuntimeError("non-finite rehearsal loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        losses.append(float(loss.item()))

    for step in range(requested_steps):
        selected_smoke = [smoke_rows[index] for index in rng.choices(range(len(smoke_rows)), k=smoke_batch)]
        selected_bridge = [bridge_rows[index] for index in rng.choices(range(len(bridge_rows)), k=bridge_batch)]
        selected_replay = [replay_rows[index] for index in rng.choices(range(len(replay_rows)), weights=replay_weights, k=replay_batch)]
        rows = selected_smoke + selected_bridge + selected_replay
        rng.shuffle(rows)
        train_step(rows)
        if (step + 1) % 60 == 0 or step == 0:
            print(f"G1_REHEARSE step={step + 1}/{requested_steps} loss={losses[-1]:.6f}", flush=True)

    # Exact semantic readiness is a prerequisite for pixel grounding. If the normal
    # rehearsal did not lock every trusted pair, run a bounded deterministic repair
    # curriculum while retaining broad replay. This teaches the decoder; it does not
    # see pixels and cannot use model self-output as truth.
    repair_limit = 360
    repair_used = 0
    model.eval()
    smoke_predictions = _predict_pairs(model, tokenizer, smoke_expected, device)
    bridge_predictions = _predict_pairs(model, tokenizer, bridge_expected, device)
    while (not all(row["exact"] for row in smoke_predictions + bridge_predictions)) and repair_used < repair_limit:
        model.train()
        for _ in range(min(60, repair_limit - repair_used)):
            focus_batch = max(1, int(args.batch_size) - 4)
            selected_focus = [focus_rows[index] for index in rng.choices(range(len(focus_rows)), k=focus_batch)]
            selected_replay = [replay_rows[index] for index in rng.choices(range(len(replay_rows)), weights=replay_weights, k=4)]
            rows = selected_focus + selected_replay
            rng.shuffle(rows)
            train_step(rows)
            repair_used += 1
        model.eval()
        smoke_predictions = _predict_pairs(model, tokenizer, smoke_expected, device)
        bridge_predictions = _predict_pairs(model, tokenizer, bridge_expected, device)
        exact_smoke = sum(1 for row in smoke_predictions if row["exact"])
        exact_bridge = sum(1 for row in bridge_predictions if row["exact"])
        print(f"G1_SEMANTIC_BRIDGE repair={repair_used}/{repair_limit} smoke={exact_smoke}/{len(smoke_predictions)} visual={exact_bridge}/{len(bridge_predictions)}", flush=True)

    if not all(row["exact"] for row in smoke_predictions):
        for row in smoke_predictions:
            if not row["exact"]: print("G1_SMOKE_MISS", json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
        raise RuntimeError("trusted rehearsal probes are not all exact after bounded repair")
    if not all(row["exact"] for row in bridge_predictions):
        for row in bridge_predictions:
            if not row["exact"]: print("G1_VISUAL_SEMANTIC_MISS", json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
        raise RuntimeError("deterministic visual semantic bridge is not exact after bounded repair")

    post_benchmark = trainer_module.token_loss(model, benchmark_rows, tokenizer.pad_id, device)
    previous_steps = int(metadata.get("training_steps") or proof.get("g1", {}).get("training_steps") or 0)
    actual_steps = requested_steps + repair_used
    metadata.update({
        "generation": "G1",
        "training_steps": previous_steps + actual_steps,
        "broad_training_steps": previous_steps,
        "rehearsal_steps": actual_steps,
        "rehearsal_seed": int(args.seed),
        "visual_semantic_bridge_exact": f"{len(bridge_predictions)}/{len(bridge_predictions)}",
    })
    model.save_checkpoint(checkpoint_path, metadata=metadata)
    checkpoint_sha = file_sha256(checkpoint_path)

    window = min(30, max(5, len(losses) // 5))
    rehearsal_early = sum(losses[:window]) / window
    rehearsal_late = sum(losses[-window:]) / window
    g0_benchmark = float(proof["g0"]["frozen_benchmark_loss"])
    g1 = proof["g1"]
    g1.update({
        "training_steps": previous_steps + actual_steps,
        "broad_training_steps": previous_steps,
        "rehearsal_steps": actual_steps,
        "rehearsal_requested_steps": requested_steps,
        "semantic_bridge_repair_steps": repair_used,
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
        "steps": actual_steps,
        "requested_steps": requested_steps,
        "semantic_bridge_repair_steps": repair_used,
        "batch_size": int(args.batch_size),
        "smoke_examples_per_batch": smoke_batch,
        "visual_semantic_examples_per_batch": bridge_batch,
        "broad_replay_examples_per_batch": replay_batch,
    }
    proof["visual_semantic_bridge"] = {
        "truth_source": "deterministic native-vision concept authority",
        "provider_generated_truth_count": 0,
        "unverified_self_output_truth_count": 0,
        "pair_total": len(bridge_predictions),
        "pair_exact_count": sum(1 for row in bridge_predictions if row["exact"]),
        "predictions": bridge_predictions,
    }
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "PHASE6_STEP2_REHEARSED "
        f"benchmark={pre_benchmark:.4f}->{post_benchmark:.4f} "
        f"rehearsal={rehearsal_early:.4f}->{rehearsal_late:.4f} "
        f"smoke={g1['smoke_exact_count']}/{g1['smoke_total']} "
        f"visual_semantic={proof['visual_semantic_bridge']['pair_exact_count']}/{proof['visual_semantic_bridge']['pair_total']} "
        f"repair={repair_used}",
        flush=True,
    )


if __name__ == "__main__":
    main()
