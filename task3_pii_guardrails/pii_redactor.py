
import re
from collections.abc import AsyncIterable, AsyncIterator

REDACTED = "[REDACTED]"
MAX_PENDING = 4096

EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])"
)

SSN_PATTERN = re.compile(
    r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"
)

CARD_PATTERN = re.compile(
    r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
)


def luhn_valid(number: str) -> bool:
    total = 0

    for index, char in enumerate(reversed(number)):
        digit = int(char)

        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9

        total += digit

    return total % 10 == 0


def redact_pii(text: str) -> str:
    text = EMAIL_PATTERN.sub(REDACTED, text)
    text = SSN_PATTERN.sub(REDACTED, text)

    def replace_card(match: re.Match) -> str:
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and luhn_valid(digits):
            return REDACTED
        return match.group()

    return CARD_PATTERN.sub(replace_card, text)


# Candidate prefixes must remain buffered until a
# delimiter confirms the end of the sensitive value.
EMAIL_CHARS = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789._%+-@"
)


def safe_cut(text: str) -> int:
    """
    Find a conservative boundary for releasing text.

    Hold any trailing email-like or numeric candidate.
    """
    if not text:
        return 0

    index = len(text)

    while index > 0 and text[index - 1] in EMAIL_CHARS:
        index -= 1

    # Also retain a trailing numeric/card-like sequence.
    numeric = re.search(r"(?:\d[ -]?){1,19}(?=[^\d -]|$)", text)
    if numeric:
        index = min(index, numeric.start())

    return index


async def redact_stream(
    chunks: AsyncIterable[str],
) -> AsyncIterator[str]:
    """
    Redact streamed text using bounded pending state.

    Incomplete candidate values are withheld until
    they can be safely evaluated.
    """
    pending = ""

    async for chunk in chunks:
        if not isinstance(chunk, str):
            raise TypeError("Stream chunks must be strings")

        pending += chunk

        cut = safe_cut(pending)

        if cut:
            safe_text = pending[:cut]
            pending = pending[cut:]

            result = redact_pii(safe_text)
            if result:
                yield result

        # Fail closed for unusually long candidates.
        if len(pending) > MAX_PENDING:
            yield REDACTED
            pending = ""

    if pending:
        result = redact_pii(pending)
        if result:
            yield result
