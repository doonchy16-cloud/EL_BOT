import regex

from el_bot import CoreEngine
from el_bot.core.engine import ValidationStatus
from el_bot.vocabulary import CANONICAL_SYMBOLS, VocabularyEngine


def test_v4_symbol_set_is_exactly_500_unique_graphemes():
    assert len(CANONICAL_SYMBOLS) == 500
    assert len(set(CANONICAL_SYMBOLS)) == 500
    assert CANONICAL_SYMBOLS[0] == "🔥"
    assert CANONICAL_SYMBOLS[-1] == "📭"


def test_every_v4_symbol_resolves_to_stable_one_based_identity():
    engine = VocabularyEngine()
    for ordinal, symbol in enumerate(CANONICAL_SYMBOLS, start=1):
        record = engine.lookup(symbol)
        assert record is not None
        assert record.symbol == symbol
        assert record.ordinal == ordinal


def test_known_el_sequence_passes_and_user_facing_status_is_emoji_only():
    parsed = CoreEngine().parse("🔥⚙️✅. 101")
    result = VocabularyEngine().resolve(parsed)

    assert result.status is ValidationStatus.PASS
    assert [item.symbol for item in result.resolved] == ["🔥", "⚙️", "✅"]
    assert result.render_el_status() == "✅"
    assert not regex.search(r"\p{L}", result.render_el_status())


def test_unknown_emoji_holds_and_is_shown_without_word_labels():
    parsed = CoreEngine().parse("🔥😀")
    result = VocabularyEngine().resolve(parsed)

    assert result.status is ValidationStatus.HOLD
    assert [token.text for token in result.unknown_emoji] == ["😀"]
    assert result.render_el_status() == "🟡❓😀"
    assert not regex.search(r"\p{L}", result.render_el_status())


def test_letters_fail_before_vocabulary_claims_pass():
    parsed = CoreEngine().parse("🔥abc")
    result = VocabularyEngine().resolve(parsed)

    assert result.status is ValidationStatus.FAIL
    assert result.render_el_status() == "❌🔤"
    assert not regex.search(r"\p{L}", result.render_el_status())


def test_punctuation_numbers_and_layout_do_not_require_vocabulary_entries():
    parsed = CoreEngine().parse("🔥:\n  123 — ✅")
    result = VocabularyEngine().resolve(parsed)

    assert result.status is ValidationStatus.PASS
    assert [item.symbol for item in result.resolved] == ["🔥", "✅"]
    assert result.unknown_emoji == ()


def test_noncanonical_nonemoji_symbol_can_remain_formatting_without_fake_meaning():
    parsed = CoreEngine().parse("🔥 = ✅")
    result = VocabularyEngine().resolve(parsed)

    assert result.status is ValidationStatus.PASS
    assert [item.symbol for item in result.resolved] == ["🔥", "✅"]


def test_reserved_symbol_that_core_classifies_as_symbol_still_resolves_by_exact_authority():
    parsed = CoreEngine().parse("✦")
    result = VocabularyEngine().resolve(parsed)

    assert result.status is ValidationStatus.PASS
    assert result.resolved[0].symbol == "✦"
    assert result.resolved[0].ordinal == 28
