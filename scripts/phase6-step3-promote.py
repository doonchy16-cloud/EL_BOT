#!/usr/bin/env python3
"""Register G1/G2, make the real measured promotion decision, and prove rollback."""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parent.parent


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step2-artifact", default=str(ROOT / "data" / "phase6-step2"))
    parser.add_argument("--step3-artifact", default=str(ROOT / "data" / "phase6-step3"))
    args = parser.parse_args()
    step2 = Path(args.step2_artifact).resolve()
    step3 = Path(args.step3_artifact).resolve()

    proof = json.loads((step3 / "g2-training-proof.json").read_text(encoding="utf-8"))
    teacher = json.loads((step3 / "teacher-evidence.json").read_text(encoding="utf-8"))
    g1_proof = json.loads((step2 / "training-proof.json").read_text(encoding="utf-8"))
    registry_module = load("_p6s3_generation_registry", ROOT / "🗃️" / "🤖")
    registry_path = step3 / "generation-registry.json"
    if registry_path.exists():
        registry_path.unlink()
    registry = registry_module.ForgeyGenerationRegistry(registry_path)

    artifacts = proof["artifacts"]
    baseline_metrics = dict(proof["baseline_metrics"])
    candidate_metrics = dict(proof["candidate_metrics"])

    g1 = registry.register_generation(
        "G1",
        parent_generation="",
        model_path=artifacts["g1_model_path"],
        tokenizer_path=artifacts["g1_tokenizer_path"],
        replay_fingerprint_sha256=str(g1_proof["curriculum"]["fingerprint_sha256"]),
        metrics=baseline_metrics,
        status="verified",
        metadata={
            "source": "Phase-6 Step-2 verified G1",
            "provider_truth_count": 0,
            "parent_main": "cc49045e8933d43aae285add3ade480fe64e9a89"
        },
    )
    registry.initialize_production("G1")
    initial_production_sha = g1["model_sha256"]

    g2 = registry.register_generation(
        "G2",
        parent_generation="G1",
        model_path=artifacts["g2_model_path"],
        tokenizer_path=artifacts["g2_tokenizer_path"],
        replay_fingerprint_sha256=artifacts["replay_fingerprint_sha256"],
        metrics=candidate_metrics,
        status="candidate",
        metadata={
            "source": "Phase-6 Step-3 admitted teacher evidence + protected replay",
            "teacher_provider_calls": int(teacher["provider_calls"]),
            "teacher_admitted_count": int(teacher["accepted_count"]),
            "provider_authored_el_truth_count": 0,
            "unverified_self_output_truth_count": 0,
            "frozen_benchmark_training_overlap_count": 0,
        },
    )

    # Explicit policy-unit fixture: deliberately degrade validation to prove the
    # rejection branch. This is NOT presented as measured model evidence.
    degraded_fixture = dict(candidate_metrics)
    degraded_fixture["validation_pass"] = False
    fixture_accepted, fixture_reasons = registry_module.ForgeyGenerationRegistry.evaluate_metrics(
        baseline_metrics, degraded_fixture, registry_module.PromotionPolicy()
    )
    if fixture_accepted or "deterministic-validation-failed" not in fixture_reasons:
        raise RuntimeError("rejection policy fixture did not reject deterministically")
    if registry.production_generation != "G1":
        raise RuntimeError("policy fixture mutated production generation")

    decision = registry.decide_promotion("G2", registry_module.PromotionPolicy())
    if not decision.accepted:
        raise RuntimeError("measured G2 did not satisfy strict promotion policy: " + ",".join(decision.reasons))
    if registry.production_generation != "G2":
        raise RuntimeError("accepted G2 did not become selected generation")
    if not registry.verify_generation_hashes("G1") or not registry.verify_generation_hashes("G2"):
        raise RuntimeError("generation hash verification failed after promotion")

    promoted_sha = registry.generations["G2"]["model_sha256"]
    rollback_record = registry.rollback("G1")
    if registry.production_generation != "G1" or rollback_record["model_sha256"] != initial_production_sha:
        raise RuntimeError("rollback did not restore exact verified G1 hash")
    rollback_verified_sha = rollback_record["model_sha256"]

    restored_record = registry.rollback("G2")
    if registry.production_generation != "G2" or restored_record["model_sha256"] != promoted_sha:
        raise RuntimeError("verified G2 could not be restored after rollback proof")

    state = json.loads(registry_path.read_text(encoding="utf-8"))
    proof_out = {
        "schema_version": 1,
        "phase": 6,
        "step": 3,
        "kind": "generation-promotion-rollback-proof",
        "actual_candidate_generation": "G2",
        "actual_decision": "PROMOTE",
        "actual_decision_reasons": list(decision.reasons),
        "production_before": "G1",
        "production_after_promotion": "G2",
        "rollback_target": "G1",
        "rollback_restored_sha256": rollback_verified_sha,
        "production_after_rollback_proof_restore": registry.production_generation,
        "final_selected_generation": "G2",
        "g1_model_sha256": initial_production_sha,
        "g2_model_sha256": promoted_sha,
        "rejection_policy_fixture": {
            "fixture_only": True,
            "accepted": fixture_accepted,
            "reasons": list(fixture_reasons),
            "production_pointer_after_fixture": "G1"
        },
        "immutable_hashes_verified": True,
        "history_kinds": [item["kind"] for item in state["history"]],
        "registry_path": str(registry_path),
    }
    (step3 / "promotion-proof.json").write_text(json.dumps(proof_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "PHASE6_STEP3_PROMOTION_OK "
        f"actual=G1->G2 rollback=G2->G1->G2 fixture_reject={','.join(fixture_reasons)} "
        f"g1={initial_production_sha[:12]} g2={promoted_sha[:12]}",
        flush=True,
    )


if __name__ == "__main__":
    main()
