# EL Bot — Phase 5 Visual Polish & Windows Packaging

**Status:** ✅ PASS

Phase 5 is complete. It changed the rendered hourglass/processing presentation and created distributable Windows packages while preserving Phase 4 as the semantic/learning authority.

## Visual polish contract

The processing overlay proves all of the following in a real Chromium/Electron render:

- the hourglass rotates only between 0° and 180°; no 360° keyframe is allowed;
- sand visibly drains and fills instead of appearing mostly static;
- the stream visibly stops before a flip, remains stopped through the turn, then resumes only after the hourglass settles;
- grains are large/bright enough to read at normal app scale;
- the flip has a readable pause → turn → settle → resume rhythm rather than a snap;
- stage time resets when the stage changes while total time continues;
- a slow-stage warning changes more than one tiny glyph: the overlay/meta/hourglass visibly enters a warning state;
- screenshot preview remains present while processing and can be enlarged without replacing the source image;
- screenshot observation capacity is expanded beyond the Phase-4 small visible-text cap while raw model prose still never becomes translation authority.

## Real-rendered proof

Source inspection is not sufficient. The Phase-5 proof harness renders the actual `⚡/🖥️` interface in Electron and captures:

- one complete 5.6-second hourglass cycle sampled at exactly **30 animation positions per second / 168 rendered frames**;
- an MP4 encoded at 30 FPS from those rendered frames;
- a contact sheet spanning the full cycle;
- idle UI, warning-state UI, and enlarged screenshot-preview stills;
- a machine-readable proof record containing expected frame count, FPS, cycle duration, rendered frame count, 0°/180° rotation evidence, stream pause/resume evidence, warning evidence, and preview-zoom evidence.

`⚡/🖥️` is intentionally an extensionless HTML authority file. Production validates it and materializes the exact bytes into a runtime `.html` file before loading it. The proof harness mirrors that boundary: it copies the exact production UI bytes to a temporary `.html`, verifies byte identity, renders that file in Electron, and injects the same production Phase-5 CSS/behavior layer. A separate fixture or direct interpretation of the extensionless source is not accepted as proof.

The completed proof is delivered with the Windows package through an exact-commit GitHub Release rather than relying on GitHub Actions artifact storage.

## Windows package contract

Phase 5 produces both:

1. **EL Bot Setup** — x64 NSIS installer;
2. **EL Bot Portable** — x64 portable executable.

The distributed application does not depend on the source checkout or a separately installed Python interpreter. Python **3.12.10 embeddable x64** is materialized into the application before packaging, and the Electron host checks that packaged runtime first.

Ollama and `qwen2.5vl:7b` are **not bundled** because the model is a large replaceable external provider. Deterministic translation still launches without Ollama; screenshot vision / AI fallback must fail safely or report provider unavailability when Ollama/model is absent.

The source developer launcher `▶️.cmd` remains supported.

## Delivery and release evidence

The Windows build is not considered releasable merely because electron-builder exits successfully. The CI release gate must prove:

- Phase 1–4 release gates remain green;
- Diagnostics remains **44/44**;
- static UI checks preserve the locked 180° animation and warning/preview contracts;
- real rendered 30-FPS proof succeeds;
- packaged app contains the embedded Python runtime and required engine sources;
- packaged `win-unpacked/EL-Bot.exe` launches and writes packaged-runtime smoke evidence proving the real interface rendered, Phase-5 polish loaded, bundled Python was selected, and bundled Python executed;
- Setup and Portable x64 outputs both exist;
- the release publisher computes SHA-256 evidence, creates a GitHub Release tied to the exact workflow SHA, uploads both EXEs + smoke evidence + visual proof + release manifest, and re-reads the release to verify required assets;
- the Phase-5 manifest is `PASS` and the verifier refuses weaker authority states;
- GitHub Actions succeeds on the exact final `main` SHA.

The authority-lock basis is candidate SHA `5faa4a93eb8f5a9e126544a130e0ada1f3750edf`, workflow run **#218**, and release tag `el-bot-v0.5.0-5faa4a93eb8f`. The final closeout still requires a fresh green workflow run on the exact merged authority-lock SHA; that exact-final-SHA result is CI evidence and is intentionally not self-embedded as a SHA inside the commit that creates it.

No visual PASS is inferred solely from CSS source, and no packaging PASS is declared merely because electron-builder returned exit code 0.
