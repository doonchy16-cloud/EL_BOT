#!/usr/bin/env python3
"""Strict evidence gate for Phase 6 Step 2 — Forgey Insta G0/G1."""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import math
import re
import sys

import torch

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "architecture" / "phase6_step2_g0_g1_manifest.json"
BENCHMARK = ROOT / "architecture" / "phase6_step2_frozen_benchmark.json"
STEP1_DATA = ROOT / "data" / "phase6-step1-data-manifest.json"
ARTIFACT = ROOT / "data" / "phase6-step2"
TOKENIZER_ARTIFACT = ARTIFACT / "tokenizer.json"
CHECKPOINT = ARTIFACT / "forgey-insta-g1.pt"
TRAIN_PROOF = ARTIFACT / "training-proof.json"
INFER_FORWARD = ARTIFACT / "infer-abc-to-el.json"
INFER_REVERSE = ARTIFACT / "infer-el-to-abc.json"


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite_positive(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0.0


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest.get("phase") == 6 and manifest.get("step") == 2, "wrong Step-2 manifest")
    require(manifest.get("status") in {"IMPLEMENTATION_IN_PROGRESS", "PASS"}, "invalid Step-2 manifest status")
    require(manifest.get("engine_count") == 44 and manifest.get("new_engine_count") == 0, "Step 2 must not add engine #45")
    require(all(value is False for value in manifest.get("scope_guards", {}).values()), "Step 2 scope guard claims later implementation")

    require(STEP1_DATA.is_file(), "Step-1 materialized data missing")
    step1 = json.loads(STEP1_DATA.read_text(encoding="utf-8-sig"))
    unicode_data = step1.get("unicode", {})
    require(unicode_data.get("emoji_version") == "17.0", "Step-2 is not using released Emoji 17.0 authority")
    official_emoji_count = int(unicode_data.get("rgi_count", 0))
    require(official_emoji_count > 3000, "official emoji inventory unexpectedly small")

    benchmark_payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    require(benchmark_payload.get("frozen") is True, "Step-2 benchmark not frozen")
    require(benchmark_payload.get("training_replay_forbidden") is True, "Step-2 benchmark not training-forbidden")
    benchmark = tuple(benchmark_payload.get("examples", ()))
    require(len(benchmark) >= 24, "frozen benchmark is too small")
    ids = [str(item.get("id", "")) for item in benchmark]
    require(len(ids) == len(set(ids)) and all(ids), "frozen benchmark IDs are missing/duplicated")
    required_categories = set(manifest["frozen_benchmark"]["required_categories"])
    actual_categories = {str(item.get("category")) for item in benchmark}
    require(required_categories.issubset(actual_categories), f"frozen benchmark category coverage missing: {sorted(required_categories - actual_categories)}")
    benchmark_sha = file_sha256(BENCHMARK)

    require(TOKENIZER_ARTIFACT.is_file(), "trained tokenizer artifact missing")
    require(CHECKPOINT.is_file(), "G1 checkpoint missing")
    require(TRAIN_PROOF.is_file(), "G0/G1 training proof missing")
    require(INFER_FORWARD.is_file() and INFER_REVERSE.is_file(), "fresh-process local inference evidence missing")

    tokenizer_module = load("_p6s2_verify_tokenizer", ROOT / "📚" / "✂️")
    token_source_module = load("_p6s2_verify_token_source", ROOT / "📚" / "🔤")
    model_module = load("_p6s2_verify_model", ROOT / "🧠" / "🤖")
    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(TOKENIZER_ARTIFACT)
    source_authority = token_source_module.ELTokenAuthority()
    source_snapshot = source_authority.snapshot()

    require(tokenizer.emoji_version == "17.0", "trained tokenizer emoji version mismatch")
    require(tuple(tokenizer.atomic_el_tokens) == tuple(source_authority.atomic_el_tokens), "trained tokenizer changed Step-1 atomic EL inventory/order")
    require(len(tokenizer.atomic_el_tokens) == source_snapshot.atomic_el_token_count, "atomic EL token count mismatch")
    require(len(source_authority.atomic_emoji_tokens) == official_emoji_count, "official emoji source count mismatch")
    require(tokenizer.special_to_id["<ABC_TO_EL>"] != tokenizer.special_to_id["<EL_TO_ABC>"], "direction token IDs collide")
    require(set(tokenizer.special_tokens).isdisjoint(tokenizer.atomic_el_tokens), "model special token leaked into EL output inventory")

    unseen = "café Ω zxqvplmno — unseen bytes 987"
    require(tokenizer.decode(tokenizer.encode_text(unseen)) == unseen, "byte fallback failed unseen UTF-8 round-trip")
    literal_control = "<ABC_TO_EL> must remain literal user text"
    require(tokenizer.decode(tokenizer.encode_text(literal_control)) == literal_control, "literal model-control string was interpreted as privileged token")
    for atomic in ("👨‍👩‍👧‍👦", "🧑🏽‍💻", "✦", "➡️"):
        require(len(tokenizer.encode_text(atomic)) == 1, f"atomic EL token was split: {atomic}")

    report = tokenizer.training_report
    require(report is not None and report.chosen_merge_count > 0, "BPE measurement report missing")
    require(report.chosen_merge_count == len(tokenizer.merges), "chosen BPE merge count differs from artifact")
    require(report.candidates, "BPE compression candidates missing")
    best_tokens = min(item.encoded_token_count for item in report.candidates)
    eligible = [item for item in report.candidates if item.encoded_token_count <= best_tokens * 1.025]
    require(eligible and report.chosen_merge_count == eligible[0].merge_count, "BPE vocabulary was not selected by the declared measured near-best rule")
    require(tokenizer.vocab_size == len(tokenizer.special_tokens) + len(tokenizer.atomic_el_tokens) + 256 + len(tokenizer.merges), "tokenizer vocabulary arithmetic mismatch")

    proof = json.loads(TRAIN_PROOF.read_text(encoding="utf-8"))
    require(proof.get("phase") == 6 and proof.get("step") == 2 and proof.get("status") == "TRAINED_CANDIDATE", "wrong training proof")
    require(str(proof.get("torch_version", "")).startswith("2.13.0"), "Step-2 tensor runtime is not pinned PyTorch 2.13.0")
    require(proof.get("base_main_sha") == manifest.get("base_main_sha"), "training proof base main SHA mismatch")
    require(proof["benchmark"]["sha256"] == benchmark_sha, "training proof benchmark hash mismatch")
    require(int(proof["benchmark"]["training_source_overlap_count"]) == 0, "frozen benchmark source leaked into training")
    require(int(proof["curriculum"]["provider_generated_truth_count"]) == 0, "provider-generated positive truth leaked into Step 2")
    require(int(proof["curriculum"]["encoded_training_count"]) >= 5000, "encoded trusted curriculum unexpectedly small")
    require(proof["tokenizer"]["sha256"] == file_sha256(TOKENIZER_ARTIFACT), "tokenizer artifact hash mismatch")
    require(proof["tokenizer"]["vocabulary_size"] == tokenizer.vocab_size, "tokenizer proof vocabulary size mismatch")

    rehearsal = proof.get("rehearsal", {})
    require(rehearsal.get("truth_source") == "trusted deterministic Step-2 curriculum only", "G1 rehearsal truth authority mismatch")
    require(int(rehearsal.get("provider_generated_truth_count", -1)) == 0, "provider-generated truth leaked into trusted rehearsal")
    require(int(rehearsal.get("unverified_self_output_truth_count", -1)) == 0, "unverified self-output leaked into trusted rehearsal")
    require(int(rehearsal.get("benchmark_source_overlap_count", -1)) == 0, "frozen benchmark leaked into trusted rehearsal")
    require(int(rehearsal.get("steps", 0)) > 0, "trusted rehearsal did not execute")

    model, checkpoint_metadata = model_module.ForgeyInstaTransformer.load_checkpoint(CHECKPOINT, map_location="cpu")
    config = model.config
    require(config.d_model == 128 and config.nhead == 4, "G0 width/head contract mismatch")
    require(config.encoder_layers == 3 and config.decoder_layers == 3, "G0 layer contract mismatch")
    require(384 <= config.dim_feedforward <= 512, "G0 feed-forward contract mismatch")
    require(config.max_context == 128, "G0 context contract mismatch")
    require(config.vocab_size == tokenizer.vocab_size, "G1 checkpoint/tokenizer vocabulary mismatch")
    parameter_report = model.parameter_report()
    require(parameter_report.within_target, f"real trainable parameter count outside 1-3M target: {parameter_report.trainable_parameters}")
    require(parameter_report.trainable_parameters == int(proof["g0"]["parameters"]["trainable_parameters"]), "parameter proof differs from checkpoint graph")
    require(CHECKPOINT.stat().st_size > 1_000_000, "G1 checkpoint is implausibly small for real neural weights")
    require(proof["g1"]["checkpoint_sha256"] == file_sha256(CHECKPOINT), "G1 checkpoint hash mismatch")
    require(checkpoint_metadata.get("generation") == "G1", "checkpoint generation metadata missing")
    require(checkpoint_metadata.get("benchmark_sha256") == benchmark_sha, "checkpoint benchmark authority mismatch")

    g0_loss = proof["g0"]["frozen_benchmark_loss"]
    early = proof["g1"]["early_training_loss"]
    late = proof["g1"]["late_training_loss"]
    g1_loss = proof["g1"]["frozen_benchmark_loss"]
    require(all(finite_positive(value) for value in (g0_loss, early, late, g1_loss)), "non-finite/non-positive G0/G1 loss evidence")
    require(float(late) <= float(early) * 0.85, f"G1 training loss did not materially improve: {early} -> {late}")
    require(float(g1_loss) <= float(g0_loss) * 0.99, f"G1 frozen benchmark did not improve over G0: {g0_loss} -> {g1_loss}")
    require(int(proof["g1"]["smoke_total"]) == 8, "trusted rehearsal probe cardinality changed")
    require(int(proof["g1"]["smoke_exact_count"]) == int(proof["g1"]["smoke_total"]), "trusted rehearsal probes are not all exact")

    forward = json.loads(INFER_FORWARD.read_text(encoding="utf-8"))
    reverse = json.loads(INFER_REVERSE.read_text(encoding="utf-8"))
    require(forward.get("kind") == reverse.get("kind") == "local-g1-inference", "wrong local inference evidence kind")
    require(forward.get("direction") == "ABC_TO_EL" and reverse.get("direction") == "EL_TO_ABC", "both local inference directions were not exercised")
    require(int(forward.get("provider_calls", -1)) == 0 and int(reverse.get("provider_calls", -1)) == 0, "provider call occurred during local G1 inference")
    require(forward.get("generation") == reverse.get("generation") == "G1", "fresh-process inference did not reload G1")
    require(bool(forward.get("prediction")) and bool(reverse.get("prediction")), "fresh-process local inference produced empty text")
    require(forward.get("exact") is True and reverse.get("exact") is True, "fresh-process rehearsal inference is not exact in both directions")
    require(int(forward.get("trainable_parameters")) == parameter_report.trainable_parameters, "forward inference loaded wrong model graph")
    require(int(reverse.get("trainable_parameters")) == parameter_report.trainable_parameters, "reverse inference loaded wrong model graph")

    # Source-level boundary proof: Step 2 cannot quietly become Steps 3-5.
    guarded_sources = {
        "tokenizer": (ROOT / "📚" / "✂️").read_text(encoding="utf-8"),
        "model": (ROOT / "🧠" / "🤖").read_text(encoding="utf-8"),
        "curriculum": (ROOT / "🧠" / "🌱").read_text(encoding="utf-8"),
        "trainer": (ROOT / "scripts" / "phase6-step2-train-g1.py").read_text(encoding="utf-8"),
        "rehearsal": (ROOT / "scripts" / "phase6-step2-rehearse-g1.py").read_text(encoding="utf-8"),
        "inference": (ROOT / "scripts" / "phase6-step2-infer.py").read_text(encoding="utf-8"),
    }
    for name, source in guarded_sources.items():
        lowered = source.lower()
        for forbidden in ("qwen2.5vl", "ollamaconnector", "forgeyconnector", "chat_internal", "generate_internal", "urllib.request"):
            require(forbidden not in lowered, f"later-step/provider coupling leaked into Step-2 {name}: {forbidden}")
    require(not (ROOT / "🧑‍🏫" / "🤖").exists(), "Step-3 teacher/training coordinator leaked into Step 2")
    require(not (ROOT / "scripts" / "publish-phase6-release.ps1").exists(), "Step-5 publisher leaked into Step 2")
    runtime_source = (ROOT / "↔️" / "↔️").read_text(encoding="utf-8")
    orchestration_source = (ROOT / "✦" / "✦").read_text(encoding="utf-8")
    require("forgeyinsta" not in runtime_source.lower(), "Step-4 primary routing leaked into translation runtime")
    require("forgeyinsta" not in orchestration_source.lower(), "Step-4 primary routing leaked into orchestration")

    if manifest.get("status") == "PASS":
        evidence = manifest.get("evidence_basis", {})
        require(evidence.get("candidate_workflow_conclusion") == "success", "PASS manifest lacks successful candidate workflow evidence")
        require(re.fullmatch(r"[0-9a-f]{40}", str(evidence.get("candidate_head_sha", ""))), "PASS manifest candidate SHA missing")
        require(manifest.get("final_exact_head_ci_required") is True, "PASS manifest must require exact final-head CI")

    print(
        "PHASE6_STEP2_OK "
        f"params={parameter_report.trainable_parameters} vocab={tokenizer.vocab_size} merges={len(tokenizer.merges)} "
        f"train={float(early):.4f}->{float(late):.4f} benchmark={float(g0_loss):.4f}->{float(g1_loss):.4f} "
        f"smoke={proof['g1']['smoke_exact_count']}/{proof['g1']['smoke_total']} "
        "local=ABC_TO_EL+EL_TO_ABC provider=0 step3=ABSENT step4=ABSENT step5=ABSENT",
        flush=True,
    )


if __name__ == "__main__":
    main()
