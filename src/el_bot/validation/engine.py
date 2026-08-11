"""Engine 4: evidence-backed EL output validation and safe release gate.

This is the final deterministic guard before any user-facing EL text is
released. It prevents accidental alphabetic output, rejects unsupported emoji
as verified meaning, and propagates upstream HOLD/FAIL evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from el_bot.core.engine import CoreEngine, ParseResult, ValidationStatus
from el_bot.intelligence import InterpretationResult
from el_bot.vocabulary import VocabularyEngine, VocabularyResult


@dataclass(frozen=True, slots=True)
class ValidationReport:
    source: InterpretationResult
    proposed_output: str
    output_surface: ParseResult
    output_vocabulary: VocabularyResult
    status: ValidationStatus

    @property
    def releasable(self) -> bool:
        return self.status is ValidationStatus.PASS

    def render_el_status(self) -> str:
        if self.status is ValidationStatus.FAIL:
            return "❌🧾"
        if self.status is ValidationStatus.HOLD:
            return "🟡🧾❓"
        return "✅🧾"

    def safe_output(self) -> str:
        """Release proposed text only when fully verified; otherwise emit EL status."""

        if self.releasable:
            return self.proposed_output
        return self.render_el_status()


class ValidationEngine:
    """Gate EL output using upstream evidence plus fresh output validation."""

    def validate(self, source: InterpretationResult, proposed_output: str) -> ValidationReport:
        if not isinstance(source, InterpretationResult):
            raise TypeError("source must be an InterpretationResult")
        if not isinstance(proposed_output, str):
            raise TypeError("proposed_output must be a string")

        output_surface = CoreEngine().parse(proposed_output, el_mode=True)
        output_vocabulary = VocabularyEngine().resolve(output_surface)

        if (
            source.status is ValidationStatus.FAIL
            or output_surface.status is ValidationStatus.FAIL
        ):
            status = ValidationStatus.FAIL
        elif (
            source.status is ValidationStatus.HOLD
            or output_vocabulary.status is ValidationStatus.HOLD
        ):
            status = ValidationStatus.HOLD
        else:
            status = ValidationStatus.PASS

        return ValidationReport(
            source=source,
            proposed_output=proposed_output,
            output_surface=output_surface,
            output_vocabulary=output_vocabulary,
            status=status,
        )
