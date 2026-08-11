# EL Bot

EL Bot is a deterministic reader/interpreter for **Emoji Language (EL)**.

## Locked EL surface rule

When EL mode is active:

- Emoji are allowed.
- Normal punctuation is allowed.
- Whitespace, line breaks, and indentation are allowed.
- Numbers are allowed.
- Alphabetic letters are not allowed in EL-facing output.

Developer source code, tests, commit messages, and internal documentation may use ordinary programming-language words. **Anything rendered to an EL-mode user must not contain alphabetic words.**

The bot must not invent meanings for unknown symbols.

## Engine 1 — Core Engine

Status: implemented in `src/el_bot/core/engine.py`.

Responsibilities:

1. Split input into Unicode grapheme clusters so ZWJ emoji, variation selectors, and keycaps stay intact.
2. Preserve the input losslessly.
3. Classify surface tokens as emoji, punctuation, number, whitespace, letter, or symbol.
4. Enforce the EL no-letters rule when EL mode is active.
5. Produce evidence for later engines without assigning semantic meaning.

Validation semantics:

- `PASS`: EL mode is active and the Core Engine found no alphabetic letters.
- `FAIL`: EL mode is active and alphabetic letters were found.
- `HOLD`: EL mode is not active; the engine does not claim EL validity.

A Core Engine PASS only proves the surface-language rule. It does **not** prove that every emoji is canonical or that an interpretation is correct.

## Engine 2 — Vocabulary / Authority Engine

Status: implemented in `src/el_bot/vocabulary/authority.py`.

Responsibilities:

1. Load the exact locked V4 symbol stream as 500 unique Unicode graphemes.
2. Resolve each canonical symbol to a stable one-based authority identity.
3. Preserve punctuation, layout, numbers, and nonsemantic formatting without inventing meanings.
4. Put interpretation on `HOLD` when a noncanonical emoji appears.
5. Never expose English meaning labels in EL-facing status output.

EL-facing status forms:

- canonical vocabulary pass → `✅`
- unknown emoji / unresolved vocabulary → `🟡❓<unknown emoji>`
- alphabetic-letter violation → `❌🔤`

## Engine 3 — Intelligence / Interpretation Engine

Status: implemented in `src/el_bot/intelligence/interpreter.py`.

Responsibilities:

1. Read canonical symbol order without translating the message to English.
2. Preserve line structure and indentation.
3. Extract canonical status anchors such as current, hold, fail, and verified symbols by their locked emoji identity.
4. Read explicit `➡️`, `⬅️`, and `↔️` relationships as deterministic symbol-to-symbol relationships.
5. Refuse to upgrade unknown vocabulary from `HOLD` to interpreted `PASS`.
6. Never echo alphabetic input through its EL renderer.

## Engine 4 — Validation Engine

Status: implemented in `src/el_bot/validation/engine.py`.

Responsibilities:

1. Re-parse every proposed user-facing response before release.
2. Block accidental alphabetic words from EL output.
3. Hold noncanonical emoji instead of pretending they are verified vocabulary.
4. Propagate upstream HOLD/FAIL evidence.
5. Release the proposed EL response only after evidence-backed PASS.

EL-facing gate output:

- release pass → `✅🧾`
- hold → `🟡🧾❓`
- fail → `❌🧾`

This fixes the runtime leakage problem: ordinary words may exist in developer code and documentation, but they cannot pass the EL user-facing release gate while EL mode is active.

## Planned next engine

**Engine 5 — Session / Context Engine**

It will preserve EL conversation context, activation state, message history, and bounded interpretation context without weakening the locked output gate.

## Development

Windows: double-click `run_tests.cmd`.

Manual:

```bash
python -m pip install -e ".[test]"
pytest
```

GitHub-hosted CI is optional evidence only. If account billing prevents GitHub Actions from starting, local test evidence remains separate and the CI state must not be reported as a code failure.
