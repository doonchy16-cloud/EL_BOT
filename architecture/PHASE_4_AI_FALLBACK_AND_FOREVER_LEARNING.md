# EL Bot — Phase 4 AI Fallback & Forever-Learning Loop

**Status:** 🟡 IMPLEMENTATION IN PROGRESS

**Authority date:** 2026-08-12

Phase 4 completes the 44-engine target and activates the owner-locked external-intelligence fallback without changing the permanent deterministic-first rule.

## Permanent translation rule

```text
ABC input
  → deterministic ABC→Emoji
  → quality audit
  ├─ PASS → release normally; no provider call
  ├─ HOLD → preserve HOLD; no provider call
  └─ FAIL
      → ✦ Forgey Orchestration policy
      → 🔌 internal provider connector
      → TEMP: 🦙 Ollama / qwen2.5vl:7b
      → structured semantic resolution
      → deterministic EL validation + reverse verification
      ├─ PASS → release validated assisted candidate
      └─ HOLD/FAIL → reject provider candidate and keep safe deterministic failure
```

The ABC→Emoji engine itself must remain provider-free. Provider-specific code belongs behind the connector adapter. Forgey Orchestration owns only escalation/routing policy and must not contain Ollama HTTP/model implementation.

## Provider semantic contract

The provider is asked to resolve meaning, not to become final Emoji Language authority. The temporary provider returns a structured internal object containing:

- whether the source is meaningfully resolvable;
- a short semantic definition/paraphrase;
- an optional candidate EL expression;
- a confidence estimate.

The provider response is internal evidence only. Raw provider prose is never emitted as EL output.

EL Bot validates assisted output through two possible paths:

1. **semantic-definition path** — translate the provider definition through the normal deterministic ABC→Emoji engine, then validate the resulting canonical EL against original recognized semantics, numbers, relationships, negation/critical information, and deterministic round trip;
2. **provider-candidate path** — only if a candidate EL expression is supplied, parse it as EL, require canonical vocabulary, reverse it deterministically to ABC, translate the reverse text back to EL, and require strict assisted validation before release.

A failed assisted validation is a rejection, not a best-effort translation.

## New Phase-4 engines

| ID | Runtime | Engine | Authority |
|---|---:|---|---|
| N06 | 🎓 | Knowledge Graduation | maturity transitions and canonical eligibility |
| N09 | 🧬 | Generalization | reusable hypotheses from validated examples |
| N11 | ♻️ | Revalidation | retest learned knowledge and recommend promotion/demotion review |
| N12 | 📈 | Learning Analytics | deterministic success, AI fallback, acceptance, learned-hit and maturity trends |
| N20 | 🧺 | Knowledge Consolidation | merge compatible duplicates while preserving evidence/provenance |

These five bring EL Bot to **44 / 44 source-present target engines**.

## Forever-learning evidence rule

Every provider-assisted attempt becomes learning evidence:

- accepted validated assists add positive evidence;
- rejected/invalid assists add negative evidence;
- provider/model/version and validation result are preserved in provenance;
- user selection can add independent user evidence;
- revalidation adds independent revalidation evidence;
- knowledge maturity is controlled only by 🎓;
- 🧿 integrity can block or demote;
- 🗃️ versions make learned state reversible;
- 🧺 consolidation never silently deletes evidence;
- 📈 measures whether provider dependency decreases.

A single provider success cannot become canonical. Strong promotion requires repeated evidence, multiple source kinds, integrity PASS, experiments/counterexamples, and revalidation.

## Learned deterministic reuse

Validated/canonical learned mappings may be reused before a provider call when the normal translator still FAILs. That reuse is deterministic and increments the learned-hit metric instead of the AI-attempt metric. This is the mechanism by which external-AI dependency can fall over time.

The static 📚501 source authority remains unchanged in Phase 4. Learned claims live in a versioned learning overlay; they do not silently rewrite the 501 base vocabulary.

## PASS gate

Phase 4 may be called PASS only when the exact final `main` SHA proves in CI:

- all five new engine sources are present and individually exercised;
- Diagnostics expands from 39 to 44 checks;
- PASS and HOLD translation paths perform zero provider calls;
- only deterministic FAIL may trigger ✦ escalation;
- the provider adapter is the only normal-translation layer importing Ollama;
- current temporary provider is truthfully identified as `ollama:qwen2.5vl:7b`;
- structured provider output is never directly released;
- valid assisted candidates pass deterministic validation before release;
- invalid/malformed assisted candidates are rejected;
- accepted and rejected provider attempts produce positive/negative learning evidence respectively;
- a single provider success cannot graduate to canonical;
- cross-source evidence can promote through discovered → provisional → validated → canonical only when the full graduation contract is met;
- revalidation can recommend demotion;
- generalization outputs hypotheses, not automatic truth;
- consolidation preserves provenance/evidence and identifies conflicts;
- learned validated/canonical mappings can prevent a later provider call;
- Phase 1, 2, and 3 gates remain green;
- the exact final GitHub Actions run succeeds on the exact final `main` SHA.

## Not Phase 4

Phase 4 does not include hourglass visual polish or Windows packaging. Those remain locked until separately authorized.
