# EL Bot — Phase 6 Canonical Authority

## Forgey Insta:EL-Bot

**Status:** 🔒 LOCKED PLAN — STEP 1 PASS / STEP 2 PASS+MERGED / STEP 3 IMPLEMENTATION AUTHORIZED / STEPS 4–5 PAUSED

**Canonical intelligence name:** `Forgey Insta:EL-Bot`

This file is the canonical Phase-6 authority. Where an older Phase-6 draft conflicts with this file, this file wins.

## Mission

`Forgey Insta:EL-Bot` becomes EL Bot's primary semantic/conversion intelligence for ABC→EL and EL→ABC after the later Step-4 routing gate. It is a small, from-scratch, EL-specialized neural model intended to perform most conversions locally, improve from validated evidence, and progressively reduce dependence on the temporary `qwen2.5vl:7b` teacher.

The existing 44-engine architecture remains intact. Phase 6 does not add engine #45.

## Permanent runtime direction for later Step 4

```text
ABC / EL input
      ↓
basic parser / integrity / security boundaries
      ↓
🧠 Forgey Insta:EL-Bot
      ↓
local candidate(s) + confidence + semantic state
      ↓
📚📖🧭🗺️ deterministic knowledge/support
      ↓
🧾 deterministic validation + round-trip checks
   ┌──────────────┴──────────────┐
 PASS                         uncertain / fail
   │                                │
   ▼                                ▼
release                    supporting engines resolve?
                                │             │
                               YES            NO
                                │             │
                                ▼             ▼
                             validate    ✦ Orchestration
                                             ↓
                                         🔌 Connector
                                             ↓
                                      🦙 qwen2.5vl:7b
                                          TEACHER
                                             ↓
                                      semantic lesson only
                                             ↓
                                   Forgey Insta + EL construction
                                             ↓
                                        🧾 validate
```

Permanent boundaries:
- Forgey Insta is the normal primary semantic translator only after Step 4 is implemented.
- Qwen is a teacher for difficult, novel, or unresolved semantic cases, not the normal translator.
- Qwen cannot directly release EL, bypass deterministic validation, write raw provider prose into canonical truth, or directly mutate production weights.
- non-semantic parser/security/auth/recovery/UI/animation failures are not teacher-learning opportunities.

## Model authority

The implemented G0/G1 model is one bidirectional encoder-decoder Transformer with `<ABC_TO_EL>` and `<EL_TO_ABC>` direction controls, 128 model width, 4 attention heads, 3 encoder layers, 3 decoder layers, 384 feed-forward width, 128-token context, shared/tied vocabulary weights, random initialization, and no pretrained semantic weights. The trainable parameter count is derived from the actual tensor graph and must remain inside the owner-locked approximately 1–3 million target unless a later separately approved architecture change says otherwise.

## Step 1 — Knowledge Foundation ✅ PASS / MERGED

Step 1 established released Unicode Emoji authority, Open English WordNet 2025+ lexical/sense/morphology/taxonomy data, provider-free lexical retrieval, atomic official emoji/EL tokenizer-source authority, historical-seed compatibility without a public 501 ceiling, and truthful product-facing knowledge status.

Step-1 merge commit: `902a79fec235f77c1bf3b4c7edf82b9a0127b900`.

## Step 2 — Forgey Insta G0/G1 ✅ PASS / MERGED

Step 2 implemented and verified:
- one from-scratch bidirectional encoder-decoder Transformer;
- from-scratch byte-level BPE with complete byte fallback;
- atomic official emoji/EL symbols;
- measured tokenizer vocabulary selection;
- trusted deterministic bootstrap + rehearsal only;
- frozen benchmark excluded from training/replay;
- reproducible G1 training;
- fresh-process local inference in both directions;
- Step-1/Phase-2/Phase-3/44-engine compatibility.

Exact verified Step-2 head before merge: `3f5264d07a74ed254299cb066ed585dbfcdc978a`.
Step-2 merge commit: `cc49045e8933d43aae285add3ade480fe64e9a89`.

Observed Step-2 evidence included 1,788,672 trainable parameters, measured 4,536-token model vocabulary with 320 BPE merges, broad training loss 6.7869→4.1417, final frozen-benchmark loss materially below G0, 8/8 trusted rehearsal probes, exact fresh-process `rocket → 🚀` and `🚀 → rocket`, provider calls 0, Phase 2 PASS, Phase 3 PASS, and 44/44 diagnostics PASS. These are evidence, not runtime constants.

## Step 3 — Teacher + Learning System 🔥 AUTHORIZED

Step 3 is the **only implementation currently authorized**.

### Teacher lesson boundary

A teacher lesson may be requested only through the existing provider-neutral connector boundary. The temporary provider is Ollama `qwen2.5vl:7b`.

Qwen may supply **semantic evidence only**. It may not supply authoritative EL output. Raw provider prose must be reduced to a strict structured lesson before it crosses the connector boundary.

A provider lesson is eligible for positive training truth only after deterministic admission proves:
1. the provider was actually called and the provider/model identity is recorded;
2. the lesson schema is exact and bounded;
3. the semantic definition contains no EL/emoji output;
4. the source case is not from the frozen Step-2 benchmark;
5. the deterministic target is independently derived/declared by trusted Step-1/Step-2 authority, never copied from provider prose;
6. provenance and trust evidence are persisted;
7. deterministic validation accepts the target/relationship;
8. no rejected provider lesson or unverified self-output is admitted as positive truth.

Rejected provider output becomes negative evidence only.

### Generation lifecycle

```text
validated teacher/deterministic evidence
  ↓
📜 provenance + 📊 trust
  ↓
versioned replay dataset
  ↓
train isolated candidate generation
  ↓
🧪 frozen benchmark
+ 🪤 protected/adversarial checks
+ 🔁 round-trip checks
+ 🧾 deterministic validation
  ↓
measurably better AND no protected regression?
  ├─ YES → promotion decision may advance production generation pointer
  └─ NO  → reject candidate; keep current production generation
```

Production weights never mutate in place. Every candidate has an immutable generation ID, parent generation, model hash, tokenizer hash, lesson/replay fingerprint, metrics, and decision evidence.

Previous passing generations remain available for rollback. Rollback changes the generation pointer to an already-verified prior artifact; it does not retrain or rewrite old weights.

### Step-3 required proof

Step 3 must implement and prove:
- teacher lesson coordinator under existing Instructor ownership, not engine #45;
- actual Qwen/Ollama teacher invocation through `🔌` with provider identity/evidence;
- strict semantic-only lesson parsing and deterministic admission/rejection;
- positive/negative evidence persistence through existing provenance/trust learning infrastructure;
- versioned replay dataset with frozen-benchmark exclusion and no self-output truth;
- isolated G2 candidate training from G1 + admitted evidence + protected replay;
- immutable generation registry with hashes and parent linkage;
- deterministic promotion policy requiring measurable improvement and protected non-regression;
- deterministic rejection path that leaves production untouched;
- rollback proof restoring a prior verified generation pointer/hash;
- fresh-process local inference from the selected generation;
- Step-1 + Step-2 + Phase-2 + Phase-3 + 44/44 regression gates.

### Explicitly NOT Step 3

Step 3 must not implement:
- Forgey-Insta-first production translation routing;
- hidden/admin console runtime;
- normal user-facing teacher invocation;
- packaging, installer, updater, or Phase-6 release publishing.

Those remain Steps 4–5.

## Five-step Phase-6 plan

1. 📚 **Knowledge Foundation** — ✅ PASS / MERGED.
2. 🧠 **Forgey Insta G0/G1** — ✅ PASS / MERGED.
3. 🦙 **Teacher + Learning System** — 🔥 **CURRENTLY AUTHORIZED**.
4. ⚡ **Primary Runtime + Hidden Console Integration** — **PAUSED**.
5. 🧪 **Proof, Packaging & Release** — **PAUSED**.

## Phase-6 final acceptance direction

Phase 6 cannot be marked PASS merely because a model exists. Final evidence must prove the primary Forgey-Insta path, from-scratch model, dynamic emoji authority, broad offline lexical foundation, safe teacher boundary, controlled learning/promotion/rollback, improved translation reliability, protected Phase 1–5 regressions, 44/44 diagnostics, Windows package behavior, and one exact-final-main-SHA green release gate.

## Current implementation gate

**Step 3 only is authorized. Steps 4–5 remain implementation-paused until separately approved by the owner.**
