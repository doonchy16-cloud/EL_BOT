"""Engine 1: deterministic Emoji Language core parsing and surface validation.

This layer deliberately does not assign semantic meanings. It is responsible for:
- preserving Unicode grapheme clusters (including ZWJ emoji and keycaps),
- classifying surface tokens,
- enforcing the EL rule that alphabetic letters are forbidden while EL mode is active,
- preserving whitespace/indentation and punctuation exactly,
- producing evidence suitable for later vocabulary and interpretation engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

import regex


_GRAPHEME_RE = regex.compile(r"\X")
_LETTER_RE = regex.compile(r"\p{L}")
_PUNCT_RE = regex.compile(r"^\p{P}+$")
_EMOJI_RE = regex.compile(r"\p{Emoji}")
_KEYCAP_RE = regex.compile(r"^[0-9#*]\ufe0f?\u20e3$")


class ValidationStatus(str, Enum):
    """Evidence-backed validation state for the Core Engine."""

    PASS = "pass"
    HOLD = "hold"
    FAIL = "fail"


class TokenKind(str, Enum):
    """Surface-level token classes; semantic meaning is intentionally excluded."""

    EMOJI = "emoji"
    PUNCTUATION = "punctuation"
    NUMBER = "number"
    WHITESPACE = "whitespace"
    LETTER = "letter"
    SYMBOL = "symbol"


@dataclass(frozen=True, slots=True)
class Token:
    text: str
    kind: TokenKind
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class ParseResult:
    source: str
    tokens: tuple[Token, ...]
    status: ValidationStatus
    el_mode: bool
    letter_tokens: tuple[Token, ...]

    @property
    def is_valid_el_surface(self) -> bool:
        """True only when EL mode is active and no alphabetic letters were found."""

        return self.el_mode and self.status is ValidationStatus.PASS

    @property
    def reconstructed(self) -> str:
        """Losslessly rebuild the original input from emitted tokens."""

        return "".join(token.text for token in self.tokens)


class CoreEngine:
    """Tokenize and validate the surface grammar of Emoji Language (EL)."""

    def parse(self, text: str, *, el_mode: bool = True) -> ParseResult:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        tokens = tuple(self._tokenize(text))
        letter_tokens = tuple(token for token in tokens if token.kind is TokenKind.LETTER)

        if not el_mode:
            status = ValidationStatus.HOLD
        elif letter_tokens:
            status = ValidationStatus.FAIL
        else:
            status = ValidationStatus.PASS

        return ParseResult(
            source=text,
            tokens=tokens,
            status=status,
            el_mode=el_mode,
            letter_tokens=letter_tokens,
        )

    def _tokenize(self, text: str) -> Iterable[Token]:
        for match in _GRAPHEME_RE.finditer(text):
            cluster = match.group(0)
            yield Token(
                text=cluster,
                kind=self._classify(cluster),
                start=match.start(),
                end=match.end(),
            )

    @staticmethod
    def _classify(cluster: str) -> TokenKind:
        if cluster.isspace():
            return TokenKind.WHITESPACE

        # Any Unicode alphabetic letter is a confirmed EL-mode surface violation,
        # even when it appears inside an otherwise unusual grapheme cluster.
        if _LETTER_RE.search(cluster):
            return TokenKind.LETTER

        # Keycap emoji include characters that would otherwise resemble numbers or
        # punctuation, so they must be recognized before those simpler categories.
        if _KEYCAP_RE.fullmatch(cluster):
            return TokenKind.EMOJI

        if cluster.isdecimal():
            return TokenKind.NUMBER

        if _PUNCT_RE.fullmatch(cluster):
            return TokenKind.PUNCTUATION

        # Unicode's Emoji property covers pictographs, arrows, dingbats, flags,
        # and other canonical emoji code points used by EL.
        if _EMOJI_RE.search(cluster):
            return TokenKind.EMOJI

        return TokenKind.SYMBOL
