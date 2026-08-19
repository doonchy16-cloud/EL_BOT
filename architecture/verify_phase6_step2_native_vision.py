#!/usr/bin/env python3
"""Strict native-vision evidence gate for Forgey Insta G1."""
from __future__ import annotations
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parent.parent; ARTIFACT=ROOT/"data"/"phase6-step2"

def load(name,path):
    loader=SourceFileLoader(name,str(path)); spec=spec_from_loader(name,loader)
    if spec is None: raise RuntimeError(f"cannot load {path}")
    module=module_from_spec(spec); sys.modules[name]=module; loader.exec_module(module); return module

def req(condition,message):
    if not condition: raise AssertionError(message)

def main():
    tokenizer_path=ARTIFACT/"tokenizer.json"; model_path=ARTIFACT/"forgey-insta-g1.pt"; proof_path=ARTIFACT/"training-proof.json"; forward_path=ARTIFACT/"infer-image-to-el.json"; reverse_path=ARTIFACT/"infer-image-to-abc.json"
    for path in (tokenizer_path,model_path,proof_path,forward_path,reverse_path): req(path.is_file(),f"native-vision evidence missing: {path}")
    tokenizer_module=load("_p6s2nv_tokenizer",ROOT/"📚"/"✂️"); model_module=load("_p6s2nv_model",ROOT/"🧠"/"🤖"); tokenizer=tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path); model,metadata=model_module.ForgeyInstaTransformer.load_checkpoint(model_path,map_location="cpu"); report=model.parameter_report(); config=model.config
    req(config.vision_enabled is True,"Forgey Insta G1 is not vision-enabled"); req(config.vision_image_size==64 and config.vision_patch_size==8 and config.vision_channels==3,"native vision geometry changed"); req(config.visual_token_count==64,"native vision patch token count changed"); req(report.vision_parameters>0,"native vision has no trainable parameters"); req(report.within_target,"multimodal Forgey Insta left 1-3M parameter envelope"); req(config.vocab_size==tokenizer.vocab_size,"native vision checkpoint/tokenizer mismatch"); req(metadata.get("vision_enabled") is True,"G1 checkpoint metadata lacks native vision")
    proof=json.loads(proof_path.read_text(encoding="utf-8")); vision=dict(proof.get("vision") or {})
    req(vision.get("enabled") is True and vision.get("modality")=="native pixels","G1 visual training proof missing"); req(vision.get("truth_source")=="deterministic synthetic pixel scenes","visual positive truth is not independently deterministic"); req("frozen Forgey text/EL encoder memory" in str(vision.get("grounding_source") or ""),"visual grounding source is not the verified frozen semantic memory"); req(vision.get("shared_text_parameters_updated") is False,"G1 visual grounding mutated verified text parameters"); req(int(vision.get("provider_generated_truth_count",-1))==0,"provider-generated visual truth leaked into G1"); req(int(vision.get("unverified_self_output_truth_count",-1))==0,"self-output visual truth leaked into G1"); req(int(vision.get("probe_total",0))>=8 and int(vision.get("probe_exact_count",-1))==int(vision.get("probe_total",0)),"G1 held-out visual probes are not all exact")
    req("concept-identity" in str(vision.get("collapse_prevention") or "") and "direction isolated" in str(vision.get("collapse_prevention") or ""),"visual contrastive semantics do not keep concept identity separate from output direction")
    req(float(vision.get("late_ce_loss",999))<float(vision.get("early_ce_loss",0)),"G1 visual decoder loss did not improve"); req(float(vision.get("late_alignment_loss",999))<float(vision.get("early_alignment_loss",0)),"G1 visual semantic alignment did not improve"); req(int(vision.get("vision_parameters",0))==report.vision_parameters,"G1 visual parameter proof differs from graph"); protected=tuple(vision.get("protected_text_probes",())); req(len(protected)>=8 and all(bool(item.get("exact")) for item in protected),"vision grounding did not preserve all protected text probes")
    image_to_el=json.loads(forward_path.read_text(encoding="utf-8")); image_to_abc=json.loads(reverse_path.read_text(encoding="utf-8"))
    for evidence,direction in ((image_to_el,"IMAGE_TO_EL"),(image_to_abc,"IMAGE_TO_ABC")):
        req(evidence.get("kind")=="forgey-native-vision-inference","wrong native vision inference evidence kind"); req(evidence.get("generation")=="G1" and evidence.get("direction")==direction,"wrong G1 vision generation/direction"); req(evidence.get("vision_enabled") is True and int(evidence.get("vision_parameters",0))==report.vision_parameters,"fresh vision process loaded wrong graph"); req(int(evidence.get("provider_calls",-1))==0,"provider call occurred during G1 native vision inference"); req(evidence.get("exact") is True and bool(evidence.get("prediction")),"fresh G1 native vision inference is not exact")
    guarded={"model":read(ROOT/"🧠"/"🤖"),"vision":read(ROOT/"🧠"/"👁️"),"vision_train":read(ROOT/"scripts"/"phase6-step2-train-vision.py"),"vision_infer":read(ROOT/"scripts"/"phase6-vision-infer.py")}
    req("keys=[item.concept for item in selected]" in guarded["vision_train"],"visual content contrastive key is not concept-only")
    req("keys=[(item.concept,item.direction)" not in guarded["vision_train"],"output direction was incorrectly reintroduced as a visual-content negative")
    for name,source in guarded.items():
        lowered=source.lower()
        for forbidden in ("qwen2.5vl","ollamaconnector","chat_internal","generate_internal","urllib.request"): req(forbidden not in lowered,f"provider coupling leaked into native vision {name}: {forbidden}")
    print(f"PHASE6_STEP2_NATIVE_VISION_AUTHORITY_OK params={report.trainable_parameters} vision_params={report.vision_parameters} probes={vision['probe_exact_count']}/{vision['probe_total']} text={len(protected)}/{len(protected)} provider=0")

def read(path): return Path(path).read_text(encoding="utf-8")
if __name__=="__main__": main()
