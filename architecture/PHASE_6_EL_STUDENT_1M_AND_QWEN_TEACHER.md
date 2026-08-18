# EL Bot — Phase 6 EL Student 1M + Qwen Teacher Distillation

**Status:** 🟡 IMPLEMENTATION IN PROGRESS

Phase 6 changes EL Bot from a mostly hand-authored semantic system with an emergency AI fallback into a **specialist student/teacher learning system** dedicated to Emoji Language conversion.

It does **not** add engine #45. The trainable student lives under existing **🧠 Intelligence**, while lesson intake/replay/training lives under existing **🧑‍🏫 Instructor**.

## Owner direction

The goal is not to keep writing a larger and larger list of hand-coded word rules. The goal is to build a small EL-specific AI from scratch that continuously learns from `qwen2.5vl:7b` and from deterministic/user-validated truth.

The deterministic system remains valuable as:

- the fast path for obvious/easy language;
- the EL syntax and grammar authority;
- the release validator;
- the source of safe bootstrap examples;
- the safety boundary that prevents teacher/student hallucinations from becoming EL truth.

## Runtime architecture

```text
ABC input
   ↓
fast deterministic + lexical front end
   ├─ PASS
   │    → release immediately
   │    → provider calls = 0
   │    → low-weight supervised lesson for EL Student
   │
   └─ semantic HOLD / semantic FAIL
        ↓
     🧠 EL Student 1M prediction
        ↓
     repeated teacher-confirmed + high-confidence + deterministic revalidation?
        ├─ YES → provider-free student release
        └─ NO
             ↓
          ✦ Orchestration
             ↓
          🔌 Connector
             ↓
          🦙 qwen2.5vl:7b TEACHER
             ↓
          plain-English semantic lesson
             ↓
          deterministic EL construction + reverse/round-trip validation
             ├─ REJECT → negative evidence; student does NOT train
             └─ ACCEPT
                  → release validated EL
                  → 📜/📊 learning evidence
                  → 🧑‍🏫 lesson replay
                  → immediate EL Student backprop update
                  → persistent model snapshot
```

A **system/runtime/security/parser HOLD** is not semantic uncertainty and must never call the student teacher/provider path.

## Student model

At Unicode Emoji 17.0, the runtime emoji authority contains **3,953** official emoji rows. The student architecture is:

```text
256 deterministic hashed text features
        ↓
256 trainable tanh hidden units
        ↓
3,953 trainable emoji logits
```

Trainable parameters at that dataset size:

```text
256 × 256       input → hidden weights
+ 256           hidden biases
+ 256 × 3,953   hidden → emoji weights
+ 3,953         emoji biases
= 1,081,713 trainable parameters
```

The output dimension is derived from the current official Unicode emoji inventory, so the parameter count may change when Unicode changes. The implementation must not hard-code `3,953` as a permanent count.

### From scratch means from scratch

The student ships with **no pretrained semantic class weights**. It does not download a pretrained neural model. The first projection receives deterministic small symmetry-breaking initialization; class knowledge starts untrained. Knowledge is acquired through validated local lessons.

No PyTorch, TensorFlow, NumPy, cloud API, or external ML runtime is required for the student. Its float parameters are stored in a compact local binary model.

## Feature encoder

The input representation is deterministic and provider-free. It hashes:

- whole normalized phrase;
- word features;
- prefixes/suffixes;
- character 2/3/4/5-grams;
- word bigrams/trigrams.

Hash collisions are expected and learned around; no hash value is treated as semantic truth.

## Training

The student uses real gradient updates and backpropagation.

- Qwen teacher lesson: strongest automatic weight.
- Explicit user-approved EL selection: strongest human evidence.
- Deterministic PASS: weaker bootstrap lesson.
- Rejected Qwen lesson: **zero positive training**.
- Each accepted primary lesson is followed by a small replay batch of older accepted lessons to reduce catastrophic forgetting.
- Model and replay records persist locally.
- Unicode/model-signature changes invalidate incompatible weights rather than silently reusing them.

## Qwen's role

`qwen2.5vl:7b` is the current teacher, not the permanent EL runtime brain.

Qwen may explain the meaning of difficult source text. Qwen does not own EL grammar, does not directly release Emoji Language, and cannot write arbitrary provider prose into the student's truth store.

The teacher may be replaced later without changing the EL Student contract.

## Semantic HOLD supersession

Phase 4 originally locked `HOLD → no AI`. Phase 6 supersedes only that blanket rule.

New rule:

- `PASS` → no provider.
- `HOLD + semantic uncertainty` → student/Qwen learning path is eligible.
- `FAIL + semantic uncertainty` → student/Qwen learning path is eligible.
- runtime/parser/security/auth/recovery/UI/animation failures or HOLDs → provider-ineligible.

This makes EL Bot learn from the exact situations where a hand-authored deterministic rule is least appropriate while preserving non-semantic safety boundaries.

## Student self-release

A high score alone is not sufficient. The current first production gate requires:

1. student prediction exists;
2. student confidence passes threshold;
3. the exact source/candidate has repeated accepted Qwen teacher confirmations;
4. the trusted teacher definition is still available;
5. the candidate passes the full deterministic assisted-validation gate again;
6. provider calls remain zero for that release.

This is intentionally conservative. Later phases may widen student generalization after measured calibration evidence.

## Lexical front end

The Phase-6 Unicode/OEWN work remains useful, but it is no longer the whole strategy.

- Unicode Emoji data provides the dynamic output vocabulary and names.
- Open English WordNet 2025 provides broad deterministic lemma/sense/synonym/taxonomy coverage.
- Easy terms resolve before neural inference.
- Hard/ambiguous terms become student/teacher learning opportunities instead of prompting endless hand-coded exception lists.

## Release gate

Phase 6 is not PASS until one exact final `main` SHA proves:

1. Phase 1–5 gates remain green.
2. Diagnostics remains 44/44.
3. actual Unicode emoji count is derived from the materialized official data.
4. the student parameter count is derived from that count and is approximately one million.
5. the student is not pretrained and has no provider imports.
6. a fresh student can learn a validated example through real gradient updates.
7. persistence/reload preserves learned behavior.
8. rejected teacher lessons do not train.
9. accepted Qwen lessons do train and enter replay.
10. deterministic PASS remains provider-free.
11. semantic HOLD is teacher-eligible.
12. non-semantic/system HOLD remains provider-free.
13. student self-release cannot occur without repeated teacher confirmation + deterministic revalidation.
14. the current local `qwen2.5vl:7b` teacher is reachable on the Windows runner.
15. Windows Setup + Portable packages include the Unicode/OEWN deterministic resources and all student code.
16. packaged runtime smoke passes.
17. exact-final-SHA GitHub Actions succeeds.
