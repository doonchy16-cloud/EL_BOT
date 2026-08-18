#!/usr/bin/env python3
"""Strict Phase-6 Step-3 teacher, generation, promotion and rollback evidence gate."""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import math
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "architecture" / "phase6_step3_teacher_learning_manifest.json"
CASES = ROOT / "architecture" / "phase6_step3_teacher_cases.json"
BENCHMARK = ROOT / "architecture" / "phase6_step2_frozen_benchmark.json"
STEP3 = ROOT / "data" / "phase6-step3"
TEACHER = STEP3 / "teacher-evidence.json"
REPLAY = STEP3 / "teacher-replay.json"
LEARNING = STEP3 / "learning-v1.json"
TRAIN = STEP3 / "g2-training-proof.json"
REGISTRY = STEP3 / "generation-registry.json"
PROMOTION = STEP3 / "promotion-proof.json"
INFER_FORWARD = STEP3 / "infer-selected-forward.json"
INFER_REVERSE = STEP3 / "infer-selected-reverse.json"


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


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def positive_finite(value) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0.0


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest.get("phase") == 6 and manifest.get("step") == 3, "wrong Step-3 manifest")
    require(manifest.get("status") in {"IMPLEMENTATION_IN_PROGRESS", "PASS"}, "invalid Step-3 manifest status")
    require(manifest.get("base_main_sha") == "cc49045e8933d43aae285add3ade480fe64e9a89", "Step-3 base main SHA changed")
    require(manifest.get("engine_count") == 44 and manifest.get("new_engine_count") == 0, "Step 3 must not add engine #45")
    require(all(value is False for value in manifest.get("scope_guards", {}).values()), "Step-3 scope guard claims Step 4/5 implementation")
    require(manifest.get("teacher", {}).get("semantic_only") is True, "teacher is not semantic-only")
    require(manifest.get("teacher", {}).get("provider_may_author_el") is False, "teacher may author EL")
    require(manifest.get("teacher", {}).get("raw_provider_prose_canonical") is False, "raw provider prose may become canonical")
    require(manifest.get("learning", {}).get("candidate_weights_mutate_production_in_place") is False, "production weights may mutate in place")
    require(manifest.get("learning", {}).get("immutable_generation_registry") is True, "immutable generation registry not required")
    require(manifest.get("learning", {}).get("rollback_required") is True, "rollback not required")

    cases_payload = json.loads(CASES.read_text(encoding="utf-8"))
    require(cases_payload.get("frozen") is True, "Step-3 teacher cases are not frozen")
    require(cases_payload.get("provider_may_author_el") is False, "teacher case authority permits provider EL")
    cases = tuple(cases_payload.get("cases", ()))
    require(len(cases) == 5, "Step-3 teacher-case cardinality changed")
    case_ids = [str(item.get("id", "")) for item in cases]
    require(len(case_ids) == len(set(case_ids)) and all(case_ids), "teacher case IDs missing/duplicated")

    benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    require(benchmark.get("frozen") is True and benchmark.get("training_replay_forbidden") is True, "Step-2 frozen benchmark authority changed")
    benchmark_keys = {(str(item["direction"]), str(item["source"])) for item in benchmark.get("examples", ())}
    positive_case_keys = {(str(item["direction"]), str(item["source"])) for item in cases if item.get("training_eligible") is True}
    require(not positive_case_keys.intersection(benchmark_keys), "teacher positive case duplicates frozen benchmark source")

    for path in (TEACHER, REPLAY, LEARNING, TRAIN, REGISTRY, PROMOTION, INFER_FORWARD, INFER_REVERSE):
        require(path.is_file(), f"Step-3 evidence missing: {path.name}")

    teacher = json.loads(TEACHER.read_text(encoding="utf-8"))
    require(teacher.get("kind") == "teacher-lesson-evidence", "wrong teacher evidence kind")
    require(int(teacher.get("provider_calls", -1)) == len(cases), "not every frozen teacher case made a real provider call")
    require(int(teacher.get("accepted_count", 0)) >= 3, "too few teacher lessons deterministically admitted")
    require(int(teacher.get("rejected_count", 0)) >= 1, "negative teacher evidence missing")
    require(int(teacher.get("provider_authored_el_count", -1)) == 0, "provider-authored EL crossed teacher boundary")
    require(int(teacher.get("unverified_self_output_truth_count", -1)) == 0, "self-output became positive training truth")
    require(int(teacher.get("benchmark_training_overlap_count", -1)) == 0, "frozen benchmark leaked into teacher training")
    require(teacher.get("teacher_cases_sha256") == file_sha256(CASES), "teacher-case evidence hash mismatch")
    require(teacher.get("frozen_benchmark_sha256") == file_sha256(BENCHMARK), "teacher benchmark evidence hash mismatch")

    lessons = tuple(teacher.get("lessons", ()))
    require(len(lessons) == int(teacher["accepted_count"]), "teacher admitted count differs from lesson evidence")
    require(all(item.get("provider") == "ollama" for item in lessons), "accepted teacher lesson came from wrong provider")
    require(all(item.get("model") == "qwen2.5vl:7b" for item in lessons), "accepted teacher lesson came from wrong model")
    require(all(item.get("semantic_definition") and isinstance(item.get("semantic_definition"), str) for item in lessons), "accepted semantic definition missing")
    require(all(not any(ord(char) > 0xFFFF for char in str(item["semantic_definition"])) for item in lessons), "unexpected supplementary symbol leaked into teacher definition")

    hostile = next((item for item in teacher.get("rejections", ()) if item.get("case_id") == "teacher-hostile-instruction"), None)
    require(hostile is not None, "hostile teacher case did not become negative evidence")
    require(hostile.get("provider_called") is True, "hostile teacher case was not actually sent through provider boundary")
    require("case-not-training-eligible" in hostile.get("reason_codes", ()), "hostile case rejection reason missing")
    require(bool(hostile.get("rejected_definition_sha256")) or "provider-error" in hostile.get("reason_codes", ()), "hostile result lacks negative evidence fingerprint/error")

    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    require(replay.get("kind") == "validated-teacher-replay", "wrong teacher replay kind")
    require(int(replay.get("frozen_benchmark_overlap_count", -1)) == 0, "replay benchmark overlap is nonzero")
    require(int(replay.get("provider_authored_el_count", -1)) == 0, "replay contains provider-authored EL")
    require(int(replay.get("unverified_self_output_truth_count", -1)) == 0, "replay contains unverified self-output")
    replay_examples = tuple(replay.get("examples", ()))
    require(len(replay_examples) == len(lessons), "replay cardinality differs from admitted lessons")
    require(all("semantic_definition" not in item for item in replay_examples), "provider semantic prose leaked into neural replay")
    require(all((str(item["direction"]), str(item["source"])) not in benchmark_keys for item in replay_examples), "frozen benchmark source present in replay")
    require(re.fullmatch(r"[0-9a-f]{64}", str(replay.get("fingerprint_sha256", ""))) is not None, "replay fingerprint missing")
    require(teacher.get("replay_fingerprint_sha256") == replay.get("fingerprint_sha256"), "teacher/replay fingerprints disagree")

    # Independent target authority is intentionally broader than the legacy runtime:
    # Step 2 established both the executable deterministic translator and a frozen,
    # trusted deterministic bootstrap curriculum. The verifier reconstructs those
    # authorities directly rather than trusting the Step-3 coordinator's decision.
    abc_module = load("_p6s3_verify_abc", ROOT / "🔤➡️😀" / "🔤➡️😀")
    curriculum_module = load("_p6s3_verify_curriculum", ROOT / "🧠" / "🌱")
    abc = abc_module.ABCToEmojiEngine()
    curriculum, _ = curriculum_module.build_bootstrap_curriculum(BENCHMARK)
    trusted_step2_targets = frozenset(
        (str(example.direction), " ".join(str(example.source).split()).casefold(), str(example.target))
        for example in curriculum
    )
    for item in replay_examples:
        concept = " ".join(str(item["canonical_concept"]).split())
        target = str(item["target"])
        result = abc.translate(concept, cross_verify=False, emit=False)
        runtime_valid = (
            result.winner == target
            and str(result.metrics.get("quality_status", "fail")).lower() != "fail"
        )
        curriculum_valid = ("ABC_TO_EL", concept.casefold(), target) in trusted_step2_targets
        require(runtime_valid or curriculum_valid, f"replay target lacks independent Step-2 authority: {item['lesson_id']}")

    learning_raw = LEARNING.read_text(encoding="utf-8")
    learning = json.loads(learning_raw)
    require(learning.get("schema") == 1, "wrong learning-store schema")
    require(len(learning.get("claims", {})) >= len(lessons), "accepted teacher provenance not persisted")
    require(len(learning.get("episodes", [])) >= 1, "rejected teacher negative episode not persisted")
    for lesson in lessons:
        require(str(lesson["semantic_definition"]) not in learning_raw, "raw/normalized provider semantic prose leaked into canonical learning store")
        require(str(lesson["learning_claim_id"]) in learning.get("claims", {}), "teacher lesson claim ID absent from learning store")

    training = json.loads(TRAIN.read_text(encoding="utf-8"))
    require(training.get("kind") == "g2-candidate-training", "wrong G2 training proof kind")
    require(training.get("parent_generation") == "G1" and training.get("candidate_generation") == "G2", "wrong generation lineage")
    require(int(training.get("teacher_lesson_count", 0)) == len(replay_examples), "G2 teacher count differs from admitted replay")
    require(int(training.get("teacher_reverse_replay_count", -1)) == len(replay_examples), "G2 reverse teacher replay count differs from admitted lessons")
    require(int(training.get("teacher_training_relation_count", -1)) == len(replay_examples) * 2, "G2 bidirectional teacher relation count mismatch")
    require(int(training.get("teacher_reverse_benchmark_overlap_count", -1)) == 0, "reverse teacher replay overlaps frozen benchmark")
    require(int(training.get("provider_authored_el_truth_count", -1)) == 0, "provider-authored EL entered G2")
    require(int(training.get("unverified_self_output_truth_count", -1)) == 0, "self-output entered G2")
    require(int(training.get("frozen_benchmark_training_overlap_count", -1)) == 0, "frozen benchmark entered G2")
    require(positive_finite(training.get("early_training_loss")) and positive_finite(training.get("late_training_loss")), "invalid G2 training loss")
    require(float(training["late_training_loss"]) < float(training["early_training_loss"]), "G2 training objective did not improve")

    baseline = dict(training.get("baseline_metrics", {}))
    candidate = dict(training.get("candidate_metrics", {}))
    require(positive_finite(baseline.get("teacher_token_loss")) and positive_finite(candidate.get("teacher_token_loss")), "teacher loss evidence invalid")
    require(
        int(candidate.get("teacher_probe_exact", 0)) > int(baseline.get("teacher_probe_exact", 0))
        or float(candidate["teacher_token_loss"]) <= float(baseline["teacher_token_loss"]) * 0.98,
        "G2 has no measurable teacher improvement over G1",
    )
    require(float(candidate.get("frozen_benchmark_loss", math.inf)) <= float(baseline.get("frozen_benchmark_loss", -math.inf)), "G2 regressed on frozen benchmark")
    require(int(candidate.get("protected_probe_total", -1)) == 8, "protected Step-2 probe cardinality changed")
    require(int(candidate.get("protected_probe_exact", -1)) >= int(baseline.get("protected_probe_exact", -1)), "G2 regressed on protected Step-2 probes")
    require(int(candidate.get("roundtrip_total", 0)) > 0 and int(candidate.get("roundtrip_exact", -1)) == int(candidate.get("roundtrip_total", 0)), "G2 teacher round-trips are not all exact")
    require(candidate.get("adversarial_integrity_pass") is True, "G2 adversarial integrity failed")
    require(candidate.get("validation_pass") is True, "G2 deterministic validation failed")
    adversarial = dict(training.get("adversarial", {}))
    require(all(adversarial.get(key) is True for key in (
        "tokenizer_literal_control_safe", "hostile_teacher_case_rejected", "benchmark_overlap_zero",
        "teacher_reverse_benchmark_overlap_zero", "provider_authored_el_zero", "self_output_truth_zero"
    )), "G2 adversarial evidence incomplete")

    artifacts = dict(training.get("artifacts", {}))
    for prefix in ("g1_model", "g1_tokenizer", "g2_model", "g2_tokenizer"):
        path = Path(str(artifacts.get(prefix + "_path", "")))
        require(path.is_file(), f"{prefix} artifact missing")
        require(file_sha256(path) == artifacts.get(prefix + "_sha256"), f"{prefix} artifact hash mismatch")
    require(artifacts.get("replay_fingerprint_sha256") == replay.get("fingerprint_sha256"), "G2 replay fingerprint mismatch")

    registry_payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    require(registry_payload.get("schema_version") == 1, "wrong generation registry schema")
    require(registry_payload.get("production_generation") == "G2", "final selected generation is not G2")
    generations = registry_payload.get("generations", {})
    require(set(generations) == {"G1", "G2"}, "generation registry contains unexpected/missing generations")
    require(generations["G1"].get("status") == "verified", "G1 is not retained as verified rollback generation")
    require(generations["G2"].get("status") == "production", "G2 is not selected production generation")
    require(generations["G2"].get("parent_generation") == "G1", "G2 parent linkage wrong")

    registry_module = load("_p6s3_verify_registry", ROOT / "🗃️" / "🤖")
    registry = registry_module.ForgeyGenerationRegistry(REGISTRY)
    require(registry.verify_generation_hashes("G1") and registry.verify_generation_hashes("G2"), "registered immutable artifact hashes do not verify")

    promotion = json.loads(PROMOTION.read_text(encoding="utf-8"))
    require(promotion.get("actual_candidate_generation") == "G2" and promotion.get("actual_decision") == "PROMOTE", "real measured G2 was not promoted")
    require(promotion.get("production_before") == "G1" and promotion.get("production_after_promotion") == "G2", "promotion pointer evidence wrong")
    require(promotion.get("rollback_target") == "G1", "rollback target is not G1")
    require(promotion.get("rollback_restored_sha256") == promotion.get("g1_model_sha256"), "rollback did not restore exact G1 model hash")
    require(promotion.get("production_after_rollback_proof_restore") == "G2" and promotion.get("final_selected_generation") == "G2", "G2 was not restored after rollback proof")
    fixture = dict(promotion.get("rejection_policy_fixture", {}))
    require(fixture.get("fixture_only") is True, "rejection policy fixture is not truthfully labeled")
    require(fixture.get("accepted") is False, "deliberately degraded policy fixture was not rejected")
    require("deterministic-validation-failed" in fixture.get("reasons", ()), "policy rejection reason missing")
    require(fixture.get("production_pointer_after_fixture") == "G1", "rejection fixture mutated production pointer")
    require(promotion.get("immutable_hashes_verified") is True, "immutable generation hashes were not verified")
    history = tuple(promotion.get("history_kinds", ()))
    require(history.count("register") == 2 and "initialize-production" in history and "promote" in history and history.count("rollback") >= 2, "generation history lacks promotion/rollback lifecycle")

    forward = json.loads(INFER_FORWARD.read_text(encoding="utf-8"))
    reverse = json.loads(INFER_REVERSE.read_text(encoding="utf-8"))
    require(forward.get("kind") == reverse.get("kind") == "selected-generation-local-inference", "wrong selected-generation inference kind")
    require(forward.get("selected_generation") == reverse.get("selected_generation") == "G2", "fresh process did not load selected G2")
    require(forward.get("direction") == "ABC_TO_EL" and reverse.get("direction") == "EL_TO_ABC", "selected-generation inference directions missing")
    require(forward.get("exact") is True and reverse.get("exact") is True, "selected G2 fresh-process inference not exact")
    require(int(forward.get("provider_calls", -1)) == 0 and int(reverse.get("provider_calls", -1)) == 0, "provider called during selected local inference")
    require(forward.get("model_sha256") == reverse.get("model_sha256") == generations["G2"]["model_sha256"], "fresh-process G2 model hash differs from registry")

    # Source-scope boundary: Step 3 may use provider evidence, but production runtime
    # remains untouched until separately authorized Step 4 and no release publisher exists.
    runtime_source = (ROOT / "↔️" / "↔️").read_text(encoding="utf-8").lower()
    orchestration_source = (ROOT / "✦" / "✦").read_text(encoding="utf-8").lower()
    for name, source in (("runtime", runtime_source), ("orchestration", orchestration_source)):
        require("forgeygenerationregistry" not in source and "phase6-step3" not in source, f"Step-4 Forgey-first routing leaked into {name}")
    require(not (ROOT / "scripts" / "phase6-step4-runtime.py").exists(), "Step-4 runtime script leaked into Step 3")
    require(not (ROOT / "scripts" / "publish-phase6-release.ps1").exists(), "Step-5 release publisher leaked into Step 3")

    if manifest.get("status") == "PASS":
        evidence_basis = manifest.get("evidence_basis", {})
        require(evidence_basis.get("candidate_workflow_conclusion") == "success", "PASS manifest lacks successful candidate workflow")
        require(re.fullmatch(r"[0-9a-f]{40}", str(evidence_basis.get("candidate_head_sha", ""))) is not None, "PASS manifest candidate SHA missing")
        require(manifest.get("final_exact_head_ci_required") is True, "PASS manifest does not require final exact-head CI")

    print(
        "PHASE6_STEP3_OK "
        f"teacher_calls={teacher['provider_calls']} admitted={teacher['accepted_count']} rejected={teacher['rejected_count']} "
        f"teacher={baseline['teacher_probe_exact']}/{baseline['teacher_probe_total']}->{candidate['teacher_probe_exact']}/{candidate['teacher_probe_total']} "
        f"teacher_loss={float(baseline['teacher_token_loss']):.4f}->{float(candidate['teacher_token_loss']):.4f} "
        f"benchmark={float(baseline['frozen_benchmark_loss']):.4f}->{float(candidate['frozen_benchmark_loss']):.4f} "
        f"protected={candidate['protected_probe_exact']}/{candidate['protected_probe_total']} "
        f"roundtrip={candidate['roundtrip_exact']}/{candidate['roundtrip_total']} reverse_replay={training['teacher_reverse_replay_count']}/{training['teacher_lesson_count']} "
        "selected=G2 rollback=PASS provider_el=0 self_truth=0 step4=ABSENT step5=ABSENT",
        flush=True,
    )


if __name__ == "__main__":
    main()
