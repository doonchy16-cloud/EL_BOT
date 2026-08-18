# Phase 6.1 — Forgey Insta:EL-Bot G0/G1 Model Specification

**Status:** ✅ STEP 2 PASS — G0/G1 VERIFIED

Step 1 is merged. Step 2 has now produced and verified the first real from-scratch Forgey Insta G0/G1 implementation. Steps 3–5 remain paused.

## Purpose

Build a small, from-scratch, bidirectional EL-specialist sequence model that can eventually become the primary ABC↔EL intelligence.

## Locked G0 architecture — implemented

- model family: Transformer encoder-decoder;
- directions: ABC→EL and EL→ABC in one shared model;
- direction control tokens: `<ABC_TO_EL>` and `<EL_TO_ABC>`;
- embedding/model width: 128;
- attention heads: 4;
- encoder layers: 3;
- decoder layers: 3;
- feed-forward width: 384;
- context: 128 tokens;
- exact observed trainable parameters: **1,788,672** on the candidate evidence run;
- parameter count is calculated from the actual model graph, not read from a magic constant;
- random initialization;
- no pretrained semantic model weights;
- shared token embedding with tied output projection;
- PyTorch is used only as the tensor/autodiff runtime; architecture weights are initialized from scratch.

## Tokenizer — implemented

English side:
- byte-level BPE trained from scratch;
- raw UTF-8 byte fallback preserves unseen text;
- vocabulary selected from measured compression candidates rather than a fixed marketing size;
- candidate evidence selected 320 BPE merges and a 4,536-ID total model vocabulary.

EL side:
- released official emoji graphemes/sequences remain atomic;
- EL structural/control symbols remain atomic;
- emoji sequences are not split into individual Unicode code points;
- model special tokens remain separate from EL output tokens;
- literal user text that looks like `<ABC_TO_EL>` is encoded as user text, not interpreted as a privileged direction command.

The Step-1 `📚/🔤` authority remains the immutable tokenizer-source inventory. `📚/✂️` is the trained Step-2 tokenizer implementation.

## G0 implementation contract — PASS

G0 instantiates from random weights and reports its exact trainable parameter count from the real tensor graph. The locked 1–3 million target is satisfied by the observed 1,788,672-parameter graph.

## G1 bootstrap contract — PASS

G1 is trained only from trusted deterministic bootstrap evidence:
- official Unicode emoji names/atomic sequences;
- existing validated historical semantic meanings;
- deterministic EL structural examples;
- no Qwen/provider-generated positive truth;
- no unverified self-output as positive truth.

The frozen Step-2 benchmark is excluded from broad training and trusted rehearsal by source key. A second trusted rehearsal stage uses only admitted non-benchmark deterministic curriculum plus broad replay; it is still bootstrap training, not Step-3 teacher learning.

## Candidate evidence

Windows Step-2 workflow run **#5 / ID `32164249835`** on candidate branch head `23358db464fdc2ce3cd6a7f1be45a3bd0b769eef` completed successfully.

Observed evidence from that run:
- model parameters: **1,788,672**;
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

The numeric values above are historical evidence from the candidate run. The implementation continues to derive tokenizer and parameter values from the actual corpus/model graph.

## Generation lifecycle

`G0` = architecture + random weights.

`G1` = first trained candidate from trusted bootstrap curriculum plus trusted non-benchmark rehearsal.

G1 is **not yet the app's production primary intelligence**. Step 4 later owns primary runtime routing. Step 3 later owns Qwen-teacher evidence, continuing-learning generations, promotion/rejection, and rollback policy.

Production weights do not update live after each prediction. Unverified self-output cannot become positive training truth.

## Frozen evaluation requirement — satisfied for Step 2

The frozen benchmark covers easy words, morphology, compounds, ambiguity, context, negation, relationships, numbers/time, technical language, unknown/nonsense inputs, ABC→EL, and EL→ABC. It is marked training/replay-forbidden and the verifier proves zero source-key overlap with both broad training and trusted rehearsal.

## Implementation gate

**Step 2 is PASS. Steps 3–5 remain implementation-paused until separately authorized by the owner.**
