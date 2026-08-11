from el_bot.core.engine import CoreEngine, TokenKind, ValidationStatus


def test_emoji_keycap_and_arrow_are_preserved_as_graphemes() -> None:
    result = CoreEngine().parse("🔥➡️1️⃣")

    assert result.status is ValidationStatus.PASS
    assert result.reconstructed == "🔥➡️1️⃣"
    assert [token.text for token in result.tokens] == ["🔥", "➡️", "1️⃣"]
    assert [token.kind for token in result.tokens] == [
        TokenKind.EMOJI,
        TokenKind.EMOJI,
        TokenKind.EMOJI,
    ]


def test_normal_punctuation_whitespace_and_indentation_are_allowed() -> None:
    source = "🔥.\n  ✅!"
    result = CoreEngine().parse(source)

    assert result.status is ValidationStatus.PASS
    assert result.is_valid_el_surface
    assert result.reconstructed == source
    assert any(token.kind is TokenKind.PUNCTUATION for token in result.tokens)
    assert any(token.kind is TokenKind.WHITESPACE for token in result.tokens)


def test_letters_are_rejected_when_el_is_active() -> None:
    result = CoreEngine().parse("🔥GO✅")

    assert result.status is ValidationStatus.FAIL
    assert not result.is_valid_el_surface
    assert "".join(token.text for token in result.letter_tokens) == "GO"


def test_unicode_letters_are_rejected_not_only_ascii() -> None:
    result = CoreEngine().parse("🔥éאב✅")

    assert result.status is ValidationStatus.FAIL
    assert result.letter_tokens


def test_zwj_emoji_stays_one_token() -> None:
    family = "👨‍👩‍👧‍👦"
    result = CoreEngine().parse(family)

    assert result.status is ValidationStatus.PASS
    assert len(result.tokens) == 1
    assert result.tokens[0].kind is TokenKind.EMOJI
    assert result.tokens[0].text == family


def test_plain_numbers_are_allowed_but_are_not_keycap_emoji() -> None:
    result = CoreEngine().parse("101")

    assert result.status is ValidationStatus.PASS
    assert all(token.kind is TokenKind.NUMBER for token in result.tokens)


def test_non_el_mode_does_not_claim_el_pass() -> None:
    result = CoreEngine().parse("hello", el_mode=False)

    assert result.status is ValidationStatus.HOLD
    assert not result.is_valid_el_surface
