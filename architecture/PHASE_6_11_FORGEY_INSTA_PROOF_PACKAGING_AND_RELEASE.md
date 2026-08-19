# Phase 6.11 — Forgey Insta Multimodal Proof, Packaging & Release

**Status:** 🚀 STEP 5 AUTHORIZED / IMPLEMENTATION IN PROGRESS

**Canonical intelligence:** `Forgey Insta:EL-Bot`

**Step-5 base:** exact Step-4 merge commit `e0ed1b2ac91ae1f9a716abfc0e93904469b91422`.

Step 5 is the final Phase-6 delivery gate. It does not change the 44-engine architecture or create an engine #45.

## Owner correction — native vision is release-blocking

On 2026-08-19, before final Phase-6 release, the Owner clarified that `Forgey Insta:EL-Bot` must be a **native vision model as well as a text/EL model**. This is newer authority than the pre-vision candidate evidence below and is therefore release-blocking.

Forgey Insta now remains one shared from-scratch encoder-decoder Transformer checkpoint, with two source modalities:

- **text** — the existing from-scratch byte-BPE / EL token path;
- **image** — RGB pixels projected by a learned patch projection, then combined with learned visual position, visual direction, and modality embeddings before entering the same Transformer encoder/decoder.

The native visual directions are `IMAGE_TO_EL` and `IMAGE_TO_ABC`. They are model-internal direction embeddings and do not expand or contaminate the EL/text vocabulary.

Native visual positive truth must come from independently known deterministic targets. The initial Phase-6 visual curriculum uses deterministic synthetic pixel scenes with known ABC and EL targets. Qwen/Ollama may not author positive native-vision training truth and Forgey may not use its own unverified outputs as positive truth.

G1 and G2 must both pass held-out native visual probes. G2 promotion must reject a candidate that regresses or fails native vision even when text metrics improve.

For production screenshots, native Forgey vision is attempted first. It may release directly only inside the deterministically trained/validated visual domain. Complex or OCR-heavy screenshots may fall through to the existing Qwen vision-sensor boundary; Qwen remains a sensor/fallback, never authoritative EL truth.

## Windows release contract

Phase 6 publishes version **0.6.0** as both:

1. **EL Bot Setup** — x64 NSIS installer;
2. **EL Bot Portable** — x64 portable executable.

Both packages must contain the same verified multimodal runtime authority.

## Self-contained Forgey runtime

The Phase-6 Windows application must not depend on the source checkout, a separately installed Python interpreter, or a separately installed PyTorch runtime for normal Forgey inference.

The package therefore materializes and includes:

- Python **3.12.10 embeddable x64**;
- PyTorch **2.13.0 CPU** and its required Python dependencies;
- the registry-selected verified **G2** multimodal model and tokenizer;
- the previously verified **G1** multimodal model and tokenizer so authenticated rollback remains real;
- the immutable generation registry and Step-3 evidence used by Current Status / Training Center;
- the native vision model/curriculum/runtime inference code required for provider-free image inference;
- the Step-4 status/admin runtime helpers;
- the authority manifests required for truthful model architecture/status reporting;
- the existing 44 deterministic engines and all normal app runtime files.

Qwen/Ollama remains an external replaceable semantic teacher and complex-screenshot fallback and is **not bundled**. Known verified Forgey-primary text and native-vision inference must work with zero provider calls.

## Portable generation registry

Training creates artifact paths that are specific to the build machine. Those paths are not distributable truth.

Before packaging, Step 5 copies each verified/production generation into `data/phase6-step3/runtime/<generation>/`, verifies copied SHA-256 hashes, and rewrites the package registry to paths relative to the application root. Model/tokenizer bytes, generation IDs, metrics, lineage, hashes, statuses, promotion history, selected-generation semantics, and native-vision weights must remain unchanged.

The package must contain both verified generations needed for the existing rollback contract. A package that contains only G2 while advertising G1 rollback is a FAIL.

## Package proof

`electron-builder` returning exit code 0 is not sufficient.

The Step-5 package gate must prove from `dist/win-unpacked/resources/app`, using the **packaged** embedded Python:

- Python is 3.12.x and comes from the package;
- PyTorch 2.13.x imports from the package;
- the packaged registry exists and selects G2;
- all packaged generation hashes verify;
- G2 checkpoint/tokenizer load successfully;
- runtime-derived trainable parameter count remains inside the locked 1–3M envelope;
- native vision is enabled and has real trainable visual parameters;
- the native visual geometry is the locked RGB 64×64 / 8×8-patch path unless newer Owner authority changes it;
- actual packaged model/tokenizer file sizes are non-zero;
- `vehicle powered by pedals with two wheels → 🚲` releases through Forgey G2;
- `🚲 → bicycle` releases through Forgey G2;
- a held-out PNG pixel fixture executes `IMAGE_TO_EL` exactly through packaged G2;
- the same held-out PNG fixture executes `IMAGE_TO_ABC` exactly through packaged G2;
- successful packaged text and native-image inferences report `provider_calls=0`;
- packaged diagnostics remain 44/44;
- the packaged Electron application renders the real interface, retains Phase-5 polish, selects bundled Python, and executes bundled Python;
- Current Status and Training Center truthfully expose native-vision availability, visual parameter count, modality, image/patch geometry, and vision-promotion metrics;
- the packaged Step-4 status/admin helpers and architecture authority are present.

Deterministic fallback alone cannot satisfy the packaged Forgey proof. A Qwen answer cannot satisfy native Forgey image proof.

## Phase-5 visual regression

Step 5 retains the exact Phase-5 real-rendered hourglass proof: 30 FPS, 168 rendered frames across the 5.6-second cycle, 0°↔180° behavior, sand stream pause/resume, warning state, and screenshot preview zoom. Phase 6 does not trade visual correctness for model packaging.

## CI / release topology

The Step-5 workflow runs on pull requests to `main` and pushes to `main`.

On a pull request it must build and prove the complete package but **must not publish a GitHub Release**.

`electron-builder` is a builder only. Its implicit CI publishing is explicitly disabled with `--publish never`. The sole release authority is `scripts/publish-step5-main-release.ps1`; no competing publisher is allowed.

After the verified Step-5 PR is merged, the exact `main` SHA runs the same package proof and then the release publisher:

- computes SHA-256 evidence for Setup, Portable, package smoke, packaged Forgey multimodal proof, separate packaged Image→EL / Image→ABC evidence, runtime-package manifest, and retained Phase-5 visual proof;
- creates a non-draft, non-prerelease GitHub Release tagged `el-bot-v0.6.0-<exact-main-short-sha>`;
- targets the exact workflow/main commit;
- uploads and re-reads all required assets;
- writes machine-readable release evidence including text+image modality and native-vision proof;
- fails if any required asset or exact-SHA binding is missing.

The legacy Phase-5 release publisher must not continue publishing v0.5 releases on future `main` pushes after Step 5 takes authority.

## Final Phase-6 acceptance

Phase 6 becomes PASS only when:

- Steps 1–4 remain green on the final Step-5 candidate;
- G1 and selected G2 pass native-vision held-out probes with zero provider-authored/self-authored positive truth;
- selected G2 promotion includes native-vision non-regression;
- Forgey-first screenshot routing safely releases learned native scenes and safely falls back for complex/OCR-heavy scenes;
- Step-5 packaged text and provider-free native-vision validation are green on the final candidate;
- Step 5 is merged to `main`;
- the Step-5 workflow is green on that exact merged `main` SHA;
- the Phase-6 GitHub Release exists for that exact SHA with all required verified assets;
- the release can be re-read and its tag/target/assets match generated evidence.

No package, model, vision capability, status, release, hash, or PASS result may be synthesized.
