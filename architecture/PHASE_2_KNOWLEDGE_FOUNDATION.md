# EL Bot — Phase 2 Knowledge Foundation

**Status:** 🟡 IMPLEMENTATION IN PROGRESS

**Authority date:** 2026-08-12

Phase 2 implements only the safe substrate required for the forever-expanding Emoji Language. It does **not** wire AI fallback, automatic learning, candidate search, graduation, generalization, or vocabulary mutation.

## Source-present Phase-2 engines

| Target ID | Runtime | Engine | Phase-2 ownership |
|---|---:|---|---|
| N01 | 🌐 | Emoji Universe Engine | finite investigable emoji-unit inventory and Unicode emoji-test ingestion |
| N05 | 📊 | Evidence & Confidence Engine | positive/negative/ambiguous evidence aggregation |
| N10 | 🧿 | Knowledge Integrity Engine | contradiction/poisoning/premature-maturity detection |
| N15 | 🧷 | Emoji Canonicalization Engine | stable Unicode/grapheme identity normalization |
| N17 | 📜 | Provenance Ledger Engine | append-only origin and validation lineage |
| N19 | 🗃️ | Knowledge Versioning & Rollback Engine | snapshot lineage, hashing, persistence, rollback |

These six bring source-present target engines from **24 to 30**, leaving 14 target engines planned-only.

## Locked boundaries

- 📚501 is unchanged and remains canonical vocabulary authority.
- 🌐 is investigable universe authority, not semantic/canonical authority.
- 🧷 normalizes identity but never assigns meaning.
- 📜 records origin but never promotes knowledge.
- 📊 aggregates evidence but never decides maturity.
- 🧿 can PASS/HOLD/FAIL a knowledge claim but cannot mutate it.
- 🗃️ versions snapshots but cannot decide which knowledge is valid.
- No Phase-2 engine may import/call Ollama, Qwen, Forgey, Connector, or Forgey Orchestration.
- No automatic learning write path is enabled in Phase 2.

## Emoji Universe truthfulness rule

The built-in 🌐 inventory is a **broad assigned-symbol investigable superset** plus all current canonical EL symbols. It is deliberately marked `rgi_complete=False`.

For an exact Unicode RGI inventory, 🌐 provides `from_emoji_test(source)`, which accepts the official Unicode `emoji-test.txt` format and includes only `component` + `fully-qualified` rows. When loaded this way, the snapshot is marked `rgi_complete=True` and retains the Unicode version declared by the file.

Phase 2 therefore supports the complete-data contract without falsely claiming that the built-in fallback inventory is already the official RGI dataset.

## Knowledge write prerequisites

Future knowledge mutation must have, at minimum:

1. 📜 provenance;
2. 📊 evidence;
3. 🧿 integrity assessment;
4. 🎓 graduation decision (Phase 4, not implemented yet);
5. 🗃️ versioned commit.

Until 🎓 exists and the later learning pipeline is explicitly authorized, Phase 2 engines are foundation/readiness components only.

## Phase-2 PASS gate

- six source files exist and import using Python 3.12;
- 🧷 handles VS presentation/keycap/ZWJ cases deterministically;
- 🌐 built-in inventory is larger than 📚501 and covers all 501 canonical symbols;
- 🌐 official `emoji-test.txt` parser distinguishes RGI rows from unqualified rows;
- 📜 rejects duplicate IDs and provider provenance without provider/model identity;
- 📊 records positive and negative evidence with deterministic confidence;
- 🗃️ hashes snapshots, persists atomically, restores lineage, and rollback creates a new version rather than rewriting history;
- 🧿 blocks missing provenance, negative-dominated evidence, premature canonical maturity, and canonical conflicts;
- 📚501 remains unchanged;
- all Phase-2 sources remain provider-free;
- Phase-1 architecture gate remains green;
- existing full regression CI remains green.
