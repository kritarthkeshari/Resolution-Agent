"""
dispatcher.py — Phase 3

Decision-Making Resolution Agent
Tool registration (whitelist) + safe dispatch gatekeeper.

Author: Kritarth Keshari

NOTE: The model can only ask for a tool by name; it never executes anything
itself. This module is the single gate between the model's requests and the
real functions. The REGISTRY is an explicit whitelist mapping approved tool
names to the functions in tools.py. dispatch_tool() looks up the requested
name in that whitelist and either runs the function or returns a controlled
error payload. A name that is not in the registry is NEVER executed — the
dispatcher refuses it instead of raising, so the agent loop can feed the
refusal back to the model as state.
"""

import tools

# ---------------------------------------------------------------------------
# Registry whitelist: tool name -> function object
# ---------------------------------------------------------------------------
# Only the four names below are callable. Anything the model names that is not
# a key here is rejected by the dispatcher.
REGISTRY = {
    "lookup_order": tools.lookup_order,
    "check_inventory": tools.check_inventory,
    "process_refund": tools.process_refund,
    "notify_customer": tools.notify_customer,
}


def dispatch_tool(tool_name, tool_args):
    """
    Safely execute a tool the model requested.

    Parameters
    ----------
    tool_name : str
        The name of the tool the model asked to invoke.
    tool_args : dict
        The keyword arguments the model supplied for that tool.

    Returns
    -------
    dict
        The tool's structured result on success, or a controlled error
        payload (status 'error') if the tool is not whitelisted or if the
        call fails. This function never raises for a bad request — every
        failure is returned as data so the agent loop can feed it back into
        the conversation state.
    """
    # --- Authorization check: is the tool on the whitelist? ---
    func = REGISTRY.get(tool_name)
    if func is None:
        return {
            "status": "error",
            "error": "tool_not_registered",
            "message": (
                f"Tool '{tool_name}' is not in the approved registry and will "
                f"not be executed. Allowed tools: {sorted(REGISTRY)}."
            ),
        }

    # --- Arguments must be a mapping we can expand as keyword args. ---
    if not isinstance(tool_args, dict):
        return {
            "status": "error",
            "error": "invalid_arguments",
            "message": (
                f"Arguments for tool '{tool_name}' must be an object/dict, "
                f"got {type(tool_args).__name__}."
            ),
        }

    # --- Execute, converting any unexpected failure into a controlled error. ---
    try:
        return func(**tool_args)
    except TypeError as exc:
        # Wrong / missing / extra arguments supplied by the model.
        return {
            "status": "error",
            "error": "bad_arguments",
            "message": f"Could not call '{tool_name}': {exc}",
        }
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        return {
            "status": "error",
            "error": "tool_execution_failed",
            "message": f"Tool '{tool_name}' raised an unexpected error: {exc}",
        }


if __name__ == "__main__":
    print(">>> valid tool, valid args")
    print(dispatch_tool("lookup_order", {"order_id": "ORD-1001"}))
    print()

    print(">>> tool NOT in registry (rejected, not executed)")
    print(dispatch_tool("delete_database", {"order_id": "ORD-1001"}))
    print()

    print(">>> valid tool, missing required arg")
    print(dispatch_tool("process_refund", {"order_id": "ORD-1002"}))
    print()

    print(">>> valid tool, args not a dict")
    print(dispatch_tool("check_inventory", "ITM-TSHIRT"))
