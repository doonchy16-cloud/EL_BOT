import regex

from el_bot import CoreEngine
from el_bot.core.engine import ValidationStatus
from el_bot.intelligence import IntelligenceEngine
from el_bot.validation import ValidationEngine
from el_bot.vocabulary import VocabularyEngine


def _source(text: str):
    parsed = CoreEngine().parse(text)
    vocabulary = VocabularyEngine().resolve(parsed)
    return IntelligenceEngine().interpret(vocabulary)


def test_valid_el_output_is_released_unchanged():
    report = ValidationEngine().validate(_source("🔥✅"), "📗🔵. ✅.")

    assert report.status is ValidationStatus.PASS
    assert report.releasable
    assert report.safe_output() == "📗🔵. ✅."
    assert report.render_el_status() == "✅🧾"


def test_alphabetic_output_is_blocked_instead_of_leaking_words():
    report = ValidationEngine().validate(_source("🔥✅"), "got it")

    assert report.status is ValidationStatus.FAIL
    assert not report.releasable
    assert report.safe_output() == "❌🧾"
    assert not regex.search(r"\p{L}", report.safe_output())


def test_unknown_emoji_is_hold_and_is_not_released_as_verified_language():
    report = ValidationEngine().validate(_source("🔥✅"), "🔥😀")

    assert report.status is ValidationStatus.HOLD
    assert not report.releasable
    assert report.safe_output() == "🟡🧾❓"


def test_upstream_hold_cannot_be_upgraded_by_valid_looking_output():
    report = ValidationEngine().validate(_source("🔥😀"), "✅")

    assert report.status is ValidationStatus.HOLD
    assert report.safe_output() == "🟡🧾❓"


def test_upstream_fail_cannot_be_hidden_by_valid_looking_output():
    report = ValidationEngine().validate(_source("🔥abc"), "✅")

    assert report.status is ValidationStatus.FAIL
    assert report.safe_output() == "❌🧾"


def test_punctuation_numbers_and_indentation_are_allowed_in_released_el():
    proposed = "🔥: 101.\n  ✅!"
    report = ValidationEngine().validate(_source("🔥✅"), proposed)

    assert report.status is ValidationStatus.PASS
    assert report.safe_output() == proposed
