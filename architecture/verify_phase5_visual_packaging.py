#!/usr/bin/env python3
"""Phase 5 visual-polish and Windows-packaging final authority gate."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "architecture" / "phase5_visual_packaging_manifest.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest.get("phase") == 5, "wrong Phase-5 manifest")
    require(manifest.get("status") == "PASS", "Phase 5 authority is not PASS")
    require(manifest.get("source_present_target_engines") == 44, "Phase 5 changed 44-engine authority")
    require(manifest.get("canonical_base_vocabulary_count") == 501, "Phase 5 changed base vocabulary authority")
    phase4 = json.loads((ROOT / "architecture" / "phase4_ai_learning_manifest.json").read_text(encoding="utf-8"))
    require(phase4.get("status") == "PASS", "Phase 4 is no longer PASS")

    visual = manifest.get("visual_proof") or {}
    packaging = manifest.get("packaging") or {}
    evidence = manifest.get("evidence") or {}
    require(visual.get("status") == "PASS", "PASS requires visual proof PASS")
    require(visual.get("fps") == 30 and visual.get("rendered_frames") == 168, "visual proof frame contract missing")
    require(visual.get("cycle_seconds") == 5.6 and visual.get("rotation") == "0-180-0", "visual proof rotation contract missing")
    require(bool(visual.get("sand_pause_resume_verified")), "sand pause/resume proof missing")
    require(bool(visual.get("warning_state_verified")), "warning-state proof missing")
    require(bool(visual.get("preview_zoom_verified")), "preview-zoom proof missing")
    require(visual.get("delivery") == "github-release", "visual proof delivery is not GitHub Release")

    require(packaging.get("status") == "PASS", "PASS requires packaging PASS")
    require(packaging.get("embedded_python") == "3.12.10", "embedded Python authority mismatch")
    require(packaging.get("packaged_runtime_smoke") == "PASS", "packaged runtime smoke authority missing")
    require(packaging.get("delivery") == "github-release", "package delivery is not GitHub Release")

    require(bool(evidence.get("authority_lock_basis_sha")), "authority lock basis SHA missing")
    require(int(evidence.get("authority_lock_basis_run", 0)) > 0, "authority lock basis run missing")
    require(bool(evidence.get("authority_lock_basis_release_tag")), "authority lock basis release tag missing")
    require(evidence.get("exact_final_sha_ci_required") is True, "exact-final-SHA CI requirement missing")
    require(evidence.get("release_assets_include_sha256_manifest") is True, "release SHA-256 manifest requirement missing")

    css = (ROOT / "⚡" / "✨").read_text(encoding="utf-8")
    enhancement = (ROOT / "⚡" / "🎞️").read_text(encoding="utf-8")
    host = (ROOT / "⚡" / "⚡").read_text(encoding="utf-8")
    vision = (ROOT / "📸" / "📸").read_text(encoding="utf-8")
    proof = (ROOT / "scripts" / "phase5-visual-proof.js").read_text(encoding="utf-8")
    publisher = (ROOT / "scripts" / "publish-phase5-release.ps1").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "🧪.yml").read_text(encoding="utf-8")

    require("rotate(180deg)" in css and "rotate(360deg)" not in css, "hourglass must remain 0↔180 only")
    require("5.6s" in css and "sandStreamFlow" in css and "flowDownWindow" in css and "flowUpWindow" in css, "Phase-5 sand timing contract missing")
    require(".processing.warn" in css and ".preview.zoom" in css and "ui-monospace" in css, "warning/zoom/timer polish missing")
    require("MutationObserver" in enhancement and "Enlarge screenshot preview" in enhancement and "Escape" in enhancement, "preview/warning behavior missing")
    require("POLISH_CSS" in host and "POLISH_JS" in host and "applyPhase5Enhancements" in host, "production host does not load Phase-5 visuals")
    require("path.join(ROOT, 'python', 'python.exe')" in host, "packaged Python is not first-class runtime candidate")
    require("EL_PACKAGE_SMOKE_FILE" in host and "app.isPackaged" in host and "bundled_python" in host, "packaged smoke evidence mode missing")

    require('"visible_text":12' in vision and '"objects":8' in vision and '"controls":8' in vision, "expanded screenshot evidence limits missing")
    require("vision_evidence" in vision and "transcribe readable text in natural visual reading order" in vision, "expanded screenshot evidence contract missing")
    require("Do not translate into Emoji Language" in vision and "not a translator" in vision, "vision authority boundary changed")

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    require(package.get("main") == "main.js", "package main entry incorrect")
    build = package.get("build") or {}
    require(build.get("appId") == "com.thespark.elbot" and build.get("productName") == "EL Bot", "package identity mismatch")
    require(build.get("asar") is False, "executed Python sources must remain outside ASAR")
    win = build.get("win") or {}
    targets = {item.get("target") for item in win.get("target", []) if isinstance(item, dict)}
    require({"nsis", "portable"}.issubset(targets), "Windows installer + portable targets required")
    require(package.get("devDependencies", {}).get("electron") == "43.2.0", "Electron version is not pinned")
    require(package.get("devDependencies", {}).get("electron-builder") == "26.15.3", "electron-builder version is not pinned")
    require((ROOT / "main.js").is_file(), "package main wrapper missing")
    require((ROOT / "scripts" / "materialize-python.ps1").is_file(), "embedded Python materializer missing")
    require((ROOT / "scripts" / "materialize-icon.js").is_file(), "package icon materializer missing")
    require((ROOT / "📦").is_dir() and (ROOT / "📦" / "README-WINDOWS.md").is_file(), "real package directory missing")

    require("const FPS = 30" in proof and "const CYCLE_MS = 5600" in proof, "30-FPS proof timing missing")
    require("sampledAngles" in proof and "streamOpacity" in proof and "hourglass-30fps.mp4" in proof and "hourglass-contact-sheet.png" in proof, "rendered proof outputs missing")
    require("capturePage" in proof and "document.getAnimations" in proof, "proof is not based on real rendered animation frames")

    require("phase5-release-manifest.json" in publisher and "Get-FileHash" in publisher and "releases" in publisher, "GitHub Release publisher evidence contract missing")
    require("publish-phase5-release.ps1" in workflow, "workflow does not enforce GitHub Release publication")
    require("actions/upload-artifact" not in workflow, "Phase 5 still depends on Actions artifact quota")

    print("✅5️⃣PASS 🎞️30FPS✅ ⏳0↔180✅ 🏖️⏸️✅ ⚠️✅ 📸🔍✅ 🐍📦✅ 🪟NSIS+PORTABLE✅ 📤RELEASE✅")


if __name__ == "__main__":
    main()
