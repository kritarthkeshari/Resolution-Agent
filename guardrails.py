"""
guardrails.py — Phase 5

Decision-Making Resolution Agent
Argument validation + refund safety checks for model-supplied tool calls.

Author: Kritarth Keshari

NOTE: The model's tool arguments are untrusted input. Before any tool runs,
these helpers validate the arguments the model supplied against the declared
schema (required fields present, correct types) and enforce the critical
money-safety rule: a financial refund may only be issued for an order id that
has already been SUCCESSFULLY looked up in this session. A validation failure
is returned as a structured error payload (never raised) so the agent loop can
feed it back into the conversation and let the model self-correct.
"""

from schemas import TOOL_SCHEMAS

# Index the schemas by tool name for quick lookup.
_SCHEMA_BY_NAME = {schema["name"]: schema for schema in TOOL_SCHEMAS}

# Map JSON-schema type names to the Python types we accept.
_JSON_TYPE_TO_PY = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_tool_args(tool_name, tool_args):
    """
    Validate model-supplied arguments against the tool's declared schema.

    Returns
    -------
    (ok, error_payload)
        ok is True and error_payload is None when the arguments are valid.
        Otherwise ok is False and error_payload is a structured 'error' dict
        describing the problem, suitable to feed back to the model as a
        tool_result so it can correct itself.
    """
    schema = _SCHEMA_BY_NAME.get(tool_name)
    if schema is None:
        # Unknown tool — the dispatcher will also reject it, but flag early.
        return False, {
            "status": "error",
            "error": "unknown_tool",
            "message": f"No schema is registered for tool '{tool_name}'.",
        }

    if not isinstance(tool_args, dict):
        return False, {
            "status": "error",
            "error": "invalid_arguments",
            "message": (
                f"Arguments for '{tool_name}' must be a JSON object, got "
                f"{type(tool_args).__name__}."
            ),
        }

    input_schema = schema["input_schema"]
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    # --- Required fields must be present and non-empty. ---
    for field in required:
        if field not in tool_args or tool_args[field] in (None, ""):
            return False, {
                "status": "error",
                "error": "missing_required_argument",
                "message": (
                    f"Tool '{tool_name}' requires a non-empty '{field}' "
                    f"argument."
                ),
            }

    # --- Provided fields must match their declared types. ---
    for field, value in tool_args.items():
        if field not in properties:
            return False, {
                "status": "error",
                "error": "unexpected_argument",
                "message": (
                    f"Tool '{tool_name}' does not accept an argument named "
                    f"'{field}'."
                ),
            }
        declared = properties[field].get("type")
        expected_py = _JSON_TYPE_TO_PY.get(declared)
        if expected_py is not None and not isinstance(value, expected_py):
            return False, {
                "status": "error",
                "error": "wrong_argument_type",
                "message": (
                    f"Argument '{field}' of '{tool_name}' should be of type "
                    f"'{declared}', got {type(value).__name__}."
                ),
            }

    return True, None


def check_refund_allowed(tool_args, verified_order_ids):
    """
    Money-safety gate: a refund may only target an order that has already been
    successfully looked up this session.

    Returns (ok, error_payload) in the same shape as validate_tool_args.
    This blocks the loop from ever issuing a refund on a hallucinated or
    unverified order id.
    """
    order_id = tool_args.get("order_id")
    if order_id not in verified_order_ids:
        return False, {
            "status": "error",
            "error": "refund_blocked_unverified_order",
            "message": (
                f"Refund refused: order '{order_id}' has not been successfully "
                f"verified with lookup_order in this session. Look the order "
                f"up first; never refund an unverified order id."
            ),
        }
    return True, None
