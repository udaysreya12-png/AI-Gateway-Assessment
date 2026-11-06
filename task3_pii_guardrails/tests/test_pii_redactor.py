
import asyncio

from pii_redactor import redact_pii, redact_stream


def run_stream(chunks):
    async def source():
        for chunk in chunks:
            yield chunk

    async def collect():
        output = []
        async for chunk in redact_stream(source()):
            output.append(chunk)
        return "".join(output)

    return asyncio.run(collect())


def test_email_redaction():
    assert redact_pii(
        "Contact john@example.com"
    ) == "Contact [REDACTED]"


def test_ssn_redaction():
    assert redact_pii(
        "SSN: 123-45-6789"
    ) == "SSN: [REDACTED]"


def test_credit_card_redaction():
    assert redact_pii(
        "Card: 4111 1111 1111 1111"
    ) == "Card: [REDACTED]"


def test_email_split_across_chunks():
    result = run_stream([
        "Contact john@",
        "example.",
        "com for help",
    ])
    assert result == "Contact [REDACTED] for help"


def test_ssn_split_across_chunks():
    result = run_stream([
        "SSN: 123-",
        "45-",
        "6789 done",
    ])
    assert result == "SSN: [REDACTED] done"


def test_card_split_across_chunks():
    result = run_stream([
        "Card: 4111 ",
        "1111 1111 ",
        "1111 done",
    ])
    assert result == "Card: [REDACTED] done"


def test_normal_text_unchanged():
    result = run_stream([
        "Hello ",
        "world!",
    ])
    assert result == "Hello world!"


def test_long_stream_preserves_text():
    text = "Hello world! " * 1000
    chunks = [
        text[i:i + 37]
        for i in range(0, len(text), 37)
    ]
    assert run_stream(chunks) == text


def test_email_username_split():
    result = run_stream([
        "Contact john",
        "@example.com now",
    ])
    assert result == "Contact [REDACTED] now"


def test_multiple_pii_values():
    result = run_stream([
        "Email john@example.com ",
        "SSN 123-45-6789 ",
        "Card 4111 1111 1111 1111.",
    ])

    assert result.count("[REDACTED]") == 3
    assert "john@example.com" not in result
    assert "123-45-6789" not in result
    assert "4111 1111 1111 1111" not in result

def test_card_split_into_single_character_chunks():
    text = "Card: 4111 1111 1111 1111. Thank you."
    chunks = list(text)

    result = run_stream(chunks)

    assert result == "Card: [REDACTED]. Thank you."
    assert "4111" not in result

def test_ssn_split_into_single_character_chunks():
    text = "SSN: 123-45-6789. Thank you."
    chunks = list(text)

    result = run_stream(chunks)

    assert result == "SSN: [REDACTED]. Thank you."
    assert "123-45" not in result
    assert "6789" not in result

def test_email_split_into_single_character_chunks():
    text = "Contact john.doe@example.com for help."
    chunks = list(text)

    result = run_stream(chunks)

    assert result == "Contact [REDACTED] for help."
    assert "john.doe" not in result
    assert "@example.com" not in result

def test_card_not_leaked_before_final_chunk():
    async def source():
        yield "Payment card: 4111 1111 1111 "
        yield "1111 confirmed."

    async def collect():
        emitted = []

        async for chunk in redact_stream(source()):
            emitted.append(chunk)

        return emitted

    emitted = asyncio.run(collect())
    result = "".join(emitted)

    assert result == "Payment card: [REDACTED] confirmed."

    for chunk in emitted:
        assert "4111" not in chunk

def test_oversized_pending_candidate_is_redacted():
    long_candidate = "a" * 5000

    result = run_stream([
        "Message: ",
        long_candidate,
        " end.",
    ])

    assert long_candidate not in result
    assert "[REDACTED]" in result

def test_stream_emits_safe_text_before_completion():
    async def source():
        yield "Hello world! "
        await asyncio.sleep(0.2)
        yield "Goodbye."

    async def check():
        stream = redact_stream(source())

        first = await asyncio.wait_for(
            anext(stream),
            timeout=0.1,
        )

        assert first == "Hello world! "

        remaining = []
        async for chunk in stream:
            remaining.append(chunk)

        assert "".join(remaining) == "Goodbye."

    asyncio.run(check())





