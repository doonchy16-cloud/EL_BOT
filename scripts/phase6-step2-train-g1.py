#!/usr/bin/env python3
"""Train the first Forgey Insta:EL-Bot G1 candidate from trusted bootstrap truth."""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import math
import os
import random
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


def stable_order(values: list[str]) -> list[str]:
    unique = tuple(dict.fromkeys(str(value) for value in values if str(value)))
    return sorted(unique, key=lambda value: (sha256(value.encode("utf-8")).digest(), value))


def fingerprint_examples(examples) -> str:
    digest = sha256()
    for example in examples:
        digest.update(example.direction.encode("utf-8")); digest.update(b"\0")
        digest.update(example.source.encode("utf-8")); digest.update(b"\0")
        digest.update(example.target.encode("utf-8")); digest.update(b"\0")
        digest.update(example.provenance.encode("utf-8")); digest.update(b"\n")
    return digest.hexdigest()


def encode_example(tokenizer, direction: str, source: str, target: str, max_context: int):
    source_ids = tokenizer.encode_source(direction, source)
    decoder_ids, labels = tokenizer.encode_target(target)
    if len(source_ids) > max_context or len(decoder_ids) > max_context or len(labels) > max_context:
        return None
    return (source_ids, decoder_ids, labels)


def collate(encoded_rows, pad_id: int, device: torch.device):
    batch = len(encoded_rows)
    src_len = max(len(row[0]) for row in encoded_rows)
    tgt_len = max(len(row[1]) for row in encoded_rows)
    source = torch.full((batch, src_len), pad_id, dtype=torch.long, device=device)
    decoder = torch.full((batch, tgt_len), pad_id, dtype=torch.long, device=device)
    labels = torch.full((batch, tgt_len), -100, dtype=torch.long, device=device)
    for index, (src, dec, lab) in enumerate(encoded_rows):
        source[index, : len(src)] = torch.tensor(src, dtype=torch.long, device=device)
        decoder[index, : len(dec)] = torch.tensor(dec, dtype=torch.long, device=device)
        labels[index, : len(lab)] = torch.tensor(lab, dtype=torch.long, device=device)
    return source, decoder, labels


def token_loss(model, rows, pad_id: int, device: torch.device, batch_size: int = 24) -> float:
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            source, decoder, labels = collate(rows[start:start + batch_size], pad_id, device)
            logits = model(source, decoder)
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                labels.reshape(-1),
                ignore_index=-100,
                reduction="sum",
            )
            count = int(labels.ne(-100).sum().item())
            total_loss += float(loss.item())
            total_tokens += count
    if not total_tokens:
        raise RuntimeError("cannot evaluate an empty token set")
    return total_loss / total_tokens


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "data" / "phase6-step2"))
    parser.add_argument("--steps", type=int, default=480)
    parser.add_argument("--batch-size", type=int, default=28)
    parser.add_argument("--seed", type=int, default=620260818)
    args = parser.parse_args()

    started = time.perf_counter()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    tokenizer_path = output / "tokenizer.json"
    checkpoint_path = output / "forgey-insta-g1.pt"
    proof_path = output / "training-proof.json"

    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cpu")

    tokenizer_module = load("_p6s2_tokenizer", ROOT / "📚" / "✂️")
    token_source_module = load("_p6s2_token_source", ROOT / "📚" / "🔤")
    curriculum_module = load("_p6s2_curriculum", ROOT / "🧠" / "🌱")
    model_module = load("_p6s2_model", ROOT / "🧠" / "🤖")

    benchmark_payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    benchmark_items = tuple(benchmark_payload["examples"])
    forbidden_keys = {(str(item["direction"]), str(item["source"])) for item in benchmark_items}
    forbidden_english = {
        str(item["source"] if item["direction"] == "ABC_TO_EL" else item["target"]).casefold()
        for item in benchmark_items
    }

    curriculum, curriculum_report = curriculum_module.build_bootstrap_curriculum(BENCHMARK)
    if any(example.key in forbidden_keys for example in curriculum):
        raise RuntimeError("frozen benchmark source leaked into model curriculum")

    # Tokenizer corpus: deterministic lexical sample + trusted curriculum English.
    authority = token_source_module.ELTokenAuthority()
    lemmas = [lemma for lemma in authority.iter_english_lemmas() if lemma.casefold() not in forbidden_english]
    ordered_lemmas = stable_order(lemmas)
    lexical_source = ordered_lemmas[:16000]
    lexical_evaluation = ordered_lemmas[16000:20000]
    if len(lexical_source) < 12000 or len(lexical_evaluation) < 3000:
        raise RuntimeError("Step-1 lexical authority is too small for Step-2 BPE measurement")

    curriculum_english = [
        value
        for value in curriculum_module.english_training_texts(curriculum)
        if value.casefold() not in forbidden_english
    ]
    tokenizer_source = tuple(lexical_source + curriculum_english)
    tokenizer_evaluation = tuple(lexical_evaluation)
    tokenizer = tokenizer_module.train_byte_bpe(
        tokenizer_source,
        tokenizer_evaluation,
        candidate_merge_counts=(128, 256, 320),
        within_best_token_fraction=1.025,
    )
    tokenizer.save(tokenizer_path)

    config = model_module.ForgeyInstaConfig(
        vocab_size=tokenizer.vocab_size,
        d_model=128,
        nhead=4,
        encoder_layers=3,
        decoder_layers=3,
        dim_feedforward=384,
        max_context=128,
        dropout=0.10,
        pad_id=tokenizer.pad_id,
    )
    model = model_module.ForgeyInstaTransformer(config).to(device)
    parameter_report = model.parameter_report()
    if not parameter_report.within_target:
        raise RuntimeError(f"G0 parameter count outside owner target: {parameter_report.trainable_parameters}")

    # Encode the model curriculum only after tokenizer selection. The benchmark is
    # separately encoded and is never appended to the training/replay rows.
    training_rows = []
    training_examples = []
    training_weights = []
    skipped_context = 0
    smoke_keys = {
        ("ABC_TO_EL", "bicycle"),
        ("ABC_TO_EL", "rocket"),
        ("ABC_TO_EL", "camera"),
        ("ABC_TO_EL", "key"),
        ("EL_TO_ABC", "🚲"),
        ("EL_TO_ABC", "🚀"),
        ("EL_TO_ABC", "📷"),
        ("EL_TO_ABC", "🔑"),
    }
    for example in curriculum:
        encoded = encode_example(tokenizer, example.direction, example.source, example.target, config.max_context)
        if encoded is None:
            skipped_context += 1
            continue
        training_rows.append(encoded)
        training_examples.append(example)
        multiplier = 32 if example.key in smoke_keys else 1
        training_weights.append(max(1, int(example.weight)) * multiplier)
    if len(training_rows) < 5000:
        raise RuntimeError(f"trusted G1 curriculum unexpectedly small after encoding: {len(training_rows)}")

    benchmark_rows = []
    for item in benchmark_items:
        encoded = encode_example(tokenizer, str(item["direction"]), str(item["source"]), str(item["target"]), config.max_context)
        if encoded is None:
            raise RuntimeError(f"frozen benchmark exceeds G0 context: {item['id']}")
        benchmark_rows.append(encoded)

    g0_benchmark_loss = token_loss(model, benchmark_rows, tokenizer.pad_id, device)
    if not math.isfinite(g0_benchmark_loss):
        raise RuntimeError("G0 benchmark loss is not finite")

    optimizer = torch.optim.AdamW(model.parameters(), lr=8e-4, betas=(0.9, 0.98), weight_decay=0.01)
    rng = random.Random(args.seed)
    step_losses: list[float] = []
    model.train()
    for step in range(int(args.steps)):
        indices = rng.choices(range(len(training_rows)), weights=training_weights, k=int(args.batch_size))
        rows = [training_rows[index] for index in indices]
        source, decoder, labels = collate(rows, tokenizer.pad_id, device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(source, decoder)
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1), ignore_index=-100)
        if not torch.isfinite(loss):
            raise RuntimeError(f"non-finite G1 loss at step {step + 1}")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        step_losses.append(float(loss.item()))
        if (step + 1) % 80 == 0 or step == 0:
            print(f"G1_TRAIN step={step + 1}/{args.steps} loss={step_losses[-1]:.6f}", flush=True)

    window = min(30, max(5, len(step_losses) // 5))
    early_loss = sum(step_losses[:window]) / window
    late_loss = sum(step_losses[-window:]) / window
    g1_benchmark_loss = token_loss(model, benchmark_rows, tokenizer.pad_id, device)

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

    tokenizer_sha = file_sha256(tokenizer_path)
    benchmark_sha = file_sha256(BENCHMARK)
    checkpoint_metadata = {
        "generation": "G1",
        "seed": int(args.seed),
        "training_steps": int(args.steps),
        "tokenizer_sha256": tokenizer_sha,
        "benchmark_sha256": benchmark_sha,
        "curriculum_sha256": fingerprint_examples(training_examples),
        "base_main_sha": "902a79fec235f77c1bf3b4c7edf82b9a0127b900",
    }
    model.save_checkpoint(checkpoint_path, metadata=checkpoint_metadata)
    checkpoint_sha = file_sha256(checkpoint_path)

    report = tokenizer.training_report
    if report is None:
        raise RuntimeError("trained tokenizer did not retain measurement report")
    proof = {
        "schema_version": 1,
        "phase": 6,
        "step": 2,
        "status": "TRAINED_CANDIDATE",
        "torch_version": str(torch.__version__),
        "device": str(device),
        "seed": int(args.seed),
        "base_main_sha": "902a79fec235f77c1bf3b4c7edf82b9a0127b900",
        "benchmark": {
            "path": str(BENCHMARK.relative_to(ROOT)).replace("\\", "/"),
            "sha256": benchmark_sha,
            "example_count": len(benchmark_items),
            "categories": sorted({str(item["category"]) for item in benchmark_items}),
            "training_source_overlap_count": sum(1 for example in training_examples if example.key in forbidden_keys),
        },
        "tokenizer": {
            "path": str(tokenizer_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": tokenizer_sha,
            "emoji_version": tokenizer.emoji_version,
            "vocabulary_size": tokenizer.vocab_size,
            "atomic_el_token_count": len(tokenizer.atomic_el_tokens),
            "chosen_merge_count": report.chosen_merge_count,
            "trained_merge_count": report.trained_merge_count,
            "source_item_count": report.source_item_count,
            "evaluation_item_count": report.evaluation_item_count,
            "compression_candidates": [asdict(item) for item in report.candidates],
        },
        "curriculum": {
            **asdict(curriculum_report),
            "encoded_training_count": len(training_rows),
            "context_skipped_count": skipped_context,
            "fingerprint_sha256": checkpoint_metadata["curriculum_sha256"],
            "provider_generated_truth_count": 0,
        },
        "g0": {
            "config": asdict(config),
            "parameters": asdict(parameter_report),
            "frozen_benchmark_loss": g0_benchmark_loss,
        },
        "g1": {
            "training_steps": int(args.steps),
            "batch_size": int(args.batch_size),
            "early_training_loss": early_loss,
            "late_training_loss": late_loss,
            "training_loss_ratio": late_loss / early_loss if early_loss else None,
            "frozen_benchmark_loss": g1_benchmark_loss,
            "benchmark_loss_ratio_to_g0": g1_benchmark_loss / g0_benchmark_loss if g0_benchmark_loss else None,
            "checkpoint_path": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"),
            "checkpoint_sha256": checkpoint_sha,
            "smoke_exact_count": sum(1 for item in smoke_predictions if item["exact"]),
            "smoke_total": len(smoke_predictions),
            "smoke_predictions": smoke_predictions,
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "PHASE6_STEP2_TRAINED "
        f"params={parameter_report.trainable_parameters} "
        f"vocab={tokenizer.vocab_size} merges={report.chosen_merge_count} "
        f"train={early_loss:.4f}->{late_loss:.4f} "
        f"benchmark={g0_benchmark_loss:.4f}->{g1_benchmark_loss:.4f} "
        f"smoke={proof['g1']['smoke_exact_count']}/{proof['g1']['smoke_total']} "
        f"seconds={proof['elapsed_seconds']:.1f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
