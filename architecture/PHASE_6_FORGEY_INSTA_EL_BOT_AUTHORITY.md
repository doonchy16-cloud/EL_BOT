# EL Bot — Phase 6 Canonical Authority

## Forgey Insta:EL-Bot

**Status:** 🔒 LOCKED PLAN — STEP 1 IMPLEMENTATION AUTHORIZED

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

The locked G0 design direction is a small bidirectional encoder-decoder Transformer using direction tokens for ABC→EL and EL→ABC, approximately 128-dimensional embeddings, 4 attention heads, 3 encoder layers, 3 decoder layers, a roughly 384–512 feed-forward width, and an initial context target around 128 tokens. The exact derived parameter count is recorded from the implemented architecture rather than hard-coded.

## Knowledge foundation — Step 1

Step 1 is the **only implementation currently authorized**.

It establishes:
- released official Unicode Emoji data as the emoji inventory/name/sequence authority;
- a dataset-derived emoji count, with no fixed historical product ceiling;
- Open English WordNet 2025+ as a broad released English lexical/sense/morphology/taxonomy foundation;
- provider-free lexical retrieval under existing 📚 Vocabulary ownership;
- future tokenizer source authority: every official emoji atomic, EL structural/control tokens atomic, English corpus available for later from-scratch byte-level BPE training;
- the historical semantic symbol set retained only as backward-compatible meanings/order for old engines, never as the public vocabulary or emoji count;
- truthful product-facing knowledge status.

Step 1 must not implement the neural model, Qwen teaching/training loop, Forgey-first runtime routing, hidden admin runtime, packaging, or Phase-6 release.

## Learning authority for later Steps 2–3

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

1. 📚 **Knowledge Foundation** — CURRENTLY AUTHORIZED.
2. 🧠 **Forgey Insta G0/G1** — model, tokenizer, initial curriculum, local inference. PAUSED.
3. 🦙 **Teacher + Learning System** — validated Qwen lessons, training evidence, generations/promotion. PAUSED.
4. ⚡ **Primary Runtime + Hidden Console Integration** — Forgey-first semantic routing and protected admin console. PAUSED.
5. 🧪 **Proof, Packaging & Release** — full regression, package smoke, exact-final-SHA CI/release. PAUSED.

## Phase-6 final acceptance direction

Phase 6 cannot be marked PASS merely because a model exists. Final evidence must prove the primary AI path, from-scratch model, dynamic emoji authority, broad offline lexical foundation, safe teacher boundary, controlled learning/promotion/rollback, improved translation reliability, protected Phase 1–5 regressions, 44/44 diagnostics, Windows package behavior, and one exact-final-main-SHA green release gate.

## Current implementation gate

**Only Step 1 is authorized. Steps 2–5 remain implementation-paused until separately approved by the owner.**
