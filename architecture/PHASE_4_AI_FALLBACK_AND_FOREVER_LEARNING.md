# EL Bot — Phase 4 AI Fallback & Forever-Learning Loop

**Status:** ✅ PASS — IMPLEMENTED AND CI-GATED

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
      → mature learned mapping lookup
      ├─ validated/canonical mapping → deterministic revalidation → release if still valid
      └─ no releasable learned mapping
          → ✦ Forgey Orchestration policy
          → 🔌 internal provider connector
          → TEMP: 🦙 Ollama / qwen2.5vl:7b
          → semantic resolution only
          → EL Bot deterministic construction + validation + reverse verification
          ├─ PASS → release validated assisted candidate
          └─ HOLD/FAIL → reject assistance and preserve safe deterministic failure
```

The ABC→Emoji engine remains provider-free. Provider-specific code lives behind `🔌/🧠`. Forgey Orchestration owns escalation/routing policy and contains no Ollama HTTP/model implementation.

## Temporary provider reality

The current temporary provider is **`ollama:qwen2.5vl:7b`**. It is intentionally treated as a semantic resolver, not an Emoji Language author.

On the current Windows runner, Qwen2.5VL text inference is materially slower than normal deterministic translation. Repeated 120-second tests timed out even after the semantic request was reduced to a tiny output. Therefore only this Phase-4 semantic adapter has a **300-second bounded generation timeout**, which remains below the Electron host's existing **350-second process ceiling**.

This is a temporary performance compromise, not the desired long-term provider behavior. Forgey is still the planned complete replacement behind the same connector/orchestration boundary.

The current provider emits a tiny internal semantic wire result. EL Bot converts that result into a strict internal object and discards any model-authored EL. Raw provider text is never released as Emoji Language output.

## New Phase-4 engines

| ID | Runtime | Engine | Authority |
|---|---:|---|---|
| N06 | 🎓 | Knowledge Graduation | maturity transitions and canonical eligibility |
| N09 | 🧬 | Generalization | reusable hypotheses from validated examples |
| N11 | ♻️ | Revalidation | retest learned knowledge and recommend promotion/demotion review |
| N12 | 📈 | Learning Analytics | deterministic success, AI fallback, acceptance, learned-hit and maturity trends |
| N20 | 🧺 | Knowledge Consolidation | merge compatible duplicates while preserving evidence/provenance |

These five bring EL Bot to **44 / 44 source-present target engines**. Diagnostics now owns **44 / 44 functional engine checks**.

## Assisted validation boundary

The failed original deterministic translation does not automatically poison an assisted candidate. Instead the assisted meaning must independently prove:

- valid EL syntax;
- canonical vocabulary membership;
- no unknown marker in released output;
- semantic-definition alignment;
- preservation of already-recognized source meaning;
- number preservation;
- relationship preservation;
- critical/negation retention;
- deterministic reverse translation;
- deterministic round-trip quality thresholds.

A failed assisted validation is a rejection, never a best-effort release.

## Forever-learning evidence rule

Every actual provider-assisted attempt becomes evidence:

- accepted validated assists add positive provider evidence;
- rejected/invalid assists add negative evidence and provider provenance to a rejection episode;
- raw provider definitions are not stored as learned truth;
- user selection can add independent user evidence;
- experiments and counterexample tests add independent evidence;
- revalidation adds independent evidence;
- knowledge maturity is controlled only by 🎓;
- 🧿 integrity can block or demote;
- 🗃️ versions make every knowledge mutation reversible;
- 🧺 consolidation preserves evidence/provenance and flags conflicts;
- 📈 measures whether provider dependency decreases.

A single provider success remains **discovered**, not canonical. Canonical graduation requires repeated evidence, multiple source kinds, integrity PASS, experiment PASS, counterexample PASS, and revalidation PASS.

## Learned deterministic reuse

Validated/canonical learned mappings are checked before a provider call after a deterministic FAIL. They are deterministically revalidated before release. A valid learned mapping therefore prevents a later provider call and increments the learned-hit metric instead of the AI-attempt metric.

The static **📚501** source authority remains unchanged. Learned claims live in a versioned learning overlay; they do not silently rewrite the 501 base vocabulary.

## CI evidence contract

Phase 4 is gated to prove:

- all five new engine sources are present and exercised;
- Diagnostics = **44 / 44**;
- PASS and HOLD paths make zero provider calls;
- only deterministic FAIL may trigger ✦ escalation;
- the provider adapter is isolated behind 🔌;
- the temporary provider is truthfully identified as `ollama:qwen2.5vl:7b`;
- raw provider output cannot use the public connector path;
- valid assisted candidates require deterministic validation before release;
- malformed/unverifiable assistance is rejected;
- accepted and rejected attempts create positive/negative learning evidence;
- one provider success cannot become canonical;
- full cross-source evidence can graduate discovered → provisional → validated → canonical;
- failed revalidation can demote knowledge;
- generalization produces hypotheses, not automatic truth;
- consolidation preserves evidence/provenance and detects conflicts;
- mature learned knowledge can eliminate a later provider call;
- Phase 1, Phase 2, and Phase 3 gates remain green;
- the real local Qwen adapter is available and returns the strictly validated semantic structure;
- the exact final `main` SHA must have a successful GitHub Actions run.

## Next boundary

**Phase 5 — Visual Polish & Windows Packaging** remains **NOT AUTHORIZED** by this document.

Phase 4 did not implement the planned hourglass visual polish or Windows packaging.
