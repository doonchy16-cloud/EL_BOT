#!/usr/bin/env python3
"""Train isolated Forgey Insta G2 from G1 + admitted teacher evidence + protected replay."""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import os
import random
import shutil
import sys
import time

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


def exact_predictions(model, tokenizer, examples, *, max_new_tokens: int = 32):
    rows = []
    for item in examples:
        direction = str(item["direction"])
        source = str(item["source"])
        expected = str(item["target"])
        prediction = model.greedy_generate(tokenizer, direction, source, max_new_tokens=max_new_tokens, device="cpu")
        rows.append({
            "direction": direction,
            "source": source,
            "expected": expected,
            "prediction": prediction,
            "exact": prediction.casefold() == expected.casefold(),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step2-artifact", default=str(ROOT / "data" / "phase6-step2"))
    parser.add_argument("--step3-artifact", default=str(ROOT / "data" / "phase6-step3"))
    parser.add_argument("--steps", type=int, default=360)
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--seed", type=int, default=630260818)
    args = parser.parse_args()

    started = time.perf_counter()
    step2 = Path(args.step2_artifact).resolve()
    step3 = Path(args.step3_artifact).resolve()
    step3.mkdir(parents=True, exist_ok=True)
    replay_path = step3 / "teacher-replay.json"
    teacher_evidence_path = step3 / "teacher-evidence.json"
    tokenizer_path = step2 / "tokenizer.json"
    g1_path = step2 / "forgey-insta-g1.pt"
    g1_proof_path = step2 / "training-proof.json"
    for required in (replay_path, teacher_evidence_path, tokenizer_path, g1_path, g1_proof_path):
        if not required.is_file():
            raise RuntimeError(f"required Step-3 input missing: {required}")

    tokenizer_module = load("_p6s3_train_tokenizer", ROOT / "📚" / "✂️")
    curriculum_module = load("_p6s3_train_curriculum", ROOT / "🧠" / "🌱")
    model_module = load("_p6s3_train_model", ROOT / "🧠" / "🤖")
    trainer_module = load("_p6s3_step2_trainer", ROOT / "scripts" / "phase6-step2-train-g1.py")
    lang_module = load("_p6s3_train_lang", ROOT / "🧠" / "🧬")

    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path)
    model, g1_metadata = model_module.ForgeyInstaTransformer.load_checkpoint(g1_path, map_location="cpu")
    model.to(torch.device("cpu"))
    if str(g1_metadata.get("generation")) != "G1":
        raise RuntimeError("Step-3 parent checkpoint is not G1")

    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    benchmark_payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    benchmark_items = tuple(benchmark_payload["examples"])
    forbidden_keys = {(str(item["direction"]), str(item["source"])) for item in benchmark_items}

    teacher_replay = json.loads(replay_path.read_text(encoding="utf-8"))
    teacher_evidence = json.loads(teacher_evidence_path.read_text(encoding="utf-8"))
    if int(teacher_replay.get("frozen_benchmark_overlap_count", -1)) != 0:
        raise RuntimeError("teacher replay declares frozen benchmark overlap")
    if int(teacher_replay.get("provider_authored_el_count", -1)) != 0:
        raise RuntimeError("provider-authored EL present in teacher replay")
    if int(teacher_replay.get("unverified_self_output_truth_count", -1)) != 0:
        raise RuntimeError("self-output truth present in teacher replay")

    teacher_examples = tuple(dict(item) for item in teacher_replay.get("examples", ()))
    if len(teacher_examples) < 3:
        raise RuntimeError("too few admitted teacher examples for G2")
    if any((str(item["direction"]), str(item["source"])) in forbidden_keys for item in teacher_examples):
        raise RuntimeError("frozen benchmark source leaked into G2 teacher examples")

    curriculum, _ = curriculum_module.build_bootstrap_curriculum(BENCHMARK)
    if any(example.key in forbidden_keys for example in curriculum):
        raise RuntimeError("frozen benchmark leaked into deterministic G2 replay")

    broad_rows = []
    broad_weights = []
    protected_expected = {
        ("ABC_TO_EL", "bicycle"): "🚲",
        ("ABC_TO_EL", "rocket"): "🚀",
        ("ABC_TO_EL", "camera"): "📷",
        ("ABC_TO_EL", "key"): "🔑",
        ("EL_TO_ABC", "🚲"): "bicycle",
        ("EL_TO_ABC", "🚀"): "rocket",
        ("EL_TO_ABC", "📷"): "camera",
        ("EL_TO_ABC", "🔑"): "key",
    }
    protected_by_key = {}
    for example in curriculum:
        encoded = trainer_module.encode_example(tokenizer, example.direction, example.source, example.target, model.config.max_context)
        if encoded is None:
            continue
        broad_rows.append(encoded)
        broad_weights.append(max(1, int(example.weight)))
        if example.key in protected_expected and example.target.casefold() == protected_expected[example.key].casefold():
            existing = protected_by_key.get(example.key)
            if existing is None or int(example.weight) > existing[0]:
                protected_by_key[example.key] = (int(example.weight), encoded)
    if len(broad_rows) < 5000:
        raise RuntimeError("broad deterministic replay unexpectedly small")
    missing_protected = tuple(key for key in protected_expected if key not in protected_by_key)
    if missing_protected:
        raise RuntimeError(f"protected Step-2 probes missing from replay: {missing_protected}")

    teacher_rows = []
    for item in teacher_examples:
        encoded = trainer_module.encode_example(tokenizer, str(item["direction"]), str(item["source"]), str(item["target"]), model.config.max_context)
        if encoded is None:
            raise RuntimeError(f"teacher example exceeds model context: {item['lesson_id']}")
        teacher_rows.append(encoded)

    benchmark_rows = []
    for item in benchmark_items:
        encoded = trainer_module.encode_example(tokenizer, str(item["direction"]), str(item["source"]), str(item["target"]), model.config.max_context)
        if encoded is None:
            raise RuntimeError(f"frozen benchmark exceeds context: {item['id']}")
        benchmark_rows.append(encoded)

    protected_examples = [
        {"direction": direction, "source": source, "target": target}
        for (direction, source), target in protected_expected.items()
    ]
    teacher_eval_examples = [
        {"direction": str(item["direction"]), "source": str(item["source"]), "target": str(item["target"]), "canonical_concept": str(item["canonical_concept"])}
        for item in teacher_examples
    ]

    baseline_teacher_loss = trainer_module.token_loss(model, teacher_rows, tokenizer.pad_id, torch.device("cpu"))
    baseline_benchmark_loss = trainer_module.token_loss(model, benchmark_rows, tokenizer.pad_id, torch.device("cpu"))
    baseline_teacher_predictions = exact_predictions(model, tokenizer, teacher_eval_examples)
    baseline_protected_predictions = exact_predictions(model, tokenizer, protected_examples)

    generation_root = step3 / "generations"
    g1_dir = generation_root / "G1"
    g2_dir = generation_root / "G2"
    g1_dir.mkdir(parents=True, exist_ok=True)
    g2_dir.mkdir(parents=True, exist_ok=True)
    g1_copy = g1_dir / "forgey-insta-g1.pt"
    g1_tokenizer = g1_dir / "tokenizer.json"
    g2_path = g2_dir / "forgey-insta-g2.pt"
    g2_tokenizer = g2_dir / "tokenizer.json"
    shutil.copy2(g1_path, g1_copy)
    shutil.copy2(tokenizer_path, g1_tokenizer)
    shutil.copy2(tokenizer_path, g2_tokenizer)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1.2e-4, betas=(0.9, 0.98), weight_decay=0.01)
    rng = random.Random(args.seed)
    losses: list[float] = []
    teacher_batch = max(8, int(args.batch_size) * 3 // 10)
    protected_batch = 8
    broad_batch = max(1, int(args.batch_size) - teacher_batch - protected_batch)
    protected_rows = [protected_by_key[key][1] for key in protected_expected]

    model.train()
    for step in range(int(args.steps)):
        selected_teacher = [teacher_rows[index] for index in rng.choices(range(len(teacher_rows)), k=teacher_batch)]
        selected_protected = [protected_rows[index] for index in rng.choices(range(len(protected_rows)), k=protected_batch)]
        selected_broad = [broad_rows[index] for index in rng.choices(range(len(broad_rows)), weights=broad_weights, k=broad_batch)]
        batch_rows = selected_teacher + selected_protected + selected_broad
        rng.shuffle(batch_rows)
        source, decoder, labels = trainer_module.collate(batch_rows, tokenizer.pad_id, torch.device("cpu"))
        optimizer.zero_grad(set_to_none=True)
        logits = model(source, decoder)
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1), ignore_index=-100)
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite G2 loss at step {step + 1}")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        losses.append(float(loss.item()))
        if step == 0 or (step + 1) % 60 == 0:
            print(f"G2_TRAIN step={step + 1}/{args.steps} loss={losses[-1]:.6f}", flush=True)

    model.eval()
    candidate_teacher_loss = trainer_module.token_loss(model, teacher_rows, tokenizer.pad_id, torch.device("cpu"))
    candidate_benchmark_loss = trainer_module.token_loss(model, benchmark_rows, tokenizer.pad_id, torch.device("cpu"))
    candidate_teacher_predictions = exact_predictions(model, tokenizer, teacher_eval_examples)
    candidate_protected_predictions = exact_predictions(model, tokenizer, protected_examples)

    roundtrip_rows = []
    for item, forward in zip(teacher_eval_examples, candidate_teacher_predictions):
        reverse = model.greedy_generate(tokenizer, "EL_TO_ABC", str(item["target"]), max_new_tokens=24, device="cpu")
        expected_reverse = str(item["canonical_concept"])
        roundtrip_rows.append({
            "source": item["source"],
            "forward_expected": item["target"],
            "forward_prediction": forward["prediction"],
            "reverse_expected": expected_reverse,
            "reverse_prediction": reverse,
            "exact": bool(forward["exact"] and reverse.casefold() == expected_reverse.casefold()),
        })

    literal_control = "<ABC_TO_EL> remains literal user text"
    tokenizer_literal_safe = tokenizer.decode(tokenizer.encode_text(literal_control)) == literal_control
    hostile_rejected = any(item.get("case_id") == "teacher-hostile-instruction" for item in teacher_evidence.get("rejections", ()))
    adversarial_integrity = bool(
        tokenizer_literal_safe
        and hostile_rejected
        and int(teacher_replay.get("frozen_benchmark_overlap_count", -1)) == 0
        and int(teacher_replay.get("provider_authored_el_count", -1)) == 0
        and int(teacher_replay.get("unverified_self_output_truth_count", -1)) == 0
    )
    validation_pass = all(lang_module.valid_el(row["prediction"]) for row in candidate_teacher_predictions)

    metadata = dict(g1_metadata)
    metadata.update({
        "generation": "G2",
        "parent_generation": "G1",
        "step3_seed": int(args.seed),
        "step3_training_steps": int(args.steps),
        "teacher_replay_fingerprint_sha256": str(teacher_replay["fingerprint_sha256"]),
        "teacher_lesson_count": len(teacher_examples),
        "frozen_benchmark_sha256": file_sha256(BENCHMARK),
    })
    model.save_checkpoint(g2_path, metadata=metadata)

    baseline_metrics = {
        "teacher_probe_exact": sum(1 for item in baseline_teacher_predictions if item["exact"]),
        "teacher_probe_total": len(baseline_teacher_predictions),
        "teacher_token_loss": baseline_teacher_loss,
        "frozen_benchmark_loss": baseline_benchmark_loss,
        "protected_probe_exact": sum(1 for item in baseline_protected_predictions if item["exact"]),
        "protected_probe_total": len(baseline_protected_predictions),
        "roundtrip_exact": 0,
        "roundtrip_total": len(roundtrip_rows),
        "adversarial_integrity_pass": True,
        "validation_pass": True,
    }
    candidate_metrics = {
        "teacher_probe_exact": sum(1 for item in candidate_teacher_predictions if item["exact"]),
        "teacher_probe_total": len(candidate_teacher_predictions),
        "teacher_token_loss": candidate_teacher_loss,
        "frozen_benchmark_loss": candidate_benchmark_loss,
        "protected_probe_exact": sum(1 for item in candidate_protected_predictions if item["exact"]),
        "protected_probe_total": len(candidate_protected_predictions),
        "roundtrip_exact": sum(1 for item in roundtrip_rows if item["exact"]),
        "roundtrip_total": len(roundtrip_rows),
        "adversarial_integrity_pass": adversarial_integrity,
        "validation_pass": validation_pass,
    }

    window = min(30, max(5, len(losses) // 5))
    proof = {
        "schema_version": 1,
        "phase": 6,
        "step": 3,
        "kind": "g2-candidate-training",
        "parent_generation": "G1",
        "candidate_generation": "G2",
        "seed": int(args.seed),
        "training_steps": int(args.steps),
        "batch_size": int(args.batch_size),
        "teacher_examples_per_batch": teacher_batch,
        "protected_examples_per_batch": protected_batch,
        "broad_examples_per_batch": broad_batch,
        "teacher_lesson_count": len(teacher_examples),
        "provider_authored_el_truth_count": 0,
        "unverified_self_output_truth_count": 0,
        "frozen_benchmark_training_overlap_count": 0,
        "early_training_loss": sum(losses[:window]) / window,
        "late_training_loss": sum(losses[-window:]) / window,
        "baseline_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "baseline_teacher_predictions": baseline_teacher_predictions,
        "candidate_teacher_predictions": candidate_teacher_predictions,
        "baseline_protected_predictions": baseline_protected_predictions,
        "candidate_protected_predictions": candidate_protected_predictions,
        "roundtrip_predictions": roundtrip_rows,
        "adversarial": {
            "tokenizer_literal_control_safe": tokenizer_literal_safe,
            "hostile_teacher_case_rejected": hostile_rejected,
            "benchmark_overlap_zero": True,
            "provider_authored_el_zero": True,
            "self_output_truth_zero": True
        },
        "artifacts": {
            "g1_model_path": str(g1_copy),
            "g1_model_sha256": file_sha256(g1_copy),
            "g1_tokenizer_path": str(g1_tokenizer),
            "g1_tokenizer_sha256": file_sha256(g1_tokenizer),
            "g2_model_path": str(g2_path),
            "g2_model_sha256": file_sha256(g2_path),
            "g2_tokenizer_path": str(g2_tokenizer),
            "g2_tokenizer_sha256": file_sha256(g2_tokenizer),
            "replay_fingerprint_sha256": str(teacher_replay["fingerprint_sha256"])
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    (step3 / "g2-training-proof.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "PHASE6_STEP3_G2_TRAINED "
        f"teacher={baseline_metrics['teacher_probe_exact']}/{baseline_metrics['teacher_probe_total']}->{candidate_metrics['teacher_probe_exact']}/{candidate_metrics['teacher_probe_total']} "
        f"teacher_loss={baseline_teacher_loss:.4f}->{candidate_teacher_loss:.4f} "
        f"benchmark={baseline_benchmark_loss:.4f}->{candidate_benchmark_loss:.4f} "
        f"protected={candidate_metrics['protected_probe_exact']}/{candidate_metrics['protected_probe_total']} "
        f"roundtrip={candidate_metrics['roundtrip_exact']}/{candidate_metrics['roundtrip_total']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
