# Phase 6.1 — Forgey Insta:EL-Bot G0 Model Specification

**Status:** 🔒 LOCKED PLAN — STEP 2 IMPLEMENTATION PAUSED

This file records the owner-approved G0 design direction. It does not authorize model implementation during Step 1.

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
- vocabulary size chosen from measured corpus/accuracy/size evidence during Step 2.

EL side:
- every released official emoji grapheme/sequence remains atomic;
- EL structural/control symbols remain atomic;
- emoji sequences must not be split into individual Unicode code points;
- model special tokens remain separate from EL output tokens.

The Step-1 `📚/🔤` authority defines the immutable tokenizer source inventories. It is not itself the trained tokenizer.

## Generation lifecycle

`G0` = architecture + random weights.

`G1` = first trained candidate from trusted bootstrap curriculum.

Later generations are candidate-trained from new validated evidence and promoted only if benchmark, adversarial, round-trip, regression, calibration, and safety gates pass relative to production.

Production weights do not update live after each prediction. Unverified self-output cannot become positive training truth.

## Frozen evaluation requirement

A held-out benchmark must never be included in training/replay data. It must cover at least easy words, morphology, compounds, ambiguity, context, negation, relationships, numbers/time, technical language, unknown/nonsense inputs, ABC→EL, and EL→ABC.

## Implementation gate

**Step 2 is paused. This file is design authority only until the owner separately authorizes Step 2.**
