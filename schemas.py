"""
schemas.py — Phase 2

Decision-Making Resolution Agent
Declarative tool contracts (schemas) exposed to the language model.

Author: Kritarth Keshari

NOTE: The model cannot see the function code in tools.py — it only sees these
declarative schemas. Each schema follows the Anthropic Messages API tool
format: a dict with "name", "description", and "input_schema" (a JSON Schema
object with "properties", typed fields, and a "required" list). Descriptions
are written to be unambiguous so the model knows exactly when to call each
tool — in particular, process_refund states plainly that it moves real money
and is only for when a replacement cannot be provided.
"""

LOOKUP_ORDER_SCHEMA = {
    "name": "lookup_order",
    "description": (
        "Look up a customer order by its order id. Use this FIRST to retrieve "
        "the order details before taking any action. Returns the customer "
        "name and email, the purchased item's id and name, the amount paid, "
        "the order status, and whether the order is eligible for an exchange "
        "(exchange_eligible). If the order id does not exist, returns an error "
        "payload with status 'error' instead of order details."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": (
                    "The unique order identifier to look up, e.g. 'ORD-1001'. "
                    "Must be supplied exactly as given by the customer."
                ),
            }
        },
        "required": ["order_id"],
    },
}

CHECK_INVENTORY_SCHEMA = {
    "name": "check_inventory",
    "description": (
        "Check real-time warehouse stock for a specific item id. Use this "
        "after looking up an order, to decide whether a replacement unit is "
        "available for an exchange. Returns the current stock_count and an "
        "'available' boolean (true when stock_count is greater than 0). A "
        "replacement exchange is only possible when 'available' is true."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "item_id": {
                "type": "string",
                "description": (
                    "The item identifier whose warehouse stock should be "
                    "checked, e.g. 'ITM-TSHIRT'. Use the item_id returned by "
                    "lookup_order."
                ),
            }
        },
        "required": ["item_id"],
    },
}

PROCESS_REFUND_SCHEMA = {
    "name": "process_refund",
    "description": (
        "Issue a FINANCIAL REFUND to the customer's original payment method. "
        "This moves money and is irreversible, so only call it when a "
        "replacement exchange is NOT possible — that is, when the order is not "
        "exchange_eligible, or when the replacement item is out of stock "
        "(available is false / stock_count is 0). Never call this for an order "
        "you have not successfully looked up first. Returns a refund_reference "
        "and the amount_refunded on success."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": (
                    "The order identifier to refund. Must be an order id that "
                    "was already confirmed to exist via lookup_order."
                ),
            },
            "reason": {
                "type": "string",
                "description": (
                    "A short human-readable reason for the refund, e.g. "
                    "'replacement out of stock' or 'order not exchange "
                    "eligible'."
                ),
            },
        },
        "required": ["order_id", "reason"],
    },
}

NOTIFY_CUSTOMER_SCHEMA = {
    "name": "notify_customer",
    "description": (
        "Send an official confirmation email to the customer summarizing the "
        "resolution (the confirmed exchange or the processed refund). Always "
        "call this as the FINAL step once the resolution is decided and "
        "executed, before giving your closing summary. Returns the address "
        "the message was delivered to."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": (
                    "The customer's email address, taken from the email "
                    "returned by lookup_order."
                ),
            },
            "message": {
                "type": "string",
                "description": (
                    "The full body of the confirmation message to send to the "
                    "customer, written in a clear and polite tone."
                ),
            },
        },
        "required": ["email", "message"],
    },
}

# The full collection passed to the model on every invocation.
TOOL_SCHEMAS = [
    LOOKUP_ORDER_SCHEMA,
    CHECK_INVENTORY_SCHEMA,
    PROCESS_REFUND_SCHEMA,
    NOTIFY_CUSTOMER_SCHEMA,
]


if __name__ == "__main__":
    import json

    print(f"Defined {len(TOOL_SCHEMAS)} tool schemas:\n")
    for schema in TOOL_SCHEMAS:
        print(json.dumps(schema, indent=2))
        print()
