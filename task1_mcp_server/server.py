
import sys
import logging
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from customer_data import CUSTOMERS


# Configure logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(levelname)s: %(message)s"
)

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Customer-Service-MCP")


# Strict validation models
class CustomerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(
        pattern=r"^CUST-[0-9]{5}$"
    )


class RefundInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(
        pattern=r"^CUST-[0-9]{5}$"
    )

    amount: float = Field(
        gt=0,
        allow_inf_nan=False
    )

    reason: str = Field(
        min_length=10
    )


# MCP Tool 1: Get Customer Record
@mcp.tool()
def get_customer_record(
    customer_id: Annotated[
        str,
        Field(
            pattern=r"^CUST-[0-9]{5}$",
            description="Customer ID in CUST-XXXXX format"
        )
    ]
) -> dict:
    """Retrieve a customer record by customer ID."""

    customer = CUSTOMERS.get(customer_id)

    if customer is None:
        return {
            "status": "not_found",
            "message": "Customer record not found"
        }

    logger.info("Customer record retrieved")

    return {
        "status": "success",
        "customer": customer
    }


# MCP Tool 2: Trigger Refund
@mcp.tool()
def trigger_refund(
    customer_id: Annotated[
        str,
        Field(pattern=r"^CUST-[0-9]{5}$")
    ],
    amount: Annotated[
        float,
        Field(gt=0, allow_inf_nan=False)
    ],
    reason: Annotated[
        str,
        Field(min_length=10)
    ]
) -> dict:
    """Trigger a mock refund for an existing customer."""

    customer = CUSTOMERS.get(customer_id)

    if customer is None:
        return {
            "status": "failed",
            "message": "Customer record not found"
        }

    logger.info("Mock refund processed")

    return {
        "status": "success",
        "customer_id": customer_id,
        "amount": amount,
        "reason": reason,
        "message": "Mock refund triggered successfully"
    }


# Reject unexpected fields at the MCP tool boundary
def enforce_strict_tool_schemas():
    tool_manager = mcp._tool_manager

    for tool in tool_manager.list_tools():
        if tool.name == "get_customer_record":
            model = CustomerInput
        elif tool.name == "trigger_refund":
            model = RefundInput
        else:
            continue

        # Update the model used to validate incoming arguments
        tool.fn_metadata.arg_model = model
        tool.parameters = model.model_json_schema()


enforce_strict_tool_schemas()


# Start MCP server using stdio transport
if __name__ == "__main__":
    logger.info("Starting Customer-Service-MCP server")
    mcp.run(transport="stdio")
