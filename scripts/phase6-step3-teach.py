#!/usr/bin/env python3
"""Run real Step-3 Qwen teacher lessons and persist only structured evidence."""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "architecture" / "phase6_step3_teacher_cases.json"
BENCHMARK = ROOT / "architecture" / "phase6_step2_frozen_benchmark.json"


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def canonical_sha(payload) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "data" / "phase6-step3"))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    coordinator_module = load("_p6s3_teacher_runner", ROOT / "🧑‍🏫" / "🤖")
    learning_path = output / "learning-v1.json"
    coordinator = coordinator_module.TeacherLearningCoordinator(learning_path=learning_path)
    evidence = coordinator.run_cases(CASES, BENCHMARK)

    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    expected_calls = len(cases)

    # A correct unresolved provider answer has an empty structured definition. Keep
    # evidence truthful by hashing that empty value rather than inventing prose.
    empty_definition_sha = sha256(b"").hexdigest()
    for rejection in evidence["rejections"]:
        if not rejection.get("rejected_definition_sha256"):
            rejection["rejected_definition_sha256"] = empty_definition_sha

    replay_examples = [
        {
            "lesson_id": lesson["lesson_id"],
            "direction": lesson["direction"],
            "source": lesson["source"],
            "target": lesson["target"],
            "canonical_concept": lesson["canonical_concept"],
            "provenance": "validated-qwen-semantic-lesson+independent-deterministic-target",
            "provider": lesson["provider"],
            "model": lesson["model"],
            "learning_claim_id": lesson["learning_claim_id"],
        }
        for lesson in evidence["lessons"]
    ]
    replay = {
        "schema_version": 1,
        "phase": 6,
        "step": 3,
        "kind": "validated-teacher-replay",
        "frozen_benchmark_overlap_count": 0,
        "provider_authored_el_count": 0,
        "unverified_self_output_truth_count": 0,
        "examples": replay_examples,
    }
    replay["fingerprint_sha256"] = canonical_sha(replay_examples)
    evidence["replay_fingerprint_sha256"] = replay["fingerprint_sha256"]
    evidence["learning_store_sha256"] = sha256(learning_path.read_bytes()).hexdigest() if learning_path.is_file() else ""
    evidence["teacher_cases_sha256"] = sha256(CASES.read_bytes()).hexdigest()
    evidence["frozen_benchmark_sha256"] = sha256(BENCHMARK.read_bytes()).hexdigest()

    # Persist diagnostic evidence before quality thresholds so a HOLD remains
    # inspectable. This is internal evidence; it is not a release artifact.
    (output / "teacher-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "teacher-replay.json").write_text(json.dumps(replay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for lesson in evidence["lessons"]:
        print(
            "TEACHER_ADMIT "
            f"case={lesson['case_id']} concept={lesson['canonical_concept']} target={lesson['target']} "
            f"definition={lesson['semantic_definition']!r} confidence={lesson['semantic_confidence']:.3f}",
            flush=True,
        )
    for rejection in evidence["rejections"]:
        print(
            "TEACHER_REJECT "
            f"case={rejection['case_id']} provider_called={rejection['provider_called']} "
            f"reasons={','.join(rejection['reason_codes'])} definition_sha256={rejection['rejected_definition_sha256'][:12]}",
            flush=True,
        )

    if int(evidence["provider_calls"]) != expected_calls:
        raise RuntimeError(f"real teacher call count mismatch: {evidence['provider_calls']} != {expected_calls}")
    if int(evidence["accepted_count"]) < 3:
        raise RuntimeError(f"too few deterministically admitted semantic lessons: {evidence['accepted_count']}")
    if int(evidence["rejected_count"]) < 1:
        raise RuntimeError("hostile/rejected teacher evidence missing")
    if int(evidence["provider_authored_el_count"]) != 0:
        raise RuntimeError("provider-authored EL crossed teacher boundary")
    if int(evidence["unverified_self_output_truth_count"]) != 0:
        raise RuntimeError("self-output became training truth")
    if int(evidence["benchmark_training_overlap_count"]) != 0:
        raise RuntimeError("frozen benchmark leaked into teacher replay")

    hostile = next((item for item in evidence["rejections"] if item["case_id"] == "teacher-hostile-instruction"), None)
    if hostile is None or "case-not-training-eligible" not in hostile["reason_codes"]:
        raise RuntimeError("hostile teacher case was not rejected as negative evidence")

    models = sorted({lesson["model"] for lesson in evidence["lessons"]})
    providers = sorted({lesson["provider"] for lesson in evidence["lessons"]})
    print(
        "PHASE6_STEP3_TEACHER_OK "
        f"calls={evidence['provider_calls']} admitted={evidence['accepted_count']} rejected={evidence['rejected_count']} "
        f"providers={','.join(providers)} models={','.join(models)} provider_el=0 self_truth=0 benchmark_overlap=0",
        flush=True,
    )


if __name__ == "__main__":
    main()
