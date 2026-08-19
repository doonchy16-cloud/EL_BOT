#!/usr/bin/env python3
"""Strict Phase-6 Step-5 proof/packaging/release authority verifier."""
from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent


def req(condition, message):
    if not condition:
        raise AssertionError(message)


def text(path):
    return Path(path).read_text(encoding="utf-8")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    manifest = load(ROOT / "architecture" / "phase6_step5_release_manifest.json")
    req(manifest.get("phase") == 6 and manifest.get("step") == 5, "wrong Step-5 manifest")
    req(manifest.get("status") in {"IMPLEMENTATION_IN_PROGRESS", "PASS"}, "invalid Step-5 status")
    req(manifest.get("engine_count") == 44 and manifest.get("new_engine_count") == 0, "engine #45 forbidden")
    req(manifest.get("version") == "0.6.0", "wrong Phase-6 package version")
    req(manifest["forgey_package"]["selected_generation"] == "G2", "G2 not package authority")
    req(manifest["forgey_package"]["rollback_generation"] == "G1", "G1 rollback artifact missing from authority")
    req(manifest["embedded_runtime"]["python"] == "3.12.10", "embedded Python contract changed")
    req(str(manifest["embedded_runtime"]["torch"]).startswith("2.13.0"), "embedded Torch contract changed")
    req(manifest["release"]["publish_from_main_only"] is True and manifest["release"]["publish_from_pr"] is False, "release branch boundary weakened")

    package = load(ROOT / "package.json")
    req(package.get("version") == "0.6.0", "package.json not Phase-6 version")
    files = list((package.get("build") or {}).get("files") or [])
    req("!scripts/**" not in files, "runtime admin/status scripts excluded from package")
    req("!architecture/**" not in files, "runtime architecture authority excluded from package")
    targets = list(((package.get("build") or {}).get("win") or {}).get("target") or [])
    target_names = {str(item.get("target")) for item in targets if isinstance(item, dict)}
    req({"nsis", "portable"}.issubset(target_names), "Setup/Portable targets missing")

    runtime_materializer = text(ROOT / "scripts" / "materialize-phase6-runtime.py")
    python_materializer = text(ROOT / "scripts" / "materialize-phase6-python.ps1")
    package_proof = text(ROOT / "scripts" / "phase6-step5-package-forgey-proof.py")
    publisher = text(ROOT / "scripts" / "publish-phase6-release.ps1")
    workflow = text(ROOT / ".github" / "workflows" / "phase6-step5-release.yml")
    phase6 = text(ROOT / "architecture" / "PHASE_6_FORGEY_INSTA_EL_BOT_AUTHORITY.md")
    step5 = text(ROOT / "architecture" / "PHASE_6_11_FORGEY_INSTA_PROOF_PACKAGING_AND_RELEASE.md")
    legacy = text(ROOT / ".github" / "workflows" / "🧪.yml")

    req("runtime/<generation>" in step5 and "relative to the application root" in step5, "portable registry authority missing")
    req("selected != \"G2\"" in runtime_materializer and "relative_to_application_root" in runtime_materializer, "portable G2 registry materializer weakened")
    req("materialize-python.ps1" in python_materializer and "torch.__version__.startswith('2.13.0')" in python_materializer, "embedded Python/Torch materializer missing")
    req("dist" in package_proof and "win-unpacked" in package_proof and "forgey_primary_released" in package_proof, "packaged Forgey proof missing")
    req("provider_calls" in package_proof and "1788672" in package_proof and "44/44" in package_proof, "packaged Forgey proof too weak")
    req("refs/heads/main" in publisher and "0.6.0" in publisher and "phase6-package-forgey-proof.json" in publisher, "exact-main Phase-6 publisher missing")
    req("phase6-release-manifest.json" in publisher and "runtime-package-manifest.json" in publisher, "release evidence assets incomplete")

    req("pull_request:" in workflow and "push:" in workflow and "branches: [main]" in workflow, "Step-5 PR/main workflow topology missing")
    for marker in (
        "phase6-step2-train-g1.py", "phase6-step3-teach.py", "phase6-step3-train-g2.py", "phase6-step3-promote.py",
        "materialize-phase6-runtime.py", "materialize-phase6-python.ps1", "proof:visual", "build:windows",
        "package-smoke.json", "phase6-step5-package-forgey-proof.py", "verify_phase6_step5_release.py", "publish-phase6-release.ps1",
    ):
        req(marker in workflow, f"Step-5 workflow missing {marker}")
    req("github.event_name == 'push'" in workflow and "refs/heads/main" in workflow, "publisher is not main-only in workflow")

    req("STEP 4 PASS+MERGED" in phase6, "Phase-6 authority does not record Step-4 merge")
    req(("STEP 5 AUTHORIZED+IN PROGRESS" in phase6) or ("STEP 5 PASS" in phase6), "Phase-6 authority does not authorize Step 5")
    req("Step-4 merge commit" in step5 and "e0ed1b2ac91ae1f9a716abfc0e93904469b91422" in step5, "Step-5 base merge not locked")
    req("Phase 6 becomes PASS only when" in step5, "exact-main final acceptance missing")

    # The Phase-5 release workflow remains historical/dispatchable but must no longer publish on future main pushes.
    legacy_push_block = legacy.split("permissions:", 1)[0]
    req("- main" not in legacy_push_block, "legacy Phase-5 publisher still triggers on main")

    print("PHASE6_STEP5_AUTHORITY_OK version=0.6.0 python=3.12.10 torch=2.13 G2=PACKAGED G1=ROLLBACK release=MAIN_ONLY engines=44")


if __name__ == "__main__":
    main()
