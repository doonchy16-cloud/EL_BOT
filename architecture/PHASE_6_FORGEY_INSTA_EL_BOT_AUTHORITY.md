# EL Bot — Phase 6 Canonical Authority

## Forgey Insta:EL-Bot

**Status:** 🔒 STEP 1 PASS+MERGED / STEP 2 PASS+MERGED / STEP 3 PASS+MERGED / STEP 4 PASS+MERGED / STEP 5 AUTHORIZED+IN PROGRESS

**Canonical intelligence name:** `Forgey Insta:EL-Bot`

This file is the canonical Phase-6 authority. Newer explicit Owner decisions override older text in this file and must be incorporated before final release.

## Mission

`Forgey Insta:EL-Bot` is EL Bot's small, from-scratch, EL-specialized **multimodal** neural intelligence. Phase 6 makes it the primary semantic/conversion path for ABC→EL and EL→ABC and gives the same model native pixel vision for Image→EL and Image→ABC, while preserving the existing 44-engine architecture as deterministic support, validation, integrity, learning, recovery, and orchestration authority. Phase 6 does not add engine #45.

Qwen `qwen2.5vl:7b` is temporary teacher/fallback semantic and complex-screenshot intelligence only. It cannot directly release authoritative EL, become canonical truth, bypass deterministic validation, mutate production weights, or author positive native-vision training truth.

## Owner correction — native vision

On **2026-08-19**, before Phase-6 final release, the Owner explicitly required `Forgey Insta:EL-Bot` to be a vision model too. This correction is release-blocking and supersedes the earlier text-only assumption.

The implementation remains one shared from-scratch encoder-decoder Transformer checkpoint:
- text sources use the existing from-scratch byte-BPE / EL embedding path;
- image sources use learned RGB patch projection plus learned visual positional, direction, and modality embeddings;
- both paths enter the same Transformer encoder/decoder and output through the same authoritative tokenizer/output projection;
- visual directions are `IMAGE_TO_EL` and `IMAGE_TO_ABC` and do not create new EL vocabulary tokens;
- visual positive truth is independently deterministic, never provider-authored and never unverified self-output;
- G2 promotion requires native-vision non-regression;
- production screenshot routing attempts native Forgey first and only releases within its validated visual domain, otherwise safely falling back to the existing Qwen sensor boundary.

The historical Step-2 observation of **1,788,672** trainable parameters is pre-native-vision evidence only. The final multimodal parameter count must be runtime-derived from the actual graph and remain inside the locked **1–3M** target.

## Completed authority

### Step 1 — Knowledge Foundation ✅ PASS / MERGED

Step-1 merge commit: `902a79fec235f77c1bf3b4c7edf82b9a0127b900`.

Established released Unicode Emoji authority, Open English WordNet 2025+ lexical/sense/morphology/taxonomy data, provider-free lexical retrieval, atomic official emoji/EL tokenizer-source authority, historical-seed compatibility without a public 501 ceiling, and truthful product-facing knowledge status.

### Step 2 — Forgey Insta G0/G1 ✅ PASS / MERGED

Step-2 merge commit: `cc49045e8933d43aae285add3ade480fe64e9a89`.

The original Step-2 text authority implemented one from-scratch bidirectional encoder-decoder Transformer with `<ABC_TO_EL>` and `<EL_TO_ABC>` direction controls, from-scratch byte BPE with complete byte fallback, atomic official emoji/EL symbols, deterministic bootstrap/rehearsal, frozen benchmark isolation, reproducible training, and fresh-process provider-free inference.

Historical Step-2 evidence included 1,788,672 trainable parameters, measured 4,536-token vocabulary with 320 BPE merges, broad loss 6.7869→4.1417, 8/8 trusted rehearsal probes, exact `rocket → 🚀` and `🚀 → rocket`, provider calls 0, Phase 2 PASS, Phase 3 PASS, and 44/44 diagnostics PASS. These are historical observations, not final multimodal runtime constants.

The 2026-08-19 Owner correction extends the same G1 model with native learned pixel vision before final Phase-6 release. G1 must now additionally pass deterministic held-out Image→EL and Image→ABC probes with protected text non-regression and zero provider/self-output positive truth.

### Step 3 — Teacher + Learning System ✅ PASS / MERGED

Step-3 merge commit: `2e40519e89ce0c8a412d5f0f47ad18fa7407ee09`.

Step 3 proved the teacher/learning/generation lifecycle: real Qwen/Ollama invocation through the existing connector; semantic-only teacher lessons; independently trusted EL targets; positive + negative provenance; frozen-benchmark exclusion; isolated G2 training; immutable generation registry; promotion/rejection/rollback; fresh provider-free selected-generation inference; and Phase/engine regressions.

The native-vision Owner correction extends generation promotion policy before release: G1 and G2 must carry native visual weights, selected G2 must pass held-out visual probes, and promotion must reject native-vision regression even if text metrics improve.

### Step 4 — Primary Runtime + Hidden Control Room ✅ PASS / MERGED

Step-4 merge commit on `main`: `e0ed1b2ac91ae1f9a716abfc0e93904469b91422`.

Step 4 proved selected verified G2 first for text translation, zero provider calls on successful selected-generation text inference, deterministic/support fallback, hidden five-click/three-second entry with zero discovery clue, local salted-scrypt Owner auth, exactly two rendered control-room pages, truthful runtime/model data, and 44/44 diagnostics.

The native-vision correction adds truthful native-vision fields to the existing two pages only; it does not add a third page or fake controls. Current Status and Training Center must expose native-vision availability, visual parameters, modality, image/patch geometry, visual validation/promotion metrics, and actual runtime-derived total parameters.

## Step 5 — Proof, Packaging & Release 🚀 AUTHORIZED / IN PROGRESS

Owner authorization date: **2026-08-18** local / **2026-08-19** UTC conversation time.

Step-5 authority began from exact merged Step-4 main SHA `e0ed1b2ac91ae1f9a716abfc0e93904469b91422`.

An initial Step-5 implementation PR was fully green and merged to intermediate main SHA `5737d9bfa8d77b7b0d0c92c7ef2b248bddec602b`. Its exact-main run `32221488194` rebuilt and passed through Step-5 static authority, then successfully produced Setup and Portable binaries but failed because `electron-builder` detected CI and attempted an unintended implicit GitHub publish requiring `GH_TOKEN`. That failure occurred before the controlled exact-main publisher and therefore produced **no Phase-6 v0.6.0 release**. It was a release-pipeline authority defect, not a Forgey training failure.

The durable repair explicitly disables electron-builder publishing with `--publish never`; `scripts/publish-step5-main-release.ps1` is the single release authority.

The same repair branch also incorporates the later Owner-native-vision correction before Phase-6 final release.

### Locked Step-5 delivery direction

Phase-6 Windows release version is **0.6.0** and must provide both x64 NSIS Setup and x64 Portable packages. The package must be self-contained for normal Forgey text and native image inference and therefore include:
- embedded Python 3.12.10 x64;
- embedded PyTorch 2.13.0 CPU runtime;
- verified multimodal G2 model/tokenizer as selected production generation;
- verified multimodal G1 model/tokenizer so authenticated rollback remains real;
- a relocatable generation registry whose artifact paths resolve relative to the application root while preserving exact model/tokenizer hashes, lineage, metrics, statuses and history;
- native vision inference/curriculum code required to load and execute packaged image inference;
- Step-4 status/admin helpers and architecture authority required by the two-page hidden control room;
- all existing 44 deterministic engines and normal runtime files.

Ollama/Qwen remains external and is not bundled. Known verified Forgey-primary text translation and native visual inference must work with `provider_calls=0`; unresolved teacher/fallback dependence must fail safely if the external provider is unavailable.

### Step-5 package proof direction

A builder exit code is not release proof. The candidate package must prove from `dist/win-unpacked/resources/app`, using packaged embedded Python/Torch and packaged model registry:
- G2 hashes verify and the model/tokenizer load;
- runtime-derived multimodal trainable parameter count remains inside 1–3M;
- native vision is enabled with nonzero learned visual parameters;
- `vehicle powered by pedals with two wheels → 🚲` releases through packaged G2;
- `🚲 → bicycle` releases through packaged G2;
- held-out actual PNG pixels execute Image→EL exactly through packaged G2;
- held-out actual PNG pixels execute Image→ABC exactly through packaged G2;
- successful packaged text and native visual inference uses zero provider calls;
- packaged diagnostics are 44/44;
- packaged Electron UI renders, retains Phase-5 polish, uses bundled Python, and truthfully shows native-vision state;
- Setup and Portable v0.6.0 both exist;
- Phase-5 real rendered 30-FPS/168-frame visual proof remains green.

### Exact-main release gate

Pull-request Step-5 CI may build/prove the complete package but must not publish a GitHub Release. After the verified Step-5 correction merge, the **new exact `main` SHA** must run the same multimodal package proof and then publish a GitHub Release tagged `el-bot-v0.6.0-<exact-main-short-sha>`, upload SHA-256 evidence including native Image→EL and Image→ABC proof, and re-read the release to verify exact tag/target/assets.

Phase 6 becomes PASS only after the final correction candidate is green, merged, the exact merged-main Step-5 workflow succeeds, and the exact-SHA Phase-6 release is independently re-read successfully.

## Current implementation gate

**Steps 1–4 remain PASS+MERGED. Step 5 remains Owner-authorized and IN PROGRESS until the release-delivery repair + native-vision correction pass all exact-head gates, merge, rerun on exact main, and publish/re-read the exact v0.6.0 release. No final Phase-6 PASS may be declared earlier.**
