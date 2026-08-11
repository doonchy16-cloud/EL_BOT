# EL Bot

EL Bot is a deterministic reader/interpreter for **Emoji Language (EL)**.

## Locked EL surface rule

When EL mode is active:

- Emoji are allowed.
- Normal punctuation is allowed.
- Whitespace, line breaks, and indentation are allowed.
- Numbers are allowed.
- Alphabetic letters are not allowed.

The bot must not invent meanings for unknown symbols. Meaning resolution belongs to the canonical EL vocabulary/authority layer, not the Core Engine.

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

A Core Engine PASS only proves the surface-language rule. It does **not** prove that every emoji is canonical or that an interpretation is correct. Those checks belong to later engines.

## Planned next engine

**Engine 2 — Vocabulary / Authority Engine**

It will resolve each canonical EL symbol to its locked primary meaning, distinguish known from unknown symbols, and refuse to guess when vocabulary evidence is missing.

## Development

```bash
python -m pip install -e ".[test]"
pytest
```
