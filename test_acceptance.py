"""
test_acceptance.py — Phase 5

Decision-Making Resolution Agent
Drives the agent against every acceptance criterion and reports PASS/FAIL.

Author: Kritarth Keshari

NOTE: Each scenario is a real agentic run, so this makes live Anthropic API
calls (one run per order id below). Requires ANTHROPIC_API_KEY in your
environment. Assertions inspect the tool-call TRACE returned by run_agent so
we verify the agent's autonomous decisions (which tools it chose and how it
branched), not just its prose.
"""

import sys

from agent import run_agent


def _tool_names(outcome):
    """Set of tool names the agent actually invoked during a run."""
    return {call["name"] for call in outcome["tool_calls"]}


def _check(label, condition):
    """Print a single PASS/FAIL line and return the boolean."""
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
    return condition


def run_case(title, request):
    """Run one scenario and print a header; return the outcome dict."""
    print("\n" + "#" * 70)
    print(f"# {title}")
    print(f"# customer: {request}")
    print("#" * 70)
    outcome = run_agent(request, verbose=True)
    return outcome


def main():
    results = []

    # -- Criterion: autonomous investigation + correct EXCHANGE branch --------
    # ORD-1001: t-shirt, eligible, stock = 7 -> exchange, NO refund.
    out = run_case(
        "ORD-1001 — eligible + in stock -> EXCHANGE",
        "Hi, my order ORD-1001 arrived damaged and I'd like it sorted out.",
    )
    names = _tool_names(out)
    results.append(_check("read the order (lookup_order)", "lookup_order" in names))
    results.append(_check("inspected inventory (check_inventory)", "check_inventory" in names))
    results.append(_check("did NOT refund (exchange path)", "process_refund" not in names))
    results.append(_check("sent confirmation email (notify_customer)", "notify_customer" in names))
    results.append(_check("gave a final summary", bool(out["final_text"])))

    # -- Criterion: correct REFUND branch when stock is 0 ---------------------
    # ORD-1002: headphones, eligible, stock = 0 -> refund.
    out = run_case(
        "ORD-1002 — eligible but out of stock -> REFUND",
        "My order ORD-1002 came broken, please help.",
    )
    names = _tool_names(out)
    results.append(_check("read the order (lookup_order)", "lookup_order" in names))
    results.append(_check("inspected inventory (check_inventory)", "check_inventory" in names))
    results.append(_check("issued a refund (process_refund)", "process_refund" in names))
    results.append(_check("sent confirmation email (notify_customer)", "notify_customer" in names))
    results.append(_check("gave a final summary", bool(out["final_text"])))

    # -- Criterion: ineligible order -> REFUND --------------------------------
    # ORD-1003: mug, exchange_eligible = False -> refund.
    out = run_case(
        "ORD-1003 — not exchange-eligible -> REFUND",
        "Order ORD-1003 is defective, I want this resolved.",
    )
    names = _tool_names(out)
    results.append(_check("read the order (lookup_order)", "lookup_order" in names))
    results.append(_check("issued a refund (process_refund)", "process_refund" in names))
    results.append(_check("sent confirmation email (notify_customer)", "notify_customer" in names))
    results.append(_check("gave a final summary", bool(out["final_text"])))

    # -- Criterion: resilience to an invalid order id -------------------------
    # ORD-9999: does not exist -> graceful "not found", no crash, no refund.
    out = run_case(
        "ORD-9999 — invalid order id -> GRACEFUL ERROR",
        "Please look into my order ORD-9999, the item is damaged.",
    )
    names = _tool_names(out)
    results.append(_check("attempted lookup (lookup_order)", "lookup_order" in names))
    results.append(_check("did NOT refund an unverified order", "process_refund" not in names))
    results.append(_check("did not crash + explained the problem", bool(out["final_text"])))
    final_lower = (out["final_text"] or "").lower()
    results.append(
        _check(
            "asked the customer to verify the id",
            any(w in final_lower for w in ("not found", "verify", "check", "couldn't find", "could not find")),
        )
    )

    # -- Summary --------------------------------------------------------------
    passed = sum(results)
    total = len(results)
    print("\n" + "=" * 70)
    print(f"ACCEPTANCE RESULT: {passed}/{total} checks passed")
    print("=" * 70)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
