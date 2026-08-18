# EL Bot — Phase 6.10 Hidden Forgey Insta AI & Training Console

**Status:** 🔒 LOCKED PLAN — IMPLEMENTATION PAUSED

**Canonical intelligence:** `Forgey Insta:EL-Bot`

This document defines the hidden administrative AI/training console for `Forgey Insta:EL-Bot`. It is planning authority only. No implementation is authorized by this file.

## Purpose

EL Bot needs a private owner/admin surface for observing and controlling the intelligence that normal users should never need to see. The page is for model status, training evidence, Qwen-teacher activity, generations, benchmarks, promotion/rejection, rollback, dataset health, diagnostics, and security auditing.

The console is **not** part of normal EL Bot navigation and must never be required for ordinary ABC↔EL use.

## Locked hidden-entry design

The existing **🤖 AI identity emoji at the far-left side of the normal top header** is the sole concealed UI activation target for the Forgey Insta admin console.

### Secret activation sequence

- Click the existing 🤖 emoji **5 times within 3 seconds**.
- Clicks 1–4 produce **no visible response whatsoever**.
- The fifth valid click reveals the Forgey Insta admin authentication prompt.
- If more than 3 seconds elapse before the fifth click, the sequence resets silently.
- Clicking another control, losing application focus, or otherwise abandoning the sequence resets it silently.
- No click counter or progress indicator is shown.

### The 🤖 must look non-interactive

The normal user receives no discovery clue:

- no hover animation;
- no hover color/glow/background change;
- no tooltip;
- no pointer/hand cursor;
- no pressed state;
- no visible keyboard-focus ring for the hidden action;
- no context-menu clue;
- no nearby Admin/Settings/Training label;
- no visible navigation item to the console.

The emoji remains visually identical to its normal identity/status presentation. The hidden click detector must not interfere with its existing visual role.

### Authentication remains the real security boundary

The five-click sequence is only an accidental-discovery barrier. Discovering the gesture does not grant admin access.

```text
🤖 ×5 within 3 seconds
        ↓
🔐 Forgey Insta admin authentication
        ↓
short-lived authenticated admin session
        ↓
Forgey Insta:EL-Bot — AI & Training Console
```

Sensitive operations such as model promotion, rollback, trusted-evidence deletion/quarantine, teacher changes, training-policy changes, or credential rotation require re-authentication plus explicit high-friction confirmation.

## Access/security model

1. **No visible normal-navigation entry.** No menu item, toolbar button, help link, route hint, or ordinary navigation path exposes the console.
2. **Locked hidden activation:** exactly 5 clicks on the existing 🤖 AI emoji within 3 seconds, with zero hover/cursor/tooltip/visual clues.
3. **Admin authentication prompt.** Access requires the owner-supplied bootstrap admin credential or its rotated successor.
4. **No plaintext credential in source, repository, packaged resources, logs, screenshots, telemetry, or crash evidence.** The credential itself must not be committed to Git. Implementation must use a salted slow password verifier or an OS/secret-backed equivalent.
5. **Rotation support.** The owner can replace the bootstrap credential later without rebuilding the model or losing training state.
6. **Short-lived authenticated session.** Admin access expires after inactivity and on application restart unless the owner explicitly chooses a future approved persistence design.
7. **Rate limiting / delay after failed attempts.** Repeated failures must not allow unlimited rapid guessing.
8. **Sensitive actions require re-authentication.** Model promotion, rollback, deleting/quarantining training evidence, changing the teacher connector, changing training policy, or rotating credentials require the admin credential again plus an explicit confirmation step.
9. **Local-only by default.** No remote network administration endpoint is created merely because the console exists.

The temporary bootstrap password has been supplied by the owner in conversation and is intended to be rotated later. **The literal password must not be written into this planning file or any repository source.**

## Console identity

Recommended title:

`Forgey Insta:EL-Bot — AI & Training Console`

Recommended persistent visual status line:

`PRIVATE ADMIN / MODEL CONTROL`

The console should be visually distinct from the normal EL Bot UI so an authenticated user cannot mistake it for the ordinary conversion surface.

## Information architecture

### 1. 🧠 Overview

Show the current production intelligence at a glance:

- current generation, e.g. `Forgey Insta:EL-Bot G12`;
- model status: production / candidate / training / rejected / rollback;
- parameter count;
- architecture signature;
- tokenizer version/signature;
- context length;
- model file hash;
- active model load state;
- local inference readiness;
- last successful model validation;
- current conversion share;
- current Qwen teacher dependency rate;
- current easy-word / sentence / round-trip benchmark summaries.

### 2. ⚡ Live AI Status

Real-time but truthful operational telemetry:

- current request state;
- ABC→EL or EL→ABC direction;
- local model inference duration;
- candidate count / beam state if applicable;
- model confidence / uncertainty calibration;
- deterministic validation result;
- whether supporting engines were invoked;
- whether Qwen teacher was eligible;
- whether Qwen teacher was actually called;
- whether the result produced new learning evidence;
- current CPU/RAM use attributable to Forgey Insta where measurable;
- queue lengths for inference/training/validation jobs.

No fake animated activity. Idle means idle.

### 3. 📖 Lexical & Knowledge Foundation

Show authoritative data health:

- Unicode Emoji dataset version;
- dataset-derived RGI emoji count;
- Open English WordNet edition/version;
- lexical lemma/sense counts;
- EL structural token count;
- tokenizer vocabulary count;
- training vocabulary coverage;
- dataset hashes;
- materialization/last-refresh status;
- provenance/licensing notices.

Historical semantic seed counts may be shown only if clearly labeled as internal legacy/seed data, never as the public emoji-universe count.

### 4. 🦙 Qwen Teacher

Show teacher status without exposing raw secrets:

- provider: temporary Ollama connector;
- current teacher model: `qwen2.5vl:7b` while that remains authoritative;
- reachable / unavailable / loading / timed out;
- model-running state;
- last successful lesson time;
- lesson request count;
- accepted lesson count;
- rejected lesson count;
- teacher dependency rate;
- average teacher latency;
- recent failure reasons;
- teacher replacement readiness.

Raw provider prose should not be dumped casually into the console. If a future diagnostic view exposes raw teacher output, it must be an explicit privileged diagnostic mode with redaction and must never imply that raw prose is canonical EL truth.

### 5. 🎓 Learning Evidence

Show what Forgey Insta is learning from:

- deterministic verified examples;
- user-confirmed corrections;
- validated Qwen lessons;
- mature/canonical learned mappings;
- negative/rejected evidence;
- counterexamples;
- ambiguity examples;
- replay-buffer size;
- training-example counts by trust tier;
- provenance coverage;
- duplicate/conflict detection;
- quarantined evidence.

Every learning item needs traceable provenance and trust level.

### 6. 🏋️ Training

Show candidate-training lifecycle:

- current training state;
- candidate generation ID;
- parent production generation;
- dataset snapshot/hash;
- training/validation split identity;
- frozen benchmark identity;
- optimizer and training configuration;
- epoch/step progress;
- train/validation loss;
- checkpoint progress;
- estimated remaining work only when it can be measured honestly;
- training hardware/device;
- stop/cancel state;
- candidate output path/hash after completion.

Training controls should include planning for:

- `Train Candidate`;
- `Pause` where technically safe;
- `Stop Candidate`;
- `Resume` only from a valid checkpoint;
- `Validate Candidate`;
- `Compare to Production`.

The normal app must remain usable while training when architecture/resources permit. If training materially degrades conversion reliability or machine responsiveness, orchestration should defer training instead of pretending background training is free.

### 7. 🧪 Benchmarks & Promotion Gate

Show side-by-side production vs candidate results:

- easy-word accuracy;
- common-sentence translation accuracy;
- ABC→EL score;
- EL→ABC score;
- round-trip score;
- ambiguity handling;
- context/sense accuracy;
- unknown/nonsense rejection;
- structural EL validity;
- semantic-loss metrics;
- teacher dependency;
- inference latency;
- memory footprint;
- protected regression failures;
- adversarial/counterexample results.

A candidate cannot be promoted merely because one aggregate score improves. Protected regressions, structural validity, safety, and required benchmarks remain hard gates.

### 8. 🗃️ Generations & Rollback

Show a model lineage view:

`G0 → G1 → G2 → ... → current production`

For each generation:

- generation ID;
- status;
- created time;
- parent generation;
- parameter count;
- architecture/tokenizer signature;
- dataset hash;
- benchmark report;
- reason promoted/rejected;
- model hash;
- rollback compatibility.

Controls:

- inspect;
- compare;
- mark/quarantine a bad candidate;
- rollback to a previously proven production generation.

Promotion and rollback are sensitive actions and require re-authentication + explicit confirmation.

### 9. 📈 Learning & Independence Analytics

Primary long-term trends:

- `forgey_insta_conversion_share` ↑;
- `qwen_teacher_dependency_rate` ↓;
- validation pass rate ↑;
- user correction rate ↓;
- easy-word reliability ↑;
- context accuracy ↑;
- round-trip accuracy ↑;
- semantic loss ↓;
- lessons collected / accepted / rejected;
- lessons absorbed into promoted generations;
- model-size history;
- generation-to-generation improvement.

Charts must use real measured data only.

### 10. 📜 Audit & Security

Show owner-relevant audit events:

- successful/failed console authentication attempts;
- credential rotation events without logging the credential;
- training started/stopped;
- candidate validation;
- candidate promotion/rejection;
- rollback;
- teacher connector changes;
- training-policy changes;
- evidence quarantine/deletion;
- dataset/version changes.

No passwords, tokens, API keys, raw secret values, or sensitive provider credentials may appear in the audit log.

## Dangerous-action UX

Actions that can affect model truth or production behavior must never be one-click operations.

Recommended pattern:

1. user selects action;
2. console explains exact effect and rollback;
3. user re-enters admin credential;
4. explicit typed confirmation or equivalent high-friction confirmation;
5. action executes;
6. immutable audit record is written;
7. result is verified before UI reports success.

Examples requiring this treatment:

- promote candidate;
- rollback production model;
- delete/quarantine trusted evidence;
- clear learning history;
- rotate admin credential;
- change Qwen teacher/provider;
- change model architecture/training policy;
- disable validation gates.

Validation gates should not be disableable through a casual toggle.

## Secret handling / rotation

The owner-supplied bootstrap credential is temporary.

Implementation requirements:

- never commit the literal credential;
- never package a recoverable plaintext form;
- store only a salted slow verifier or OS-backed secret representation;
- use a fresh random salt;
- use a memory-hard/slow password KDF appropriate to the runtime, preferably Argon2id or scrypt; PBKDF2 is an acceptable fallback only if the platform/runtime constraints require it and parameters are appropriately strong;
- constant-time verifier comparison where applicable;
- credential rotation replaces the verifier and invalidates active admin sessions;
- failed login attempts are rate-limited;
- no password hints containing the secret;
- recovery/reset flow must be separately designed and owner-approved rather than using a hidden backdoor password.

## Hidden access does not equal security

The activation sequence is intentionally obscure only to prevent accidental discovery by ordinary users. A technically capable local user may inspect a packaged desktop app. Therefore the page's protection depends on authentication, privilege gating, safe secret storage, and action re-authentication—not on hiding the route name or gesture.

## Acceptance direction

Phase 6.10 is not PASS until implementation evidence proves at minimum:

1. the 🤖 identity emoji shows no visible hover/cursor/tooltip/click clue;
2. exactly five valid clicks within three seconds reveal authentication and incomplete/expired sequences do nothing visible;
3. no visible normal-user navigation exposes the console;
4. unauthenticated access to the console and privileged IPC/actions is rejected even if the route is discovered directly;
5. the literal bootstrap password is absent from repository source, package resources, logs, screenshots, and generated evidence;
6. valid authentication opens a short-lived admin session;
7. failed attempts are rate-limited;
8. session expiry/restart closes admin access;
9. rotation invalidates the old verifier/session;
10. sensitive model/training actions require re-authentication;
11. status values are sourced from real model/training/teacher data;
12. production/candidate generation and lineage are truthful;
13. benchmarks and analytics use measured data only;
14. Qwen status and teacher activity are truthful;
15. promotion/rollback produce verified audit records;
16. no admin action can bypass the mandatory EL validation/promotion authority merely because the console is authenticated;
17. packaged Windows runtime preserves the same authentication boundary;
18. security tests include direct-route/IPC bypass attempts, not only UI clicking;
19. existing normal EL Bot conversion behavior remains available to non-admin users without exposing admin internals.

## Implementation gate

**Implementation remains paused.** This file locks the hidden-console purpose, exact 🤖 five-click/three-second access sequence, access/security model, information architecture, and sensitive-action behavior only. Runtime/UI/security/model/training changes require a later explicit implementation GO.