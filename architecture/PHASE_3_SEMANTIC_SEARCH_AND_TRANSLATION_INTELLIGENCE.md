# EL Bot — Phase 3 Semantic Search & Full Translation Intelligence

**Status:** 🟡 IMPLEMENTATION IN PROGRESS

**Authority date:** 2026-08-12

Phase 3 implements the deterministic semantic/search layer required to make ABC → Emoji substantially less dictionary-bound while preserving the locked rule that AI is not used unless a later phase explicitly authorizes a genuine deterministic FAIL fallback.

## Source-present Phase-3 engines

| Target ID | Runtime | Engine | Phase-3 ownership |
|---|---:|---|---|
| N02 | 🔍 | Complete Candidate Search | evaluate every coordinate in the declared finite frontier |
| N03 | 🧩 | Concept Decomposition | break a resolved sense into roles/actions/entities/functions |
| N04 | 🗺️ | Semantic Graph | deterministic concept/sense graph and related-term queries |
| N07 | 🧫 | Experiment | controlled semantic/context experiments |
| N08 | 🏆 | Candidate Competition | rank already-evaluated surviving candidates |
| N13 | 🧭 | Context & Sense Disambiguation | contextual sense/proper-noun/polysemy decisions |
| N14 | 🧱 | EL Grammar & Composition | meaning-preserving canonical EL structural templates |
| N16 | ♾️ | Search Frontier & Exhaustion | exact finite coordinates, counts, checkpoints, expansion and exhaustion proof |
| N18 | 🪤 | Counterexample & Adversarial Semantics | seek contexts that falsify proposed senses |

These nine bring the target architecture to **39 source-present engines**, leaving five planned-only learning engines for Phase 4.

## Complete-search truthfulness

`complete` means complete for an explicitly declared finite frontier.

- ♾️ computes the exact coordinate count as `sum(N^length)` across the declared length range.
- 🔍 evaluates every coordinate it visits and errors if its evaluation ledger count differs from the declared visited interval.
- A frontier is marked exhausted only when its cursor reaches the exact total.
- Checkpoint/resume and expansion preserve the distinction between `partially visited` and `exhausted`.
- No candidate is silently removed because a heuristic calls it impossible.

For resolved unknown ABC concepts, the Phase-3 bridge performs an **exhaustive depth-1 pass across every unit in the loaded 🌐 Emoji Universe**. Multi-symbol meanings can also be supplied by 🧱 grammar templates, while ♾️/🔍 can represent and exhaust deeper Cartesian frontiers when explicitly requested. Phase 3 does not falsely claim that an astronomical deeper frontier was exhausted when it was not.

## Canonical release boundary

🌐 contains investigable units beyond 📚501, but 📚501 remains the canonical release authority in Phase 3.

Therefore:

- every loaded universe unit may be evaluated;
- non-501 units may survive semantic investigation and appear in search evidence;
- they are **not automatically promoted into canonical EL**;
- canonicalization/learning of new vocabulary remains gated behind later evidence/integrity/graduation/versioning work.

This preserves the forever-expanding design without bypassing the knowledge-safety boundary built in Phase 2.

## Normal-word rescue path

For a legacy unknown term:

```text
legacy deterministic parse
  → 🧭 resolve context/sense
  → 🧩 decompose meaning
  → 🗺️ expand semantic relationships
  → 🧱 create canonical EL structural candidates
  → ♾️ full loaded-universe depth-1 frontier
  → 🔍 evaluate every unit
  → 🏆 rank survivors
  → merge Phase-3 candidates back into the existing 24-stage ABC engine
  → existing deterministic audits + round trip + winner selection
```

Initial locked regression targets include `converter`, `ChatGPT`, and `words`.

## Ambiguity rule

A surface word is not permanently assigned one meaning merely because one context worked. Example:

- `words` in a normal language sentence → language-word sense;
- `Microsoft Word` in a document/software context → product sense.

🧫 validates such context expectations and 🪤 actively records contexts that falsify an over-broad proposed sense.

## Still not Phase 3

Phase 3 does **not** implement:

- Qwen/Ollama fallback;
- Forgey fallback;
- automatic learning writes;
- 🎓 knowledge graduation;
- 🧬 generalization from learned evidence;
- ♻️ learned-knowledge revalidation;
- 📈 learning analytics;
- 🧺 knowledge consolidation;
- hourglass/UI polish;
- Windows packaging.

## PASS gate

Phase 3 can be called PASS only after the exact final `main` head proves all of the following in CI:

- all nine Phase-3 engine sources import and are provider-free;
- 📚501 remains unchanged;
- contextual Word-vs-words sense resolution behaves deterministically;
- `converter`, `ChatGPT`, and `words` decompose and compose to non-failing canonical EL candidates;
- an exact 3-unit depth-2 frontier evaluates 12/12 candidates;
- a full loaded 🌐 depth-1 frontier is exhausted with no skipped coordinates;
- candidate competition is deterministic;
- experiment and counterexample engines distinguish context success from over-broad claims;
- ABC → Emoji resolves the initial normal-word regression targets without AI;
- genuinely unresolved nonsense remains a deterministic FAIL;
- existing regression behavior remains green;
- Diagnostics expands from 30 to 39 checks;
- Phase-1 and Phase-2 gates remain green.
