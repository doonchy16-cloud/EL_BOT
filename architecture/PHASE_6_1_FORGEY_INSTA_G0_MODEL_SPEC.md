# Phase 6.1 — Forgey Insta:EL-Bot G0/G1 Model Specification

**Status:** ✅ STEP 2 TEXT AUTHORITY PASS — NATIVE-VISION OWNER EXTENSION REQUIRED BEFORE PHASE-6 RELEASE

Step 2 originally verified the first real from-scratch Forgey Insta G0/G1 text/EL implementation. On 2026-08-19, before final Phase-6 release, the Owner explicitly required `Forgey Insta:EL-Bot` to be a vision model too. This newer authority extends the same G0/G1 graph; it does not add engine #45 or replace the verified text architecture.

## Purpose

Build one small, from-scratch, multimodal EL-specialist Transformer that serves ABC↔EL and native Image→EL / Image→ABC intelligence.

## Locked shared Transformer architecture

- model family: Transformer encoder-decoder;
- text directions: ABC→EL and EL→ABC in one shared model;
- text direction control tokens: `<ABC_TO_EL>` and `<EL_TO_ABC>`;
- native visual directions: `IMAGE_TO_EL` and `IMAGE_TO_ABC` as learned model-internal direction embeddings;
- embedding/model width: 128;
- attention heads: 4;
- encoder layers: 3;
- decoder layers: 3;
- feed-forward width: 384;
- context: 128 source/target positions;
- random initialization;
- no pretrained semantic or visual weights;
- shared token embedding with tied output projection;
- PyTorch is tensor/autodiff runtime only; Forgey model weights are trained from scratch;
- total trainable parameters are always derived from the actual graph and must remain inside 1–3 million.

The historical pre-native-vision candidate graph had **1,788,672** trainable parameters. That value remains valid historical evidence but is **not** the final multimodal runtime constant.

## Native vision extension — release-blocking Owner authority

The same checkpoint includes a trainable visual source branch:

- input: normalized RGB pixels;
- initial locked normalized geometry: 64×64;
- patch size: 8×8;
- patch count: 64;
- learned Conv2d RGB patch projection into the shared 128-dimensional model space;
- learned visual position embeddings;
- learned visual direction embeddings for Image→EL / Image→ABC;
- learned visual modality embedding;
- resulting visual source sequence enters the same Transformer encoder/decoder used by text.

The visual direction controls do not consume or expand user/EL tokenizer IDs.

## Tokenizer

English side:
- byte-level BPE trained from scratch;
- raw UTF-8 byte fallback preserves unseen text;
- vocabulary selected from measured compression candidates;
- historical candidate evidence selected 320 BPE merges and a 4,536-ID total model vocabulary.

EL side:
- released official emoji graphemes/sequences remain atomic;
- EL structural/control symbols remain atomic;
- emoji sequences are not split into individual Unicode code points;
- model special tokens remain separate from EL output tokens;
- literal user text that looks like `<ABC_TO_EL>` is encoded as user text, not interpreted as privileged control.

Image sources do not bypass the authoritative decoder/tokenizer output space.

## G1 bootstrap + native visual curriculum

Text G1 remains trained only from trusted deterministic bootstrap evidence:
- official Unicode emoji names/atomic sequences;
- existing validated historical semantic meanings;
- deterministic EL structural examples;
- no Qwen/provider-generated positive truth;
- no unverified self-output as positive truth.

Native visual G1 is trained from deterministic pixel scenes whose targets are independently known before model execution. Initial visual curriculum includes simple colors/shapes/warning/check/cross/arrows with both ABC and EL targets. This curriculum is not intended to pretend general OCR/scene understanding already exists; it establishes real from-scratch pixel learning and a safe expandable visual foundation.

During the visual adapter stage, non-visual model parameters are frozen so the visual branch learns alignment without silently rewriting verified text weights. Protected text probes must remain exact after visual training.

## Native visual evaluation

Release-bound G1 must prove:
- visual training loss materially improves;
- zero provider-authored positive visual truth;
- zero unverified self-output visual truth;
- held-out pixel probes are exact for both Image→EL and Image→ABC;
- fresh-process inference decodes actual PNG pixels rather than accepting pre-extracted labels;
- provider calls are zero for successful native visual inference;
- protected text probes remain exact;
- model remains in the locked 1–3M parameter envelope.

## Historical Step-2 candidate evidence

Windows Step-2 workflow run **#5 / ID `32164249835`** on candidate branch head `23358db464fdc2ce3cd6a7f1be45a3bd0b769eef` completed successfully for the original text authority.

Observed historical evidence:
- model parameters: **1,788,672** pre-native-vision;
- tokenizer vocabulary: **4,536** IDs;
- BPE merges: **320**;
- broad G1 training loss: **6.7869 → 4.1417**;
- frozen benchmark loss: **G0 8.4877 → final G1 4.8358**;
- trusted rehearsal loss: **3.2511 → 2.3778**;
- trusted rehearsal probes: **8/8 exact**;
- fresh-process `rocket → 🚀`: exact;
- fresh-process `🚀 → rocket`: exact;
- provider calls during local inference: **0**;
- Phase-2 compatibility: PASS;
- Phase-3 compatibility: PASS;
- 44/44 diagnostics: PASS.

These numeric values are historical evidence. Final multimodal values must come from the live graph/evidence.

## Generation lifecycle

`G0` = architecture + random weights including randomly initialized visual branch.

`G1` = trusted bootstrap text training + trusted rehearsal + deterministic native-vision adapter training.

`G2` and later generations inherit the same multimodal graph. Text teacher learning may update the shared Transformer, so the visual adapter is re-aligned from deterministic pixel truth before promotion. Promotion must include native-vision non-regression.

Production weights do not update live after each prediction. Unverified self-output cannot become positive training truth in either modality.

## Implementation gate

**The historical Step-2 text authority remains PASS. Final Phase-6 release additionally requires the native-vision Owner extension to pass exact-head G1/G2, runtime, package, and exact-main release gates.**
