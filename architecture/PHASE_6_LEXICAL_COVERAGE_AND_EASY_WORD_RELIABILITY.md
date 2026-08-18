# EL Bot — Phase 6 Lexical Coverage & Easy-Word Reliability

**Status:** 🟡 IMPLEMENTATION IN PROGRESS

Phase 6 fixes ordinary-word failures by expanding lexical coverage inside the existing **📚 Vocabulary** authority. It does **not** create engine #45 and it does not move semantic logic into Electron `main.js`.

## Owner-locked product direction

- Remove the old fixed **501** vocabulary ceiling as the current/public emoji authority.
- Keep the historical semantic seed only as a stable compatibility layer for existing meanings/control symbols.
- Treat the actual official Unicode emoji dataset as the current emoji-symbol authority; the count is derived from the loaded dataset rather than hard-coded.
- Maximize practical English lexical coverage rather than stopping at an arbitrary 1,000/5,000/10,000-word target.
- Preserve deterministic-first translation and the Phase-4 FAIL-only provider boundary.

## Lexical resolution order

```text
incoming word / phrase
        ↓
📖 exact lexical/phrase match
        ↓ if unresolved
🔤 lemma + inflection resolution
        ↓ if unresolved
🧭 contextual sense selection
        ↓ if unresolved
🧩 safe morphology / compound semantics
        ↓ if unresolved
🗺️ synonym + hypernym/taxonomy traversal
        ↓
📊 semantic-loss scoring + ambiguity check
        ↓
resolved candidate → existing 🏆 / 🧾 validation
        │
        ├─ close sense tie → HOLD / unresolved
        └─ no resolution → existing Phase-3 semantic rescue
                               ↓ if genuine FAIL only
                            ✦ → 🔌 → temporary Qwen
```

Naive substring containment is forbidden as a semantic root algorithm. A word such as `scarcity` must never become `car` merely because its spelling contains that sequence.

## Emoji authority

`data/unicode/emoji-test.txt` is materialized from the official Unicode Emoji dataset. `🌐 Emoji Universe` and `📚 Vocabulary` must report the count derived from that file. A broad assigned-symbol scan may exist only as an explicit offline fallback and may not claim to be the complete current Unicode emoji inventory.

The historical semantic seed remains available under `SEMANTIC_BASE_SYMBOLS` so existing meanings and grammar contracts remain stable. Its length is not a product vocabulary limit and must not be presented to the user as "the number of emojis EL Bot knows."

## English lexical authority

Phase 6 materializes Open English WordNet 2025 into `data/oewn/` and uses it for:

- lemma and inflection lookup;
- multiple word senses;
- synonyms;
- noun/verb/adjective/adverb coverage;
- hypernym traversal;
- multi-word lexical entries;
- context-aware ranking and explicit semantic-loss scoring.

The generated `data/` tree is ignored by Git source authority but is materialized before source tests/launch and is included in Windows packaging so the shipped app can use the dictionary offline.

## Safety rules

- Dictionary and taxonomy resolution are provider-free.
- PASS and HOLD remain zero-provider paths.
- Qwen remains eligible only after genuine deterministic FAIL under the existing Phase-4 rules.
- A close lexical sense tie must not be guessed; it remains unresolved/HOLD for later context or deeper deterministic processing.
- Truly unknown synthetic tokens remain unresolved rather than receiving fabricated meanings.
- Word length, UTF-8 byte count, hashes, or arbitrary structural vectors are not semantic translations.
- Raw third-party dictionary text does not automatically become canonical learned knowledge.

## Reliability gate

Phase 6 is not PASS until CI proves, on one exact final `main` SHA:

1. Phase 1–5 gates remain green.
2. Diagnostics remains 44/44.
3. Official Unicode emoji data is materialized and the runtime emoji count matches it exactly.
4. Open English WordNet 2025 is available with a six-figure lexical index.
5. Easy direct words and common multi-word terms resolve to expected emoji.
6. Inflection/lemma cases resolve consistently.
7. Ambiguous or synthetic nonsense input does not silently acquire a fabricated meaning.
8. `easy_word_resolution_rate` meets the locked regression threshold and is reported as measured evidence.
9. Normal PASS/HOLD translation remains provider-free.
10. Windows packages contain the materialized lexical/emoji data and the packaged application passes a real runtime smoke test.
11. Phase-6 authority is locked to `PASS` and the exact final SHA succeeds in GitHub Actions.

## Third-party data attribution

The build uses Unicode emoji data and Open English WordNet data under their respective upstream terms. The release must retain applicable attribution/license files and identify the upstream data editions used. Phase 6 does not claim ownership of those datasets.
