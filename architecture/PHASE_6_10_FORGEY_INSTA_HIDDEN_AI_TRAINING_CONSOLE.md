# Phase 6.10 — Hidden Forgey Insta Control Room

**Status:** ✅ STEP 4 PASS / MERGED

**Canonical intelligence:** `Forgey Insta:EL-Bot`

This is the locked Step-4 control-room authority. The Owner authorized Step 4 on 2026-08-18 and explicitly refined the hidden console to exactly **two primary pages**. Step 4 passed its final exact-head evidence gate and was merged to `main` as `e0ed1b2ac91ae1f9a716abfc0e93904469b91422`.

## Hidden entry

The existing **🤖 at the far-left of EL Bot's header** is the sole concealed activation target.

- click the existing 🤖 **5 times within 3 seconds**;
- clicks 1–4 produce no visible response;
- the fifth valid click opens local Owner authentication;
- timeout, clicking another control, app focus loss, or abandoning the sequence resets silently;
- no counter, progress, tooltip, hover clue, glow, pointer cursor, pressed state, keyboard clue, nearby label, or ordinary navigation entry.

The gesture is camouflage only. Authentication is the security boundary.

## Authentication

- no Owner password is committed, hard-coded, shipped in plaintext, logged, or embedded in evidence;
- first use creates a local Owner credential for that installation;
- only a salted slow **scrypt** verifier is stored under Electron `userData`;
- no backdoor/recovery password and no remote admin endpoint;
- failed attempts are rate-limited;
- successful login creates a short-lived in-memory local session;
- app restart and session expiry invalidate access;
- credential rotation invalidates existing sessions;
- audit records contain action metadata only, never passwords or translation text.

Sensitive generation rollback requires both an active session and password re-entry plus the exact confirmation phrase `ROLLBACK <generation>`.

## Exactly two primary pages

### 1. 📊 Current Status

This page answers: **what is EL Bot / Forgey Insta doing right now?**

It shows real, currently observable data only:
- EL Bot app active time;
- Forgey model active time for the current app process once a neural generation has actually released a translation;
- translation count for the current app run;
- Forgey-primary release count and share;
- Qwen teacher/fallback usage count;
- latest inference metadata without storing the user's source/output text: direction, source length, latency, quality, selected generation, teacher usage;
- selected generation and verified artifact-hash state;
- neural runtime readiness;
- Step-1/Step-2/Step-3 authority status;
- current 44-engine diagnostics when measurable;
- Qwen teacher evidence and dependency counts;
- authentication session remaining time;
- credential rotation control.

If a value cannot be observed, the page says **Unavailable**. It never invents uptime, activity, counts, confidence, status, or errors.

### 2. 🏋️ Training Center

This page answers: **what exactly is the current AI, what evidence produced it, and how is it performing?**

It shows, from the actual selected registry/checkpoint/tokenizer/evidence when available:
- selected generation;
- actual model checkpoint file size;
- actual tokenizer file size;
- runtime-derived trainable and total parameter counts;
- tokenizer vocabulary size;
- architecture family;
- model width;
- attention heads;
- encoder/decoder layers;
- feed-forward width;
- context length;
- pretrained-semantic-weight status;
- model and tokenizer hashes;
- generation lineage and statuses;
- teacher exactness and token loss;
- frozen benchmark loss;
- protected probes;
- round-trip metrics;
- adversarial-integrity and deterministic-validation state;
- teacher calls, admitted lessons, rejected/negative evidence;
- learning claim and negative-episode counts;
- replay example count and replay fingerprint;
- promotion and rollback history;
- raw measured training/promotion evidence for inspection.

The Training Center includes a real **Validate Current Generation** control and authenticated rollback for previously verified generations. A generic post-G2 continual trainer is not fabricated: until such a trainer exists, the UI explicitly reports that training-next-generation is unavailable instead of showing a fake Start button.

## Runtime contract

Step 4 changed normal translation routing to:

```text
ABC / EL input
  ↓
🧠 registry-selected Forgey Insta generation — PRIMARY ATTEMPT
  ↓
deterministic structural / canonical / round-trip support + validation
  ├─ PASS → release Forgey result with provider_calls=0
  └─ reject / unavailable
       ↓
existing deterministic/support path
       ↓
if still unresolved → ✦ orchestration → 🔌 connector → 🦙 Qwen semantic teacher/fallback evidence
       ↓
deterministic EL construction + validation only
```

The old deterministic translator remains intact as historical/support authority. Step 4 uses a runtime facade rather than rewriting Step-3-proven translation code.

## No-fake-data rule

No fake model size, parameter count, training progress, active time, confidence, status, teacher usage, generation, chart, benchmark, or audit event is allowed. Missing or unmeasurable data must remain missing and be labeled accordingly.

## Verified closeout

Final Step-4 branch head `b8ca651a64e4c4c6e9817d3dcadec5dbbb638c8b` passed exact-head Step 1, Step 2, Step 3 and Step 4 workflows, including Forgey-primary routing, provider-free selected-generation inference, truthful Status data, salted-scrypt authentication, rendered two-page Electron control-room proof, Phase 2, Phase 3, and 44/44 diagnostics. It was merged to `main` as `e0ed1b2ac91ae1f9a716abfc0e93904469b91422`.

Step 5 now packages and proves this merged control-room/runtime authority. Step 5 must not weaken the two-page contract, fabricate unavailable training controls, or publish a release before its exact-main release gate.
