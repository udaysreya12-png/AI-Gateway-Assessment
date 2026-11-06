
# Task 1 — Customer Service MCP Server

## Overview

This project implements a custom Model Context Protocol
(MCP) server using Python and the MCP Python SDK.

The server exposes two tools:

1. get_customer_record
2. trigger_refund

It uses Pydantic for strict input validation and
communicates through the stdio transport.

## Technology Stack

- Python 3.12
- MCP Python SDK 1.30.0
- Pydantic 2.x
- AnyIO
- JSON-RPC 2.0
- stdio transport

## Project Structure

task1_mcp_server/
├── server.py
├── customer_data.py
├── test_client.py
├── test_jsonrpc.py
├── test_transport.py
├── README.md
└── .venv/

## Tool 1: get_customer_record

Retrieves a mock customer record.

Input:
- customer_id: Required string
- Format: CUST-XXXXX (exactly five digits)

Example:

{
  "customer_id": "CUST-00001"
}

The tool returns customer information if the ID exists,
or a not_found response otherwise.

## Tool 2: trigger_refund

Simulates a customer refund.

Inputs:
- customer_id: Required string matching CUST-XXXXX
- amount: Required positive finite number
- reason: Required string of at least 10 characters

Example:

{
  "customer_id": "CUST-00001",
  "amount": 50.0,
  "reason": "Customer requested refund"
}

The refund is simulated; no real payment is processed.

## Strict Validation

Pydantic models enforce:

- Required fields
- Customer ID format
- Positive refund amounts
- Finite numeric amounts
- Minimum refund reason length
- Rejection of unexpected fields

Invalid tool arguments produce MCP tool errors
with isError=True.

## Transport

The server uses MCP stdio transport.

- stdout: JSON-RPC protocol messages
- stderr: Application logs and diagnostics

A JSON-RPC ping request was successfully processed
without stdout contamination.

## Installation

Create and activate a virtual environment:

python -m venv .venv

Windows PowerShell:

.\.venv\Scripts\Activate.ps1

Install dependencies:

python -m pip install "mcp==1.30.0" "pydantic>=2,<3"

## Run the Server

python server.py

The server waits for MCP requests on stdin.
It is normally launched by an MCP client.

## Testing

Run the MCP client:

python test_client.py

Run the JSON-RPC test:

python test_jsonrpc.py

Run the transport isolation test:

python test_transport.py

The test scripts exercise specific scenarios and may
need their input arguments adjusted for other cases.

## Verified Test Results

- Both MCP tools discovered successfully
- Valid customer lookup succeeded
- Valid mock refund succeeded
- Invalid customer ID rejected
- Negative and zero refund amounts rejected
- Short refund reason rejected
- Missing required refund reason rejected
- Unexpected input fields rejected
- Unknown tool name returned isError=True
- JSON-RPC error -32602 observed
- JSON-RPC ping request succeeded
- stdout/stderr isolation verified

## Error Handling Notes

Tool validation failures are represented as MCP tool
results with isError=True.

Protocol-level JSON-RPC errors are handled by the
MCP SDK. The -32602 response was observed at runtime.

The SDK contains a -32601 Method not found handler,
but this response was not independently demonstrated
by the runtime tests.

## Implementation Note

Strict extra-field validation is configured using
Pydantic models and MCP SDK internal tool metadata.

These internal APIs may change between SDK versions.
The implementation was tested with MCP SDK 1.30.0.
