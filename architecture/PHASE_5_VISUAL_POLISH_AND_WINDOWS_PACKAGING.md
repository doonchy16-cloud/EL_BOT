# EL Bot — Phase 5 Visual Polish & Windows Packaging

**Status:** 🟡 IMPLEMENTATION IN PROGRESS

Phase 5 is the first phase allowed to change the rendered hourglass/processing presentation and to create distributable Windows packages. Phase 4 remains the semantic/learning authority and must stay green.

## Visual polish contract

The processing overlay must prove all of the following in a real Chromium/Electron render:

- the hourglass rotates only between 0° and 180°; no 360° keyframe is allowed;
- sand visibly drains and fills instead of appearing mostly static;
- the stream visibly stops before a flip, remains stopped through the turn, then resumes only after the hourglass settles;
- grains are large/bright enough to read at normal app scale;
- the flip has a readable pause → turn → settle → resume rhythm rather than a snap;
- stage time resets when the stage changes while total time continues;
- a slow-stage warning changes more than one tiny glyph: the overlay/meta/hourglass must visibly enter a warning state;
- screenshot preview remains present while processing and can be enlarged without replacing the source image;
- screenshot observation capacity is expanded beyond the Phase-4 small visible-text cap while raw model prose still never becomes translation authority.

## Real-rendered proof

Source inspection is not enough. The Phase-5 proof harness must render the actual `⚡/🖥️` interface in Electron and capture:

- one complete hourglass cycle sampled at exactly **30 animation positions per second**;
- an MP4 encoded at 30 FPS from those rendered frames;
- a contact sheet spanning the full cycle;
- idle UI, warning-state UI, and enlarged screenshot-preview stills;
- a machine-readable proof record that includes expected frame count, FPS, cycle duration, rendered frame count, and 0°/180° rotation contract.

`⚡/🖥️` is intentionally an extensionless HTML authority file. Production does not ask Chromium to interpret that extensionless path directly: the Electron host validates it and materializes the exact bytes into a runtime `.html` file before loading it. The proof harness must mirror that boundary. It must copy the exact production UI bytes to a temporary `.html`, verify the materialized bytes are identical, then render that file in Electron before injecting the same production Phase-5 CSS/behavior layer. Directly rendering a different fixture or treating the extensionless source as a webpage is not acceptable proof.

Packaging status remains locked until this proof harness succeeds.

## Windows package contract

Phase 5 must produce both:

1. **EL Bot Setup** — x64 NSIS installer;
2. **EL Bot Portable** — x64 portable executable.

The distributed application must not depend on the source checkout or a separately installed Python interpreter. A Python 3.12 embeddable runtime is materialized into the application before packaging and the Electron host checks that packaged runtime first.

Ollama and `qwen2.5vl:7b` are **not bundled** because the model is a large replaceable external provider. Deterministic translation must still launch without Ollama; screenshot vision / AI fallback must fail safely or report provider unavailability when Ollama/model is absent.

The source developer launcher `▶️.cmd` remains supported.

## CI PASS gate

Phase 5 may become PASS only when one exact final `main` SHA proves:

- Phase 1–4 release gates remain green;
- Diagnostics remains 44/44;
- static UI checks confirm the new 180° animation and warning/preview contracts;
- the real rendered 30-FPS visual proof succeeds and is uploaded as `phase5-visual-proof`;
- the packaged app contains the embedded Python runtime and required engine sources;
- the packaged executable launches far enough for a packaged-runtime smoke test to verify the rendered interface;
- both Setup and Portable x64 artifacts are built and uploaded;
- the final manifest is `PASS` and the verifier refuses any weaker authority state;
- GitHub Actions succeeds on the exact final SHA.

No visual PASS may be inferred solely from CSS source, and no packaging PASS may be declared merely because electron-builder returned exit code 0.
