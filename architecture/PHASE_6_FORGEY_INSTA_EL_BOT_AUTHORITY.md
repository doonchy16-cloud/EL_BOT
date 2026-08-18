# EL Bot — Phase 6 Canonical Authority

## Forgey Insta:EL-Bot

**Status:** 🔒 LOCKED PLAN — STEP 1 PASS / STEP 2 PASS / STEP 3 PAUSED

**Canonical intelligence name:** `Forgey Insta:EL-Bot`

This file is the canonical Phase-6 planning authority. Where an older Phase-6 draft conflicts with this file, this file wins.

## Mission

`Forgey Insta:EL-Bot` will become EL Bot's primary semantic/conversion intelligence for both ABC→EL and EL→ABC. It is a small, from-scratch, EL-specialized neural model intended to perform most conversions locally, improve from validated evidence, and progressively reduce dependence on the temporary `qwen2.5vl:7b` teacher.

The existing 44-engine architecture remains intact around Forgey Insta as knowledge, validation, orchestration, evidence, learning, reliability, security, versioning, and recovery infrastructure. Phase 6 does not add engine #45.

## Locked runtime direction for later Step 4

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

Permanent direction:
- Forgey Insta is the normal primary semantic translator once Step 4 is implemented.
- Qwen is a teacher for genuinely difficult, novel, or unresolved semantic cases, not the normal translator.
- Qwen cannot directly release EL, bypass validation, write raw provider prose into canonical truth, or directly control production weights.
- non-semantic runtime/parser/security/auth/recovery/UI/animation failures are not teacher-learning opportunities.

## Locked model direction

The first production generations target approximately **1–3 million trainable parameters**, with translation quality and measured performance more important than an exact marketing number.

From scratch means:
- random initial weights;
- no copied Qwen weights;
- no pretrained GPT/BERT/other semantic model weights;
- specialized specifically for EL conversion;
- local/offline inference once trained;
- versioned, benchmarked, and rollbackable generations.

The Step-2 G0 implementation is a bidirectional encoder-decoder Transformer using direction tokens for ABC→EL and EL→ABC: 128-dimensional width, 4 attention heads, 3 encoder layers, 3 decoder layers, 384 feed-forward width, and 128-token context. The parameter count is derived from the actual tensor graph.

## Knowledge foundation — Step 1 ✅ PASS / MERGED

Step 1 is merged into `main` and established:
- released official Unicode Emoji data as the emoji inventory/name/sequence authority;
- a dataset-derived emoji count, with no fixed historical product ceiling;
- Open English WordNet 2025+ as a broad released English lexical/sense/morphology/taxonomy foundation;
- provider-free lexical retrieval under existing 📚 Vocabulary ownership;
- tokenizer source authority: every official emoji atomic, EL structural/control tokens atomic, broad English corpus available for from-scratch byte-level BPE;
- the historical semantic symbol set retained only as backward-compatible meanings/order for old engines, never as the public vocabulary or emoji count;
- truthful product-facing knowledge status.

Step 1 merge commit: `902a79fec235f77c1bf3b4c7edf82b9a0127b900`.

## Forgey Insta G0/G1 — Step 2 ✅ PASS

Step 2 implemented and verified:
- the locked G0 encoder-decoder Transformer architecture from random initialization;
- one shared bidirectional model controlled by `<ABC_TO_EL>` and `<EL_TO_ABC>`;
- from-scratch byte-level BPE for English using Step-1 tokenizer-source authority;
- atomic official emoji/EL structural tokens with no Unicode-codepoint splitting;
- measured tokenizer vocabulary selection rather than a magic size;
- trusted bootstrap curriculum with no Qwen/provider-generated training truth;
- frozen held-out benchmark excluded from broad training and trusted rehearsal;
- reproducibly trained G1 candidate;
- trusted non-benchmark deterministic rehearsal plus broad replay;
- local checkpoint reload and fresh-process inference in both directions;
- real derived parameter count inside the locked approximately 1–3 million target;
- Step-1/Phase-2/Phase-3/44-engine compatibility.

Candidate Windows evidence on branch head `23358db464fdc2ce3cd6a7f1be45a3bd0b769eef`:
- Step-2 run #5 / ID `32164249835`: SUCCESS;
- Step-1 regression run #21 / ID `32164249818`: SUCCESS;
- real trainable parameters: 1,788,672;
- measured tokenizer vocabulary: 4,536 IDs with 320 BPE merges;
- broad training loss: 6.7869 → 4.1417;
- frozen benchmark: G0 8.4877 → final G1 4.8358;
- trusted rehearsal: 3.2511 → 2.3778;
- trusted rehearsal probes: 8/8 exact;
- fresh-process `rocket → 🚀`: exact;
- fresh-process `🚀 → rocket`: exact;
- provider calls: 0;
- Phase 2: PASS;
- Phase 3: PASS;
- diagnostics: 44/44 PASS.

These measurements are evidence, not runtime constants. The model/tokenizer derive their actual dimensions from source authority and the implemented graph.

Step 2 still does **not** implement teacher/Qwen lesson ingestion, generation promotion/rollback policy, Forgey-first production routing, hidden admin runtime, packaging, or Phase-6 release publishing.

## Learning authority for later Step 3

Forgey Insta is intended to keep learning when useful evidence appears, but production weights must never mutate blindly after every prediction.

```text
validated evidence
  ↓
📜 provenance + 📊 trust
  ↓
training/replay dataset
  ↓
train candidate generation
  ↓
🧪 benchmark + 🪤 adversarial + 🔁 round-trip + 🧾 validation
  ↓
measurably better with no protected regression?
  ├─ YES → promote
  └─ NO  → reject and retain current production
```

Unverified self-predictions and rejected teacher outputs cannot become positive training truth. Previous passing generations remain available for rollback.

## Five-step Phase-6 implementation plan

1. 📚 **Knowledge Foundation** — ✅ PASS / MERGED.
2. 🧠 **Forgey Insta G0/G1** — ✅ PASS ON VERIFIED BRANCH; model, tokenizer, trusted bootstrap/rehearsal, local inference proven.
3. 🦙 **Teacher + Learning System** — validated Qwen lessons, training evidence, generations/promotion. **PAUSED**.
4. ⚡ **Primary Runtime + Hidden Console Integration** — Forgey-first semantic routing and protected admin console. **PAUSED**.
5. 🧪 **Proof, Packaging & Release** — full regression, package smoke, exact-final-SHA CI/release. **PAUSED**.

## Phase-6 final acceptance direction

Phase 6 cannot be marked PASS merely because a model exists. Final evidence must prove the primary AI path, from-scratch model, dynamic emoji authority, broad offline lexical foundation, safe teacher boundary, controlled learning/promotion/rollback, improved translation reliability, protected Phase 1–5 regressions, 44/44 diagnostics, Windows package behavior, and one exact-final-main-SHA green release gate.

## Current implementation gate

**Step 2 is PASS. Steps 3–5 remain implementation-paused until separately approved by the owner.**
