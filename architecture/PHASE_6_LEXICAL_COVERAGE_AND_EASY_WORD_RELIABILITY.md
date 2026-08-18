# EL Bot — Phase 6 Lexical Coverage & Easy-Word Reliability

**Status:** 🔁 SUPERSEDED DURING PHASE 6 IMPLEMENTATION

This file records the original Phase-6 lexical-only direction. The Unicode Emoji 17.0 and Open English WordNet work implemented from this plan remains active as EL Bot's fast deterministic front end.

The owner subsequently authorized a stronger Phase-6 architecture: a from-scratch, approximately one-million-parameter EL specialist that continuously learns from validated `qwen2.5vl:7b` teacher lessons.

Current Phase-6 authority is:

`architecture/PHASE_6_EL_STUDENT_1M_AND_QWEN_TEACHER.md`

Important retained rules from this earlier plan:

- the fixed `501` public/current vocabulary ceiling is removed;
- the actual Unicode emoji count is dataset-derived;
- Open English WordNet remains the broad lexical front end;
- naive substring root matching remains forbidden;
- raw third-party dictionary content is not automatic canonical truth;
- Qwen output must still pass deterministic EL construction and validation.

Important superseded rule:

- `HOLD → provider never` is no longer universal. Phase 6 now permits **semantic HOLD** to enter the student/Qwen teacher path while system/runtime/security/parser HOLD remains provider-free.
