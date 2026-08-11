"""Engine 2: canonical Emoji Language V4 vocabulary authority.

The runtime-facing contract is emoji-native: this engine does not emit English
meaning labels to EL users. It resolves symbols against the locked 500-symbol
V4 authority, preserves canonical ordinal identity, and refuses to guess when
an unknown emoji is encountered.
"""

from __future__ import annotations

from dataclasses import dataclass

from el_bot.core.engine import ParseResult, Token, TokenKind, ValidationStatus


_CANONICAL_SYMBOL_STREAM = "🔥⚙️🖥️🤖🧠📡🧪🧯🔌🧾🛡️💾🚀🔒✅🪪🖱️📸👁️📗❌🔍🔐🏁📚🕵️🔁✦⚪🔵🟢🟡🔴🟣🎛️🎞️🔔🧩🗃️🧱🧰🌐📜📋📎🧷🧹🧭⏱️📈🧬🧵⭐🏆💎👑🎯🥇💡🛠️🔧🔨🏗️🧑‍💻🧑‍🏫🧑‍🔬🧑‍⚖️🧿🛰️📶🔗⛓️🪢🕸️🚦🚧⚠️‼️❗❓⁉️🆘🛑⛔📴🟰➕➖✏️📝📄📑🗂️📂🗄️🗑️🕰️🆕♻️🔄⬆️⬇️📥📤⬅️➡️🔀🔃⏸️▶️⏹️⏭️⏮️⏳⌛🕒📅🗓️🧮📊📉🎚️🪜🧲💭🗣️💬📨📩✉️📣📢🔕🗯️🎙️🔊🔇🎥🖼️🎨🪄✨🌟💫🌈🎭🖌️📐📏🏛️🗺️🌳🌱🌿🌲🔑🗝️🛂🧑‍🚒🩹❤️‍🩹🪫🔋⚡🐌🧊🌡️💻📱🖨️⌨️🎮🕹️🥽🎧☁️🖧🤝🫱🏻‍🫲🏼🧑‍🤝‍🧑👥👤🧑‍💼🏢🏠🏭🏦💰💵🛒💳📦🎁🚚🧳🚪🛫🛬🎉🥳💥💪🧨☢️🏷️#️⃣🆔🔢🔤🔣🧼🪣🧺📬🚥🔘⚫🟤🩶🩵🩷💜🖤🤍🔶🔷🔸🔹♦️◼️◻️🏅🎖️🥈🥉🎗️🎟️🎫🎬🎤🎼🎵🎶🎹🎸🥁🎻🎺🎷🪗💯💢👍👎👌✌️🤞🤟🤘🤙👈👉👆👇☝️✋🤚🖐️🖖👋👏🙌🫶👐🤲🙏✍️🫂🙋🙆🙅🤷🤦🧑‍🎨🧑‍🔧🧑‍🏭🧑‍🚀🧑‍⚕️🧑‍🌾🧑‍🍳🧑‍🎓🧑‍🎤🧑‍✈️👨‍👩‍👧‍👦👪🦾🦿💼🎓🏫🏥🏪🏬🏨🏡🏘️🏟️🏰🏯🏤🏣💴💶💷🪙💹🏧🪛🔩🪚⚒️⛏️🪓🪤🖲️💽💿📀📼📷📹📺📻📞☎️📟📠🗒️📒📓📔📕📖📘📙📰🗞️📃📇📁🔖📌📍✂️🖇️🖊️🖋️🖍️🔬🔭⚗️🧫🩻🩺💊💉🩸🩼🦽🦼🔓🔏☑️✔️✖️❎❕❔🚨♨️🆗🆒🆙🆓🆖🆚⏯️⏺️⏏️⏩⏪🔂↩️↪️↔️↕️↖️↗️↘️↙️⤴️⤵️🔼🔽🟥🟧🟨🟩🟦🟪🟫⬛⬜🔲🔳▪️▫️◾◽🌍🌎🌏🌞🌝🌚🌙☀️🌤️⛅🌥️🌦️🌧️⛈️🌩️🌨️❄️☃️⛄🌬️💨🌪️🌫️🌊💧💦☔🌂🌋🏔️⛰️🏕️🏖️🏜️🏝️🏞️🚗🚙🚌🚎🏎️🚓🚑🚒🚐🛻🚛🚜🏍️🛵🚲🛴🛹🛼🚁✈️🛩️🚂🚆🚇🚊🚉🚢⛵🛥️🚤🛳️⛽🚏🛣️🛤️👾🎲♟️🃏🎰📧📮📪📫📭"

# Kept as a tuple literal derived from the locked V4 grapheme order. The package
# already depends on `regex` for Unicode grapheme handling, so we use the same
# segmentation rule as Core Engine and validate the invariant at import time.
import regex

CANONICAL_SYMBOLS: tuple[str, ...] = tuple(regex.findall(r"\X", _CANONICAL_SYMBOL_STREAM))

if len(CANONICAL_SYMBOLS) != 500 or len(set(CANONICAL_SYMBOLS)) != 500:
    raise RuntimeError("EL V4 authority invariant violated")

_CANONICAL_ORDINAL = {symbol: index for index, symbol in enumerate(CANONICAL_SYMBOLS, start=1)}


@dataclass(frozen=True, slots=True)
class SymbolAuthority:
    """Canonical identity for one V4 symbol, without English runtime meaning text."""

    symbol: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class VocabularyResult:
    """Evidence from resolving a Core Engine parse against V4 authority."""

    source: ParseResult
    resolved: tuple[SymbolAuthority, ...]
    unknown_emoji: tuple[Token, ...]
    status: ValidationStatus

    @property
    def is_fully_canonical(self) -> bool:
        return self.status is ValidationStatus.PASS

    def render_el_status(self) -> str:
        """Return an EL-mode-safe status containing no alphabetic words."""

        if self.status is ValidationStatus.FAIL:
            return "❌🔤"
        if self.status is ValidationStatus.HOLD:
            if self.unknown_emoji:
                return "🟡❓" + "".join(token.text for token in self.unknown_emoji)
            return "🟡❓"
        return "✅"


class VocabularyEngine:
    """Resolve EL symbols to locked V4 identity and reject semantic guessing."""

    def resolve(self, parsed: ParseResult) -> VocabularyResult:
        if not isinstance(parsed, ParseResult):
            raise TypeError("parsed must be a ParseResult")

        resolved: list[SymbolAuthority] = []
        unknown_emoji: list[Token] = []

        for token in parsed.tokens:
            ordinal = _CANONICAL_ORDINAL.get(token.text)
            if ordinal is not None:
                resolved.append(SymbolAuthority(symbol=token.text, ordinal=ordinal))
            elif token.kind is TokenKind.EMOJI:
                # Unknown emoji are not silently assigned a meaning.
                unknown_emoji.append(token)

        if parsed.status is ValidationStatus.FAIL:
            status = ValidationStatus.FAIL
        elif parsed.status is ValidationStatus.HOLD or unknown_emoji:
            status = ValidationStatus.HOLD
        else:
            status = ValidationStatus.PASS

        return VocabularyResult(
            source=parsed,
            resolved=tuple(resolved),
            unknown_emoji=tuple(unknown_emoji),
            status=status,
        )

    @staticmethod
    def lookup(symbol: str) -> SymbolAuthority | None:
        """Resolve one exact grapheme to its V4 identity, or return None."""

        ordinal = _CANONICAL_ORDINAL.get(symbol)
        if ordinal is None:
            return None
        return SymbolAuthority(symbol=symbol, ordinal=ordinal)
