"""
agent.py — Phase 5 (hardened)

Decision-Making Resolution Agent
The ReAct state loop, hand-written on the raw Anthropic Messages API,
with guardrails: a strict iteration ceiling + human escalation, graceful
error recovery fed back into state, and validation of model-supplied args.

Author: Kritarth Keshari

NOTE: This is a BY-HAND agent loop. It uses only the raw Anthropic Messages
API (`pip install anthropic`) — no Claude Agent SDK and no agent framework.
The loop, the tool_use detection, the dispatch, the argument validation, and
the state feedback are all written explicitly here.

The only real external call in the whole project is client.messages.create()
(the model's reasoning). Every "action" the model takes is routed through the
whitelisted dispatcher in dispatcher.py, which can only reach the mock
functions in tools.py.

Guardrails (Phase 5):
  * Execution ceiling: at most MAX_ITERATIONS model invocations; on reaching
    it the loop halts and flags the session for human escalation.
  * Graceful recovery: tool/validation errors are returned as structured
    payloads and fed back into state so the model can self-correct.
  * Argument validation: model-supplied args are checked against the schema
    before any tool runs.
  * Money safety: a refund can never fire on an unverified / hallucinated
    order id — the order must have been successfully looked up first.
"""

import json

import anthropic

from schemas import TOOL_SCHEMAS
from dispatcher import dispatch_tool
from guardrails import validate_tool_args, check_refund_allowed

# Current Claude model id (Claude 5 family). Haiku is the fastest, cheapest
# option; swap for "claude-sonnet-5-5" (stronger) or another id if you prefer.
MODEL = "claude-haiku-5-5"
MAX_TOKENS = 1024

# Strict execution ceiling. If the agent has not produced a final answer after
# this many model invocations, it halts and escalates to a human.
MAX_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are an automated customer-order resolution specialist. A customer "
    "has reported an issue with an item they ordered. Resolve it autonomously "
    "using the tools provided — decide which tools to call and in what order "
    "yourself; the user will not tell you which tool to use.\n\n"
    "Workflow:\n"
    "1. Look up the order to get its details and exchange eligibility.\n"
    "2. If the order is exchange_eligible, check warehouse inventory for the "
    "item to see whether a replacement unit is in stock.\n"
    "3. Decide the resolution:\n"
    "   - If the order is exchange_eligible AND the item is in stock "
    "(available is true / stock_count > 0), confirm a replacement EXCHANGE. "
    "Do NOT issue a refund in this case.\n"
    "   - Otherwise (order not exchange_eligible, OR the item is out of "
    "stock), issue a financial REFUND to the original payment method.\n"
    "4. Always send a confirmation email to the customer summarizing the "
    "resolution, then give the customer a clear, polite summary.\n\n"
    "If an order id cannot be found, do not guess or retry endlessly — explain "
    "that the order was not found and ask the customer to verify the id. Never "
    "issue a refund for an order you have not successfully looked up."
)


def _extract_tool_uses(response):
    """Return the list of tool_use content blocks in a model response."""
    return [block for block in response.content if block.type == "tool_use"]


def _extract_text(response):
    """Concatenate all text blocks in a model response into one string."""
    return "\n".join(
        block.text for block in response.content if block.type == "text"
    ).strip()


def _run_one_tool(tu, verified_order_ids):
    """
    Validate and execute a single model tool request, returning a structured
    result payload. Never raises — all failures come back as 'error' payloads
    so they can be fed back into the conversation state.

    Side effect: records a successfully looked-up order id in verified_order_ids
    so a later refund can be authorized.
    """
    # --- Guardrail 1: validate the model-supplied arguments. ---
    ok, err = validate_tool_args(tu.name, tu.input)
    if not ok:
        return err

    # --- Guardrail 2: money safety — never refund an unverified order. ---
    if tu.name == "process_refund":
        ok, err = check_refund_allowed(tu.input, verified_order_ids)
        if not ok:
            return err

    # --- Execute via the safe dispatcher (whitelist enforced there). ---
    result = dispatch_tool(tu.name, tu.input)

    # Track verified orders so refunds can later be authorized.
    if (
        tu.name == "lookup_order"
        and isinstance(result, dict)
        and result.get("status") == "success"
    ):
        verified_order_ids.add(result.get("order_id"))

    return result


def run_agent(user_message, verbose=True):
    """
    Run the hardened ReAct loop for a single customer request.

    Returns a dict:
      {
        "final_text": str | None,   # the model's closing summary (None if escalated)
        "tool_calls": [ {name, input, result}, ... ],  # trace of everything run
        "escalated": bool,          # True if the iteration ceiling was hit
      }
    """
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": user_message}]
    verified_order_ids = set()
    trace = []

    for turn in range(1, MAX_ITERATIONS + 1):
        if verbose:
            print(f"\n----- model invocation #{turn}/{MAX_ITERATIONS} -----")

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # Record the assistant's raw blocks verbatim (required before results).
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = _extract_tool_uses(response)

        # --- Tool call detection: a final text answer ends the loop. ---
        if response.stop_reason != "tool_use" or not tool_uses:
            final_text = _extract_text(response)
            if verbose:
                print("\n===== FINAL ANSWER =====")
                print(final_text)
            return {
                "final_text": final_text,
                "tool_calls": trace,
                "escalated": False,
            }

        # --- Execution and state feedback. ---
        tool_results = []
        for tu in tool_uses:
            if verbose:
                print(f"  model -> tool_use: {tu.name}({json.dumps(tu.input)})")

            result = _run_one_tool(tu, verified_order_ids)
            trace.append({"name": tu.name, "input": tu.input, "result": result})

            if verbose:
                print(f"  tool_result: {json.dumps(result)}")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    # Structured data as a JSON string, never prose.
                    "content": json.dumps(result),
                    # Mark error payloads so the model clearly sees the failure.
                    "is_error": isinstance(result, dict)
                    and result.get("status") == "error",
                }
            )

        messages.append({"role": "user", "content": tool_results})

    # --- Execution ceiling reached: halt and flag for human escalation. ---
    escalation = (
        f"[ESCALATION] The agent reached the maximum of {MAX_ITERATIONS} "
        f"iterations without resolving the request. The session has been "
        f"halted and flagged for review by a human specialist."
    )
    if verbose:
        print("\n" + escalation)
    return {
        "final_text": None,
        "tool_calls": trace,
        "escalated": True,
    }


def _interactive_cli():
    """Interactive terminal front end: read customer requests and resolve them.

    Type a complaint at the prompt (e.g. mentioning order ORD-1001) and the
    agent resolves it. Type 'quit', 'exit', or press Ctrl-C to stop.
    Requires ANTHROPIC_API_KEY in your environment.
    """
    print("=" * 70)
    print("Decision-Making Resolution Agent  —  interactive mode")
    print("Describe the customer's order issue (include the order id).")
    print("Try: ORD-1001, ORD-1002, ORD-1003, or ORD-9999.")
    print("Type 'quit' or 'exit' to leave.")
    print("=" * 70)

    while True:
        try:
            request = input("\nCUSTOMER> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not request:
            continue
        if request.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break

        run_agent(request, verbose=True)


if __name__ == "__main__":
    _interactive_cli()
