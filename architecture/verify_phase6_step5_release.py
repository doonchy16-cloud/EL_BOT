#!/usr/bin/env python3
"""Strict Phase-6 Step-5 multimodal proof/packaging/release authority verifier."""
from __future__ import annotations
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent.parent

def req(condition, message):
    if not condition: raise AssertionError(message)
def text(path): return Path(path).read_text(encoding="utf-8")
def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    manifest=load(ROOT/"architecture"/"phase6_step5_release_manifest.json")
    req(manifest.get("phase")==6 and manifest.get("step")==5,"wrong Step-5 manifest")
    req(manifest.get("status") in {"IMPLEMENTATION_IN_PROGRESS","PASS"},"invalid Step-5 status")
    req(manifest.get("engine_count")==44 and manifest.get("new_engine_count")==0,"engine #45 forbidden")
    req(manifest.get("version")=="0.6.0","wrong Phase-6 package version")
    req(manifest["forgey_package"]["selected_generation"]=="G2","G2 not package authority")
    req(manifest["forgey_package"]["rollback_generation"]=="G1","G1 rollback artifact missing from authority")
    req(manifest["forgey_package"].get("native_vision_required") is True,"native Forgey vision is not a release requirement")
    req(manifest["embedded_runtime"]["python"]=="3.12.10","embedded Python contract changed")
    req(str(manifest["embedded_runtime"]["torch"]).startswith("2.13.0"),"embedded Torch contract changed")
    req(manifest["release"]["publish_from_main_only"] is True and manifest["release"]["publish_from_pr"] is False,"release branch boundary weakened")

    package=load(ROOT/"package.json")
    req(package.get("version")=="0.6.0","package.json not Phase-6 version")
    req("--publish never" in str((package.get("scripts") or {}).get("build:windows","")),"electron-builder implicit publishing is not disabled")
    files=list((package.get("build") or {}).get("files") or [])
    req("!scripts/**" not in files,"runtime admin/status scripts excluded from package")
    req("!architecture/**" not in files,"runtime architecture authority excluded from package")
    targets=list(((package.get("build") or {}).get("win") or {}).get("target") or [])
    target_names={str(item.get("target")) for item in targets if isinstance(item,dict)}
    req({"nsis","portable"}.issubset(target_names),"Setup/Portable targets missing")

    runtime_materializer=text(ROOT/"scripts"/"materialize-phase6-runtime.py")
    python_materializer=text(ROOT/"scripts"/"materialize-phase6-python.ps1")
    package_proof=text(ROOT/"scripts"/"phase6-step5-package-forgey-proof.py")
    publisher=text(ROOT/"scripts"/"publish-step5-main-release.ps1")
    workflow=text(ROOT/".github"/"workflows"/"phase6-step5-release.yml")
    model=text(ROOT/"🧠"/"🤖"); vision=text(ROOT/"🧠"/"👁️"); screenshot=text(ROOT/"📸"/"📸")
    phase6=text(ROOT/"architecture"/"PHASE_6_FORGEY_INSTA_EL_BOT_AUTHORITY.md")
    step5=text(ROOT/"architecture"/"PHASE_6_11_FORGEY_INSTA_PROOF_PACKAGING_AND_RELEASE.md")

    req("runtime/<generation>" in step5 and "relative to the application root" in step5,"portable registry authority missing")
    req("native vision" in step5.lower() and "provider-free" in step5.lower(),"Step-5 authority does not require packaged native vision")
    req("selected != \"G2\"" in runtime_materializer and "relative_to_application_root" in runtime_materializer,"portable G2 registry materializer weakened")
    req("materialize-python.ps1" in python_materializer and "torch.__version__.startswith('2.13.0')" in python_materializer,"embedded Python/Torch materializer missing")
    req("vision_patch_projection" in model and "forward_image" in model and "greedy_generate_image" in model,"Forgey model is not natively multimodal")
    req("deterministic synthetic pixel scenes" in vision and "provider_generated_truth_count" in vision,"native vision truth boundary missing")
    req("Forgey Insta native vision is attempted first" in screenshot and "native_forgey_vision_released" in screenshot,"screenshot path is not Forgey-first")
    req("dist" in package_proof and "win-unpacked" in package_proof and "forgey_primary_released" in package_proof,"packaged Forgey proof missing")
    req("vision_enabled" in package_proof and "vision_parameters" in package_proof and "IMAGE_TO_EL" in package_proof and "IMAGE_TO_ABC" in package_proof and "native_vision_provider_calls" in package_proof,"packaged native vision proof too weak")
    req("1788672" not in package_proof,"historical pre-vision parameter count is hard-coded into package proof")
    req("refs/heads/main" in publisher and "0.6.0" in publisher and "phase6-package-forgey-proof.json" in publisher,"exact-main Phase-6 publisher missing")
    req("phase6-package-vision-el.json" in publisher and "phase6-package-vision-abc.json" in publisher,"release omits native vision evidence assets")
    req("phase6-release-manifest.json" in publisher and "runtime-package-manifest.json" in publisher,"release evidence assets incomplete")
    req(not (ROOT/"scripts"/"publish-phase6-release.ps1").exists(),"historical Step-1/2/3 publisher sentinel was reused")

    req("push:" in workflow and "branches: [main]" in workflow and "workflow_dispatch:" in workflow and "pull_request:" not in workflow,"Step-5 workflow must be single main/manual completion authority")
    for marker in (
        "phase6-step2-train-g1.py","phase6-step2-train-vision.py","verify_phase6_step2_native_vision.py",
        "phase6-step3-teach.py","phase6-step3-train-g2.py","phase6-step3-refresh-vision.py","phase6-step3-promote.py","verify_phase6_step3_native_vision.py",
        "phase6-vision-infer.py","phase6-step4-runtime-proof.js","phase6-step4-console-proof.js","ci-screenshot-vision.ps1","CURRENT_COMPLETE_REGRESSION_FAILED",
        "materialize-phase6-runtime.py","materialize-phase6-python.ps1","proof:visual","build:windows","package-smoke.json",
        "phase6-step5-package-forgey-proof.py","verify_phase6_step5_release.py","publish-step5-main-release.ps1",
    ):
        req(marker in workflow,f"Step-5 workflow missing {marker}")
    req("verify_phase1_architecture.py" not in workflow,"obsolete fixed-501 Phase-1 release verifier reintroduced into Step 5")
    req("LEGACY_RELEASE_ENGINE_REGRESSION_FAILED" not in workflow,"obsolete legacy release-engine gate reintroduced into Step 5")
    req("github.event_name == 'push'" in workflow and "refs/heads/main" in workflow,"publisher is not main-only in workflow")
    req("ConvertFromUtf32(0x1F9E0)" in workflow and "ConvertFromUtf32(0x1F916)" in workflow and "ConvertFromUtf32(0x1F441)" in workflow,"Windows package runtime checks do not construct Unicode paths from ASCII-safe codepoints")
    req("'🧠\\🤖'" not in workflow and "'🧠\\👁️'" not in workflow,"literal emoji filesystem paths reintroduced into Windows PowerShell package step")

    req("STEP 4 PASS+MERGED" in phase6,"Phase-6 authority does not record Step-4 merge")
    req("native vision" in phase6.lower(),"Phase-6 authority does not record Owner native-vision correction")
    req(("STEP 5 AUTHORIZED+IN PROGRESS" in phase6) or ("STEP 5 PASS" in phase6),"Phase-6 authority does not authorize Step 5")
    req("Step-4 merge commit" in step5 and "e0ed1b2ac91ae1f9a716abfc0e93904469b91422" in step5,"Step-5 base merge not locked")
    req("Phase 6 becomes PASS only when" in step5,"exact-main final acceptance missing")
    req(not (ROOT/".github"/"workflows"/"🧪.yml").exists(),"legacy Phase-5 main auto-release workflow still active")

    print("PHASE6_STEP5_AUTHORITY_OK version=0.6.0 multimodal=TEXT+IMAGE native_vision=REQUIRED provider_free_package_vision=REQUIRED python=3.12.10 torch=2.13 G2=PACKAGED G1=ROLLBACK current44=REGRESSED phase4_5=REGRESSED release=MAIN_ONLY engines=44")

if __name__=="__main__": main()
