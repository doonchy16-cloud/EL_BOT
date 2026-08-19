# Phase 6.11 — Forgey Insta Proof, Packaging & Release

**Status:** 🚀 STEP 5 AUTHORIZED / IMPLEMENTATION IN PROGRESS

**Canonical intelligence:** `Forgey Insta:EL-Bot`

**Step-5 base:** exact Step-4 merge commit `e0ed1b2ac91ae1f9a716abfc0e93904469b91422`.

Step 5 is the final Phase-6 delivery gate. It does not change the 44-engine architecture or invent another model generation. It packages the already-verified Step-4 Forgey runtime into a self-contained Windows application and proves that the packaged application actually uses Forgey G2.

## Windows release contract

Phase 6 publishes version **0.6.0** as both:

1. **EL Bot Setup** — x64 NSIS installer;
2. **EL Bot Portable** — x64 portable executable.

Both packages must contain the same verified runtime authority.

## Self-contained Forgey runtime

The Phase-6 Windows application must not depend on the source checkout, a separately installed Python interpreter, or a separately installed PyTorch runtime for normal Forgey inference.

The package therefore materializes and includes:

- Python **3.12.10 embeddable x64**;
- PyTorch **2.13.0 CPU** and its required Python dependencies;
- the registry-selected verified **G2** model and tokenizer;
- the previously verified **G1** model and tokenizer so authenticated rollback remains real;
- the immutable generation registry and Step-3 evidence used by Current Status / Training Center;
- the Step-4 status/admin runtime helpers;
- the authority manifests required for truthful model architecture/status reporting;
- the existing 44 deterministic engines and all normal app runtime files.

Qwen/Ollama remains an external replaceable semantic teacher/fallback and is **not bundled**. Known verified Forgey-primary translation must work with zero provider calls. If an unresolved case requires Qwen and Ollama is unavailable, that dependency must fail safely rather than being hidden or simulated.

## Portable generation registry

Training creates artifact paths that are specific to the build machine. Those paths are not distributable truth.

Before packaging, Step 5 copies each verified/production generation into `data/phase6-step3/runtime/<generation>/`, verifies copied SHA-256 hashes, and rewrites the package registry to paths relative to the application root. Model/tokenizer bytes, generation IDs, metrics, lineage, hashes, statuses, promotion history, and selected-generation semantics must remain unchanged.

The package must contain both verified generations needed for the existing rollback contract. A package that contains only G2 while advertising G1 rollback is a FAIL.

## Package proof

`electron-builder` returning exit code 0 is not sufficient.

The Step-5 package gate must prove from `dist/win-unpacked/resources/app`, using the **packaged** embedded Python:

- Python is 3.12.x and comes from the package;
- PyTorch 2.13.x imports from the package;
- the packaged registry exists and selects G2;
- all packaged generation hashes verify;
- G2 checkpoint/tokenizer load successfully;
- runtime-derived trainable parameter count remains 1,788,672;
- actual packaged model/tokenizer file sizes are non-zero;
- `vehicle powered by pedals with two wheels → 🚲` releases through Forgey G2;
- `🚲 → bicycle` releases through Forgey G2;
- both successful packaged inferences report `provider_calls=0` and round-trip PASS;
- packaged diagnostics remain 44/44;
- the packaged Electron application renders the real interface, retains Phase-5 polish, selects bundled Python, and executes bundled Python;
- the packaged Step-4 status/admin helpers and architecture authority required by the two-page control room are present.

Deterministic fallback alone cannot satisfy the packaged Forgey proof.

## Phase-5 visual regression

Step 5 retains the exact Phase-5 real-rendered hourglass proof: 30 FPS, 168 rendered frames across the 5.6-second cycle, 0°↔180° behavior, sand stream pause/resume, warning state, and screenshot preview zoom. Phase 6 does not trade visual correctness for model packaging.

## CI / release topology

The Step-5 workflow runs on pull requests to `main` and on pushes to `main`.

On a pull request it must build and prove the complete package but **must not publish a GitHub Release**.

After the verified Step-5 PR is merged, the exact `main` SHA runs the same package proof and then the release publisher:

- computes SHA-256 evidence for Setup, Portable, package smoke, packaged Forgey proof, runtime-package manifest, and retained Phase-5 visual proof;
- creates a non-draft, non-prerelease GitHub Release tagged `el-bot-v0.6.0-<exact-main-short-sha>`;
- targets the exact workflow/main commit;
- uploads and re-reads all required assets;
- writes machine-readable release evidence;
- fails if any required asset or exact-SHA binding is missing.

The legacy Phase-5 release publisher must not continue publishing v0.5 releases on future `main` pushes after Step 5 takes authority.

## Final Phase-6 acceptance

Phase 6 becomes PASS only when:

- Steps 1–4 remain green on the final Step-5 candidate;
- Step-5 package validation is green on the final candidate;
- Step 5 is merged to `main`;
- the Step-5 workflow is green on that exact merged `main` SHA;
- the Phase-6 GitHub Release exists for that exact SHA with all required verified assets;
- the release can be re-read and its tag/target/assets match the generated evidence.

No package, model, status, release, hash, or PASS result may be synthesized.
