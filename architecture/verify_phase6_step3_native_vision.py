#!/usr/bin/env python3
"""Strict selected-generation native-vision gate for Forgey Insta G2."""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
STEP3 = ROOT / "data" / "phase6-step3"


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path)); spec = spec_from_loader(name, loader)
    if spec is None: raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec); sys.modules[name] = module; loader.exec_module(module); return module


def req(condition, message):
    if not condition: raise AssertionError(message)


def main() -> None:
    registry_path = STEP3 / "generation-registry.json"; proof_path = STEP3 / "g2-training-proof.json"
    image_el_path = STEP3 / "infer-selected-image-to-el.json"; image_abc_path = STEP3 / "infer-selected-image-to-abc.json"
    for path in (registry_path, proof_path, image_el_path, image_abc_path): req(path.is_file(), f"G2 native vision evidence missing: {path}")
    registry = json.loads(registry_path.read_text(encoding="utf-8")); req(registry.get("production_generation") == "G2", "native vision selected generation is not G2")
    record = dict((registry.get("generations") or {}).get("G2") or {}); req(record, "G2 registry record missing")
    model_path = Path(str(record.get("model_path") or "")); tokenizer_path = Path(str(record.get("tokenizer_path") or ""))
    req(model_path.is_file() and tokenizer_path.is_file(), "G2 visual model/tokenizer files missing")
    tokenizer_module = load("_p6s3nv_tokenizer", ROOT / "📚" / "✂️"); model_module = load("_p6s3nv_model", ROOT / "🧠" / "🤖")
    tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path); model, metadata = model_module.ForgeyInstaTransformer.load_checkpoint(model_path, map_location="cpu")
    report = model.parameter_report(); req(model.config.vision_enabled is True and report.vision_parameters > 0, "selected G2 is not natively vision-enabled")
    req(metadata.get("vision_enabled") is True and str(metadata.get("generation")) == "G2", "G2 native vision metadata missing")
    req(metadata.get("visual_semantic_bridge_exact") == "26/26", "G2 checkpoint did not preserve the deterministic visual semantic bridge")
    req(model.config.vocab_size == tokenizer.vocab_size and report.within_target, "G2 multimodal graph invalid")

    proof = json.loads(proof_path.read_text(encoding="utf-8")); vision = dict(proof.get("vision") or {}); candidate = dict(proof.get("candidate_metrics") or {})
    bridge = dict(proof.get("visual_semantic_bridge") or {})
    req(bridge.get("truth_source") == "deterministic native-vision concept authority", "G2 visual semantic bridge truth source changed")
    req(int(bridge.get("provider_authored_el_count", -1)) == 0 and int(bridge.get("unverified_self_output_truth_count", -1)) == 0, "G2 visual semantic bridge violated truth boundary")
    req(int(bridge.get("pair_total", 0)) == 26 and int(bridge.get("pair_exact_count", -1)) == 26, "G2 did not preserve all 26 deterministic visual semantic pairs before pixel refresh")
    req(int(candidate.get("visual_semantic_bridge_total", 0)) == 26 and int(candidate.get("visual_semantic_bridge_exact", -1)) == 26, "G2 candidate metrics omit exact 26/26 visual semantic bridge")
    req(vision.get("enabled") is True and vision.get("truth_source") == "deterministic synthetic pixel scenes", "G2 visual replay proof missing")
    req(int(vision.get("provider_generated_truth_count", -1)) == 0 and int(vision.get("unverified_self_output_truth_count", -1)) == 0, "G2 visual truth boundary failed")
    req(int(vision.get("probe_total", 0)) >= 8 and int(vision.get("probe_exact_count", -1)) == int(vision.get("probe_total", 0)), "G2 held-out visual probes are not all exact")
    req(candidate.get("vision_validation_pass") is True and int(candidate.get("vision_probe_exact", -1)) == int(candidate.get("vision_probe_total", 0)), "G2 promotion metrics omit native vision")
    req(all(bool(item.get("exact")) for item in vision.get("protected_text_probes", ())), "G2 vision refresh regressed text")

    trainer = (ROOT / "scripts" / "phase6-step3-train-g2.py").read_text(encoding="utf-8")
    req("visual_bridge_expected" in trainer and "len(visual_bridge_expected)!=26" in trainer, "G2 trainer does not lock the 26-pair visual semantic bridge")
    req("selected_bridge" in trainer and "visual_bridge_batch" in trainer, "G2 learning batches do not rehearse visual semantic truth")
    req("G2_SEMANTIC_BRIDGE" in trainer and "repair_limit=360" in trainer, "G2 lacks bounded semantic bridge repair")
    req('"visual_semantic_bridge_exact":"26/26"' in trainer, "G2 checkpoint metadata does not lock semantic bridge exactness")

    for path, direction in ((image_el_path, "IMAGE_TO_EL"), (image_abc_path, "IMAGE_TO_ABC")):
        evidence = json.loads(path.read_text(encoding="utf-8"))
        req(evidence.get("kind") == "forgey-native-vision-inference" and evidence.get("generation") == "G2", "wrong selected G2 vision evidence")
        req(evidence.get("direction") == direction and evidence.get("exact") is True, "selected G2 vision direction is not exact")
        req(int(evidence.get("provider_calls", -1)) == 0 and evidence.get("vision_enabled") is True, "selected G2 vision called provider or lacked vision graph")
        req(int(evidence.get("vision_parameters", 0)) == report.vision_parameters, "selected G2 visual parameter graph mismatch")
    print(f"PHASE6_STEP3_NATIVE_VISION_AUTHORITY_OK selected=G2 params={report.trainable_parameters} vision_params={report.vision_parameters} semantic_bridge=26/26 probes={vision['probe_exact_count']}/{vision['probe_total']} provider=0")


if __name__ == "__main__": main()
