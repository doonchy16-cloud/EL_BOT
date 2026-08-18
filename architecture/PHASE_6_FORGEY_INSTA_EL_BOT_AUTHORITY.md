# EL Bot — Phase 6 Canonical Authority

## Forgey Insta:EL-Bot

**Status:** 🔒 LOCKED PLAN — IMPLEMENTATION PAUSED

**Canonical intelligence name:** `Forgey Insta:EL-Bot`

This document is the canonical Phase-6 planning authority. Where an older Phase-6 draft conflicts with this file, this file wins.

## Mission

Build `Forgey Insta:EL-Bot` as the primary conversion intelligence and main semantic component of EL Bot. It is a from-scratch, EL-specialized neural model intended to perform the majority of ABC↔EL conversions locally, improve continuously from validated evidence, and progressively reduce dependence on the temporary `qwen2.5vl:7b` teacher.

The existing 44-engine architecture is retained as the surrounding language, validation, orchestration, evidence, learning, reliability, versioning, and recovery system. Phase 6 does not add engine #45.

## Primary runtime authority

Normal conversion routing is superseded from the old deterministic-first translator rule.

```text
ABC / EL input
      ↓
🧠 Forgey Insta:EL-Bot
      ↓
local candidate(s) + confidence + semantic state
      ↓
existing deterministic EL knowledge / lexical / graph support
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
                                   Forgey Insta:EL-Bot +
                                   deterministic EL construction
                                             ↓
                                        🧾 validate
```

### Permanent routing rules

1. `Forgey Insta:EL-Bot` is the normal primary translator for both ABC→EL and EL→ABC.
2. The deterministic engines remain authoritative validators and structured knowledge/support systems; they do not need to perform most conversions themselves.
3. Qwen is a teacher for genuinely difficult, novel, or unresolved semantic cases—not the normal translator.
4. Qwen may provide semantic meaning/evidence but may not directly release EL, write arbitrary provider prose into canonical knowledge, bypass validation, or directly control production model weights.
5. Runtime/parser/security/auth/recovery/UI/animation failures are not semantic-learning opportunities and must never invoke Qwen merely because they are HOLD/FAIL.
6. Semantic uncertainty may invoke the teacher when the local model/supporting engines cannot resolve the case safely.

## Forgey Insta:EL-Bot model direction

The first production generation should be a small from-scratch neural model, initially targeting approximately **1–3 million trainable parameters**. Parameter count is a design range, not a permanent magic number; translation quality, calibration, speed, memory use, and learning stability decide whether later generations stay small or scale upward.

`From scratch` means:

- random initial trainable weights;
- no copied Qwen weights;
- no pretrained GPT/BERT/other language-model weights;
- no pretrained semantic student checkpoint downloaded from elsewhere;
- specialized specifically for EL conversion;
- local/offline inference once trained;
- versioned and rollbackable model generations.

The exact G0 neural architecture, tokenizer/features, parameter count, optimizer, training schedule, and model file format are implementation decisions that must be separately designed and verified before coding resumes. This authority intentionally does not freeze an untested one-hidden-layer or exact-1,000,000-parameter architecture.

## Knowledge foundation

The previously planned lexical work remains part of Phase 6, but it supports the AI rather than replacing it.

Training/support knowledge may include:

- official Unicode Emoji data and names;
- the actual dataset-derived RGI emoji inventory (no fixed `501` product ceiling and no permanent hard-coded emoji count);
- Open English WordNet lexical entries, senses, synonyms, morphology, and taxonomy;
- existing verified EL mappings and deterministic PASS examples;
- validated Qwen semantic lessons;
- explicit user corrections/selections after validation;
- accepted historical learning evidence and provenance.

The historical semantic seed may remain internally where old engines depend on stable symbol meanings/order, but its size is not the public EL vocabulary size and not the emoji-universe count.

## Learning authority

`Forgey Insta:EL-Bot` is always learning **when useful evidence appears**, but production weights do not mutate blindly after every output.

```text
new validated evidence
      ↓
📜 provenance + 📊 trust level
      ↓
training/replay dataset
      ↓
train candidate generation
      ↓
🧪 benchmark + 🪤 adversarial + 🔁 round-trip + 🧾 validation
      ↓
candidate measurably better and no protected regression?
      ├─ YES → promote new version
      └─ NO  → reject / keep current production model
```

### Training evidence hierarchy

Highest-value evidence includes:

- explicit user correction/selection that survives deterministic validation;
- deterministic verified EL truth;
- Qwen semantic lesson that survives deterministic validation and provenance requirements;
- verified model outcomes that are retained as evidence only under controlled anti-feedback rules.

Rejected teacher output receives negative evidence and **must not become positive training truth**.

The model must not train directly on its own unverified predictions. This prevents self-reinforcing semantic drift.

## Model generations and rollback

Use explicit generations such as:

`Forgey Insta:EL-Bot G0 → G1 → G2 → ...`

Each candidate generation records at minimum:

- model/generation ID;
- parameter count;
- architecture/tokenizer signature;
- training dataset hash/version;
- trusted-example counts by source;
- training/validation metrics;
- easy-word reliability;
- context/sense accuracy;
- ambiguity handling accuracy;
- round-trip accuracy;
- nonsense/unknown rejection rate;
- semantic-loss metrics;
- Qwen teacher dependency rate;
- previous production generation;
- promotion or rejection evidence.

Previous passing models remain available for rollback.

## Success direction

The desired long-term trend is:

```text
Forgey Insta:EL-Bot conversion share  ↑
local validated accuracy              ↑
coverage/generalization               ↑
Qwen teacher dependency               ↓
semantic loss                         ↓
regressions                           → 0 protected
```

Qwen dependency approaching exceptional-case use is a goal to measure, not a result to assume.

## Existing 44-engine roles

The 44-engine architecture remains intact. Relevant engines support `Forgey Insta:EL-Bot` as follows:

- 🧠 Intelligence — primary model/runtime intelligence ownership;
- 📚 Vocabulary / lexical foundation — symbol and lexical authority;
- 🧭 Context & Sense — contextual evidence;
- 🧩 Decomposition — structural/morphological support;
- 🗺️ Semantic Graph — taxonomy/relationships;
- 🧱 Composition — EL construction support;
- 🏆 Competition — candidate ranking/evidence;
- 🧾 Validation — release authority;
- 📊 Evidence + 📜 Provenance — learning trust;
- 🎓 Graduation + ♻️ Revalidation — knowledge/model maturity;
- 📈 Analytics — improvement/dependency metrics;
- 🗃️ Versioning — dataset/model rollback;
- 🧑‍🏫 Instructor — curriculum, lessons, replay, training coordination;
- ✦ Orchestration + 🔌 Connector — teacher eligibility and provider isolation;
- 🛡️ Reliability / 🧯 Recovery / 🔐 Security — protect runtime and learning state.

## Phase-6 acceptance direction

Phase 6 cannot be marked PASS merely because a neural model exists. The final implementation must prove, on one exact final `main` SHA:

1. `Forgey Insta:EL-Bot` is actually the primary normal conversion path.
2. The model is genuinely from-scratch and EL-specialized.
3. The model performs real local neural inference and real trainable updates in the controlled training pipeline.
4. The exact model architecture/parameter count is derived and recorded rather than hidden behind a marketing number.
5. Unicode emoji authority reports the actual dataset-derived inventory, not `501` or another magic constant.
6. Broad lexical resources are available offline in the packaged app.
7. Easy/common language reliability is materially improved and measured.
8. Ambiguous language is resolved by context when justified or represented as uncertainty/HOLD rather than random certainty.
9. Nonsense/unknown inputs do not acquire fabricated meanings.
10. Most validated routine conversions can be handled locally by `Forgey Insta:EL-Bot` without Qwen.
11. Difficult/novel semantic cases can invoke Qwen as teacher through ✦/🔌 only.
12. Qwen output cannot bypass deterministic EL validation or directly become canonical truth.
13. Learning evidence can accumulate continuously, but production-model promotion is gated and rollbackable.
14. Rejected teacher lessons and unverified model guesses cannot train as positive truth.
15. Old model generations remain recoverable.
16. All protected Phase 1–5 behavior and 44/44 diagnostics remain green unless explicitly superseded by this authority.
17. Windows Setup + Portable package the required local model/runtime/data resources and work offline for local inference.
18. Packaged-runtime smoke proves the primary model is actually selected and usable.
19. Exact-final-SHA CI passes the full regression, learning, model, package, and release gates.
20. Phase-6 authority is updated to PASS only after that evidence exists.

## Supersession

This authority supersedes conflicting Phase-6 statements that:

- make deterministic translation the mandatory first/primary translator for every normal conversion;
- restrict the student model to only HOLD/FAIL cases;
- require immediate production-weight backprop after each accepted lesson;
- freeze the student to one exact million-parameter architecture before model-design evidence exists;
- treat the historical 501-symbol seed as the EL/emoji vocabulary ceiling.

Those older ideas may remain useful historical planning context only where they do not conflict with this file.

## Implementation gate

**Implementation is paused.** Locking this document authorizes the architecture, name, and planning direction only. Source/model/training/runtime/package changes require a separate explicit implementation GO after the exact G0 model/training proposal is reviewed.
