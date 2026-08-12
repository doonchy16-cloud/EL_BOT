# EL Bot Architecture Authority

## Current Phase

**Phase 1 — Architecture & Engine Contracts**

This directory contains architecture authority and verification only. It does not implement the 20 planned language/learning engines.

Read in this order:

1. `../PLANNING_EL_FOREVER_EXPANDING_LANGUAGE_ARCHITECTURE_2026-08-12.md` — Owner-locked product direction and 20-engine expansion planning.
2. `PHASE_1_44_ENGINE_CONTRACTS.md` — reconciled 24 existing + 20 planned engine responsibilities, data contracts, escalation contract, dependency boundaries, and target flow.
3. `phase1_44_engine_registry.json` — machine-readable 44-engine contract and dependency registry.
4. `verify_phase1_architecture.py` — architecture gate used by `.github/workflows/🧱.yml`.

## Hard Boundary

`architecture complete` does **not** mean `feature implemented`.

Phase 1 does not change translation behavior, `📚501`, AI fallback wiring, automatic learning, Complete Candidate Search runtime behavior, hourglass/UI polish, or Windows packaging.

Phase 2 may begin only after the Phase 1 architecture gate is green.
