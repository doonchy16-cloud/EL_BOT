"""Engine 3: deterministic EL structure and relationship interpretation.

This engine reads canonical Emoji Language structure without translating it to
English. It identifies lines, indentation, canonical symbol order, status
anchors, and explicit directional relationships. It does not invent unstated
semantic relationships.
"""

from __future__ import annotations

from dataclasses import dataclass

from el_bot.core.engine import Token, TokenKind, ValidationStatus
from el_bot.vocabulary import SymbolAuthority, VocabularyEngine, VocabularyResult


_RELATION_OPERATORS = frozenset({"➡️", "⬅️", "↔️"})
_STATUS_SYMBOLS = frozenset(
    {
        "⚪",
        "🔵",
        "🟢",
        "🟡",
        "🔴",
        "🟣",
        "✅",
        "❌",
        "🚧",
        "⚠️",
        "🛑",
        "⛔",
        "📴",
    }
)


@dataclass(frozen=True, slots=True)
class Relationship:
    left: SymbolAuthority
    operator: SymbolAuthority
    right: SymbolAuthority

    @property
    def el(self) -> str:
        return f"{self.left.symbol}{self.operator.symbol}{self.right.symbol}"


@dataclass(frozen=True, slots=True)
class InterpretedLine:
    raw: str
    indentation: str
    symbols: tuple[SymbolAuthority, ...]
    statuses: tuple[SymbolAuthority, ...]
    relationships: tuple[Relationship, ...]
    punctuation: tuple[str, ...]

    @property
    def el_relationships(self) -> tuple[str, ...]:
        return tuple(item.el for item in self.relationships)


@dataclass(frozen=True, slots=True)
class InterpretationResult:
    source: VocabularyResult
    lines: tuple[InterpretedLine, ...]
    status: ValidationStatus

    @property
    def is_interpretable(self) -> bool:
        return self.status is ValidationStatus.PASS

    def render_el_status(self) -> str:
        """Return an EL-safe interpretation status with no alphabetic output."""

        if self.status is ValidationStatus.FAIL:
            return "❌🧠"
        if self.status is ValidationStatus.HOLD:
            return "🟡🧠❓"
        return "✅🧠"

    def render_el(self) -> str:
        """Return source EL only when it is letter-free; never echo failed letters."""

        if self.source.source.letter_tokens:
            return "❌🔤"
        return self.source.source.source

    def render_relationships_el(self) -> str:
        """Render only explicit directional relationships in emoji-native form."""

        rendered_lines: list[str] = []
        for line in self.lines:
            if line.relationships:
                rendered_lines.append(line.indentation + "  ".join(line.el_relationships))
        return "\n".join(rendered_lines)


class IntelligenceEngine:
    """Interpret only explicit EL structure backed by canonical vocabulary."""

    def interpret(self, vocabulary: VocabularyResult) -> InterpretationResult:
        if not isinstance(vocabulary, VocabularyResult):
            raise TypeError("vocabulary must be a VocabularyResult")

        if vocabulary.status is ValidationStatus.FAIL:
            return InterpretationResult(
                source=vocabulary,
                lines=(),
                status=ValidationStatus.FAIL,
            )

        lines = tuple(self._build_lines(vocabulary))
        status = (
            ValidationStatus.HOLD
            if vocabulary.status is ValidationStatus.HOLD
            else ValidationStatus.PASS
        )
        return InterpretationResult(source=vocabulary, lines=lines, status=status)

    def _build_lines(self, vocabulary: VocabularyResult):
        current: list[Token] = []
        for token in vocabulary.source.tokens:
            if token.kind is TokenKind.WHITESPACE and ("\n" in token.text or "\r" in token.text):
                yield self._interpret_line(current)
                current = []
            else:
                current.append(token)
        yield self._interpret_line(current)

    @staticmethod
    def _interpret_line(tokens: list[Token]) -> InterpretedLine:
        raw = "".join(token.text for token in tokens)
        indentation_parts: list[str] = []
        for token in tokens:
            if token.kind is TokenKind.WHITESPACE:
                indentation_parts.append(token.text)
            else:
                break
        indentation = "".join(indentation_parts)

        symbols: list[SymbolAuthority] = []
        punctuation: list[str] = []
        for token in tokens:
            authority = VocabularyEngine.lookup(token.text)
            if authority is not None:
                symbols.append(authority)
            elif token.kind is TokenKind.PUNCTUATION:
                punctuation.append(token.text)

        statuses = tuple(item for item in symbols if item.symbol in _STATUS_SYMBOLS)

        relationships: list[Relationship] = []
        for index, item in enumerate(symbols):
            if item.symbol not in _RELATION_OPERATORS:
                continue
            if index == 0 or index + 1 >= len(symbols):
                continue
            left = symbols[index - 1]
            right = symbols[index + 1]
            if left.symbol in _RELATION_OPERATORS or right.symbol in _RELATION_OPERATORS:
                continue
            relationships.append(Relationship(left=left, operator=item, right=right))

        return InterpretedLine(
            raw=raw,
            indentation=indentation,
            symbols=tuple(symbols),
            statuses=statuses,
            relationships=tuple(relationships),
            punctuation=tuple(punctuation),
        )
