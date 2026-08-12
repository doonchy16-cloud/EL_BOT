# EL Bot Architecture Authority

## Current Phase

**Phase 2 — 🌐📚 Knowledge Foundation**

Phase 1 is complete and green. Phase 2 is implementing the safe knowledge substrate for the forever-expanding Emoji Language while keeping AI fallback, automatic learning, search, graduation, and vocabulary mutation disabled.

Read in this order:

1. `../PLANNING_EL_FOREVER_EXPANDING_LANGUAGE_ARCHITECTURE_2026-08-12.md` — Owner-locked product direction and 20-engine expansion planning.
2. `PHASE_1_44_ENGINE_CONTRACTS.md` — reconciled 44-engine target architecture and dependency boundaries.
3. `phase1_44_engine_registry.json` — immutable Phase-1 target registry snapshot.
4. `verify_phase1_architecture.py` — Phase-1 architecture gate.
5. `PHASE_2_KNOWLEDGE_FOUNDATION.md` — Phase-2 implementation scope, boundaries, and PASS criteria.
6. `phase2_knowledge_foundation_manifest.json` — machine-readable Phase-2 source-present manifest.
7. `verify_phase2_knowledge_foundation.py` — deterministic Phase-2 foundation gate.

## Phase-2 source-present target engines

- 🌐 Emoji Universe
- 📊 Evidence & Confidence
- 🧿 Knowledge Integrity
- 🧷 Emoji Canonicalization
- 📜 Provenance Ledger
- 🗃️ Knowledge Versioning & Rollback

Source-present target count: **30 / 44**.
Remaining planned-only target count: **14 / 44**.

## CI Enforcement

The established `.github/workflows/🧪.yml` workflow runs `🧪/🚀` as its release smoke gate. `🧪/🚀` executes both Phase-1 and Phase-2 verifiers, and the normal Diagnostics Engine now owns 30 engine checks.

## Hard Boundary

Phase 2 does **not** enable:

- AI fallback from ABC → Emoji;
- automatic knowledge writes;
- 🎓 graduation/canonical promotion;
- 🔍 Complete Candidate Search runtime;
- 🧬 generalization;
- ♻️ revalidation;
- 🧺 consolidation;
- hourglass/UI polish implementation;
- Windows packaging.

`📚501` remains unchanged and locked as the current canonical vocabulary count.
