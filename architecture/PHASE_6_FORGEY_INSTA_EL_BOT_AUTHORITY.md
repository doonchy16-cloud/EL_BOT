# EL Bot — Phase 6 Canonical Authority

## Forgey Insta:EL-Bot

**Status:** 🔒 LOCKED PLAN — STEP 1 PASS+MERGED / STEP 2 PASS+MERGED / STEP 3 PASS / STEP 4 PAUSED / STEP 5 PAUSED

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

The implemented Forgey Insta model family is one bidirectional encoder-decoder Transformer with `<ABC_TO_EL>` and `<EL_TO_ABC>` direction controls, 128 model width, 4 attention heads, 3 encoder layers, 3 decoder layers, 384 feed-forward width, 128-token context, shared/tied vocabulary weights, random initialization, and no pretrained semantic weights. The trainable parameter count is derived from the actual tensor graph and must remain inside the owner-locked approximately 1–3 million target unless a later separately approved architecture change says otherwise.

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

## Step 3 — Teacher + Learning System ✅ PASS

Step 3 is implemented on its verified branch and remains unmerged until owner approval.

### Teacher lesson boundary

A teacher lesson is requested only through the existing provider-neutral `🔌` boundary. The temporary provider is Ollama `qwen2.5vl:7b`.

Qwen supplies **semantic evidence only**. It does not supply authoritative EL output. Provider output is reduced to a strict bounded structured lesson before admission. Positive training truth requires an EL target independently anchored by trusted Step-1/Step-2 authority; rejected provider output becomes negative evidence only.

The verified teacher admission path proves:
1. actual provider invocation and provider/model identity evidence;
2. exact bounded lesson schema;
3. semantic definition without provider-authored EL;
4. frozen Step-2 benchmark exclusion;
5. independent trusted EL target authority;
6. provenance/trust persistence;
7. deterministic admission/rejection;
8. rejected provider output and unverified self-output never become positive neural truth.

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
  ├─ YES → promote generation pointer
  └─ NO  → reject candidate; keep production generation
```

Production weights never mutate in place. Every generation carries immutable lineage and artifact evidence. Previous verified generations remain rollback targets, and rollback changes the selected pointer to an already-verified exact-hash artifact rather than retraining or rewriting old weights.

### Verified candidate evidence

Candidate head: `35e85a898f0c2e5359f905342498f6fa06616bd4`.

Exact candidate workflows on that SHA:
- Step-1 regression run #40 / ID `32182064506`: SUCCESS;
- Step-2 regression run #24 / ID `32182064458`: SUCCESS;
- Step-3 teacher/learning run #15 / ID `32182064476`: SUCCESS.

Observed Step-3 run #15 evidence:
- Qwen teacher: Ollama `qwen2.5vl:7b`, reachable and present;
- teacher calls: 5;
- deterministically admitted lessons: 3;
- rejected/negative lessons: 2;
- provider-authored EL positive truth: 0;
- unverified self-output positive truth: 0;
- frozen benchmark training overlap: 0;
- G1→G2 teacher exactness: 0/3 → 3/3;
- G1→G2 teacher token loss: 4.4057 → 0.0990;
- frozen benchmark: 4.8178 → 4.5608;
- protected Step-2 probes: 8/8;
- admitted teacher round-trip: 3/3;
- protected reverse teacher replay: 3/3;
- real measured promotion: G1 → G2;
- rejection-policy fixture: deterministic validation failure correctly rejected without moving the production pointer;
- rollback: G2 → G1 → G2 with exact artifact-hash verification;
- selected-generation fresh-process `vehicle powered by pedals with two wheels → 🚲`: exact;
- selected-generation fresh-process `🚲 → bicycle`: exact;
- Phase 2: PASS;
- Phase 3: PASS;
- diagnostics: 44/44 PASS;
- Step 4: ABSENT;
- Step 5: ABSENT.

These numbers are historical evidence, not runtime constants. The generation registry and promotion policy operate on the actual measured artifacts, hashes, replay fingerprints, and metrics produced by each run.

### Explicitly NOT Step 3

Step 3 does not implement:
- Forgey-Insta-first user translation routing;
- hidden/admin console runtime;
- normal user-facing teacher invocation;
- packaging, installer, updater, or Phase-6 release publishing.

Those remain Steps 4–5.

## Five-step Phase-6 plan

1. 📚 **Knowledge Foundation** — ✅ PASS / MERGED.
2. 🧠 **Forgey Insta G0/G1** — ✅ PASS / MERGED.
3. 🦙 **Teacher + Learning System** — ✅ **PASS ON VERIFIED BRANCH; awaiting owner merge approval**.
4. ⚡ **Primary Runtime + Hidden Console Integration** — **PAUSED**.
5. 🧪 **Proof, Packaging & Release** — **PAUSED**.

## Phase-6 final acceptance direction

Phase 6 cannot be marked PASS merely because a model exists. Final evidence must prove the primary Forgey-Insta path, from-scratch model, dynamic emoji authority, broad offline lexical foundation, safe teacher boundary, controlled learning/promotion/rollback, improved translation reliability, protected Phase 1–5 regressions, 44/44 diagnostics, Windows package behavior, and one exact-final-main-SHA green release gate.

## Current implementation gate

**Step 3 is PASS on its verified branch. Step 4 remains implementation-paused until separately approved by the owner.**
