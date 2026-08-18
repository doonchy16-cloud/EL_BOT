# Phase 6.1 — Forgey Insta:EL-Bot G0 Model Specification

**Status:** 🔥 STEP 2 IMPLEMENTATION AUTHORIZED

This file records the owner-approved G0/G1 design direction. Step 1 is merged; Step 2 is now authorized. Steps 3–5 remain paused.

## Purpose

Build a small, from-scratch, bidirectional EL-specialist sequence model that can eventually become the primary ABC↔EL intelligence.

## Locked G0 direction

- model family: small Transformer encoder-decoder;
- directions: ABC→EL and EL→ABC in one model;
- direction control tokens: `<ABC_TO_EL>` and `<EL_TO_ABC>`;
- embedding/model width target: 128;
- attention heads: 4;
- encoder layers: 3;
- decoder layers: 3;
- feed-forward width target: approximately 384–512;
- initial context target: approximately 128 tokens;
- initial trainable parameter target: approximately 1–3 million, expected roughly 2–3 million after the exact tokenizer/vocabulary dimensions are known;
- parameter count must be calculated from the real architecture, never frozen as a magic number;
- random initialization;
- no pretrained semantic model weights;
- training may use a standard tensor/autodiff framework such as PyTorch; 'from scratch' refers to architecture weights/data, not reimplementing matrix multiplication;
- production export may use a compact local runtime artifact such as ONNX if later evidence supports it.

## Tokenizer direction

English side:
- byte-level BPE trained from scratch on the approved corpus;
- no permanent unknown-word ceiling because raw bytes remain representable;
- vocabulary size chosen from measured corpus compression + model-size evidence during Step 2.

EL side:
- every released official emoji grapheme/sequence remains atomic;
- EL structural/control symbols remain atomic;
- emoji sequences must not be split into individual Unicode code points;
- model special tokens remain separate from EL output tokens.

The Step-1 `📚/🔤` authority defines the immutable tokenizer source inventories. It is not itself the trained tokenizer.

## G0 implementation contract

G0 must be instantiated from random weights and report its exact trainable parameter count from the implemented tensor graph. G0 must be executable in both directions before training, even though random output is not expected to be semantically useful.

The Step-2 implementation uses one shared token embedding and one tied output projection where evidence supports the parameter target. This is an implementation detail of the single bidirectional model, not a second model.

## G1 bootstrap contract

G1 is the first trained candidate from trusted, deterministic bootstrap evidence only:
- official Unicode emoji names/atomic sequences;
- existing validated historical semantic meanings;
- deterministic EL structural examples;
- no Qwen/provider-generated positive truth;
- no unverified self-output as positive truth.

The frozen Step-2 benchmark must be excluded from model training/replay examples. Its exact content/hash is evidence authority for this step.

G1 is a candidate, not Phase-6 production. Step 4 later decides production routing; Step 3 later owns teacher-driven continuing learning and generation promotion/rollback policy.

## Generation lifecycle

`G0` = architecture + random weights.

`G1` = first trained candidate from trusted bootstrap curriculum.

Later generations are candidate-trained from new validated evidence and promoted only if benchmark, adversarial, round-trip, regression, calibration, and safety gates pass relative to production.

Production weights do not update live after each prediction. Unverified self-output cannot become positive training truth.

## Frozen evaluation requirement

A held-out benchmark must never be included in training/replay data. It must cover at least easy words, morphology, compounds, ambiguity, context, negation, relationships, numbers/time, technical language, unknown/nonsense inputs, ABC→EL, and EL→ABC.

Step 2 must prove at minimum:
- G1 training objective improves materially from early to late training;
- G1 frozen-benchmark loss improves over G0;
- the saved G1 artifact reloads into a fresh local process/model instance;
- local greedy inference executes in both directions without a provider;
- tokenizer byte fallback round-trips unseen English text;
- official emoji remain atomic tokens;
- no Step-3 teacher/Qwen training path is implemented.

## Implementation gate

**Step 2 is authorized. Steps 3–5 remain paused.**
