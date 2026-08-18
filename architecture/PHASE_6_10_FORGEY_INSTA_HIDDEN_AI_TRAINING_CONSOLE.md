# Phase 6.10 — Hidden Forgey Insta AI & Training Console

**Status:** 🔒 LOCKED PLAN — STEP 4 IMPLEMENTATION PAUSED

**Canonical intelligence:** `Forgey Insta:EL-Bot`

This is planning authority only. The hidden console must not be implemented during Step 1.

## Locked hidden entry

The existing **🤖 AI identity emoji at the far-left of EL Bot's top header** is the sole concealed UI activation target.

- click the existing 🤖 **5 times within 3 seconds**;
- clicks 1–4 produce no visible response;
- the fifth valid click opens Forgey Insta admin authentication;
- timeout, clicking another control, app focus loss, or abandoning the sequence resets it silently;
- no click counter or progress indicator.

The 🤖 must give **zero discovery clue**:
- no hover animation;
- no hover glow/background/color change;
- no tooltip;
- no pointer/hand cursor;
- no pressed state;
- no visible keyboard-focus clue for the hidden action;
- no nearby Admin/Settings/Training label;
- no ordinary navigation entry.

Hidden access is not the security boundary. Discovering the five-click gesture grants only the password prompt.

## Authentication/security direction

- owner-supplied bootstrap credential is temporary and must be rotated later;
- the literal credential must never be committed, hard-coded, packaged in recoverable plaintext, logged, or shown in evidence;
- implementation must use a salted slow password verifier or appropriate OS-backed secret storage;
- short-lived local admin session;
- failed attempts rate-limited;
- restart/session expiry closes admin access;
- credential rotation invalidates old sessions/verifier;
- no hidden backdoor recovery password;
- no remote admin endpoint by default.

Sensitive operations require re-authentication plus explicit high-friction confirmation and verified audit logging, including model promotion, rollback, trusted-evidence deletion/quarantine, teacher/provider changes, training-policy changes, and credential rotation.

## Planned console areas

1. 🧠 Overview — production/candidate generation, parameter count, architecture/tokenizer signature, model hash, readiness.
2. ⚡ Live AI Status — real inference state, direction, latency, confidence, validation, support/teacher usage, CPU/RAM where measurable.
3. 📖 Knowledge Foundation — Unicode version/count, OEWN edition/counts, tokenizer vocabulary, hashes/provenance.
4. 🦙 Qwen Teacher — reachability, model, calls, latency, accepted/rejected lessons, dependency rate.
5. 🎓 Learning Evidence — deterministic truth, user corrections, validated teacher lessons, negative evidence, provenance/trust tiers.
6. 🏋️ Training — candidate generation, dataset hash/splits, optimizer/config, progress/loss/checkpoints, start/pause/stop/validate/compare controls.
7. 🧪 Benchmarks & Promotion — production-vs-candidate accuracy, round-trip, ambiguity, unknown rejection, semantic loss, latency, regressions.
8. 🗃️ Generations & Rollback — G0→G1→G2 lineage, reports, hashes, promotion/rejection reason, rollback.
9. 📈 Learning Analytics — Forgey Insta conversion share ↑, Qwen dependency ↓, accuracy ↑, corrections/semantic loss ↓.
10. 📜 Audit & Security — truthful auth/training/promotion/rollback/config events without secrets.

No fake status, fake activity, fake charts, fake generation progress, or fake metrics are allowed.

## Implementation gate

**Step 4 is paused. This file records the locked hidden-console design only.**
