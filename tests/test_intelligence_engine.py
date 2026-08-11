import regex

from el_bot import CoreEngine
from el_bot.core.engine import ValidationStatus
from el_bot.intelligence import IntelligenceEngine
from el_bot.vocabulary import VocabularyEngine


def _interpret(text: str):
    parsed = CoreEngine().parse(text)
    vocabulary = VocabularyEngine().resolve(parsed)
    return IntelligenceEngine().interpret(vocabulary)


def test_explicit_direction_chain_becomes_relationships_without_word_translation():
    result = _interpret("📚➡️🧠➡️💬")

    assert result.status is ValidationStatus.PASS
    assert result.lines[0].el_relationships == ("📚➡️🧠", "🧠➡️💬")
    assert result.render_relationships_el() == "📚➡️🧠  🧠➡️💬"
    assert not regex.search(r"\p{L}", result.render_relationships_el())


def test_status_anchors_are_extracted_in_canonical_order():
    result = _interpret("📗🏭🔵. 🎞️🟡. ☁️🚧.")

    assert [item.symbol for item in result.lines[0].statuses] == ["🔵", "🟡", "🚧"]
    assert result.render_el_status() == "✅🧠"


def test_indentation_and_lines_are_preserved_for_structure():
    result = _interpret("🔥\n  📚➡️🧠\n    ✅")

    assert len(result.lines) == 3
    assert result.lines[0].indentation == ""
    assert result.lines[1].indentation == "  "
    assert result.lines[2].indentation == "    "
    assert result.render_el() == "🔥\n  📚➡️🧠\n    ✅"


def test_unknown_emoji_propagates_hold_and_no_fake_interpretation_pass():
    result = _interpret("🔥😀")

    assert result.status is ValidationStatus.HOLD
    assert result.render_el_status() == "🟡🧠❓"
    assert not result.is_interpretable


def test_letter_failure_is_never_echoed_back_through_el_renderer():
    result = _interpret("🔥abc")

    assert result.status is ValidationStatus.FAIL
    assert result.render_el() == "❌🔤"
    assert result.render_el_status() == "❌🧠"
    assert not regex.search(r"\p{L}", result.render_el())
    assert not regex.search(r"\p{L}", result.render_el_status())


def test_punctuation_is_recorded_without_becoming_fake_vocabulary():
    result = _interpret("🔥, ✅!")

    assert result.lines[0].punctuation == (",", "!")
    assert [item.symbol for item in result.lines[0].symbols] == ["🔥", "✅"]
