
# Task 3 — Streaming PII Guardrails

## Overview

This project implements a FastAPI-based LLM gateway that proxies text-generation requests to an upstream LLM provider and applies PII redaction to streamed output.

The gateway detects and redacts:
- Email addresses
- US Social Security Numbers (SSNs)
- Credit card numbers (with Luhn validation)

It also handles sensitive values split across multiple streaming chunks.

## Architecture

Client
  |
  v
FastAPI Gateway (port 8000)
  |
  v
HTTPX Async Client
  |
  v
Mock LLM Provider (port 9000)
  |
  v
SSE Response Parsing
  |
  v
Streaming PII Redactor
  |
  v
Sanitized Response to Client

## Project Files

- `streaming_gateway.py` — FastAPI gateway and upstream streaming integration.
- `pii_redactor.py` — PII detection, masking, and streaming buffer logic.
- `mock_llm_provider.py` — Mock OpenAI-compatible streaming provider.
- `tests/test_pii_redactor.py` — Automated redaction tests.
- `requirements.txt` — Python dependencies.

## Setup

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the mock LLM provider:

```bash
python -m uvicorn mock_llm_provider:app --host 127.0.0.1 --port 9000
```

In another terminal, start the gateway:

```bash
python -m uvicorn streaming_gateway:app --host 127.0.0.1 --port 8000
```

## API Endpoints

### GET /health

Returns:

```json
{"status": "ok"}
```

### POST /v1/generate

Example request:

```json
{
  "prompt": "Generate a sample response containing PII"
}
```

The gateway forwards the prompt to the upstream provider, processes streamed response deltas, and returns sanitized text.

Example output:

```text
Hello! Contact [REDACTED] for support. SSN: [REDACTED]. Card: [REDACTED]. Thank you!
```

## Streaming PII Redaction

The redactor uses regular expressions to identify supported PII formats.

Credit card candidates are additionally checked using the Luhn algorithm to reduce false positives.

A pending buffer is maintained across incoming chunks so that PII split between chunks can be recognized before the buffered text is emitted.

The implementation uses a bounded pending-buffer strategy to limit retained text. Buffer sizing and emission boundaries require careful handling because sensitive values may span chunks.

## Testing

Run:

```bash
python -m pytest tests/test_pii_redactor.py -v
```

Local test results:

- 16 automated tests passed.
- End-to-end gateway request returned the expected redacted output.
- Health endpoint returned `ok`.

Tests include PII detection, chunk-boundary handling, single-character chunks, and buffering behavior.

## Limitations and Future Improvements

- Detection is limited to the implemented PII formats.
- Unusual formatting, Unicode variations, and adversarial chunk boundaries may require additional protection.
- Buffering introduces a latency-versus-safety tradeoff.
- The current gateway returns sanitized plain text rather than forwarding the original SSE event format.
- Production deployment should add authentication, upstream timeouts, observability, and broader security testing.

## Conclusion

This task demonstrates an asynchronous LLM gateway with streaming-response interception and PII redaction, supported by automated and end-to-end functional tests.
