"""
tools.py — Phase 1

Decision-Making Resolution Agent
Deterministic mock tools + in-memory data stores.

Author: Kritarth Keshari

NOTE: Everything here is MOCK. No real database, payment gateway, or email
service is touched. Each tool is a plain deterministic function that returns
STRUCTURED data (a dict with a "status" field of "success" or "error"),
never prose. These are the only functions the agent is ever allowed to call.
"""

# ---------------------------------------------------------------------------
# Mock data stores
# ---------------------------------------------------------------------------
# Rigged so that each order exercises a different branch of the agent's logic:
#   ORD-1001  -> t-shirt,    eligible,     item in stock (7)  -> exchange path
#   ORD-1002  -> headphones, eligible,     item out of stock  -> refund path
#   ORD-1003  -> mug,        NOT eligible                     -> ineligible path
#   ORD-9999  -> absent from the store                        -> error path

_ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "customer_name": "Asha Mehta",
        "customer_email": "asha.mehta@example.com",
        "item_id": "ITM-TSHIRT",
        "item_name": "Cotton T-Shirt",
        "amount": 24.99,
        "status": "delivered",
        "exchange_eligible": True,
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_name": "Liam Carter",
        "customer_email": "liam.carter@example.com",
        "item_id": "ITM-HEADPHONES",
        "item_name": "Wireless Headphones",
        "amount": 89.50,
        "status": "delivered",
        "exchange_eligible": True,
    },
    "ORD-1003": {
        "order_id": "ORD-1003",
        "customer_name": "Priya Nair",
        "customer_email": "priya.nair@example.com",
        "item_id": "ITM-MUG",
        "item_name": "Ceramic Mug",
        "amount": 12.00,
        "status": "delivered",
        "exchange_eligible": False,
    },
}

# Warehouse inventory keyed by item_id.
_INVENTORY = {
    "ITM-TSHIRT": 7,       # in stock  -> exchange possible
    "ITM-HEADPHONES": 0,   # out of stock -> forces refund
    "ITM-MUG": 15,         # in stock, but its order is not exchange-eligible
}


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------
def lookup_order(order_id):
    """Look up a customer order by its id. Returns structured order details."""
    order = _ORDERS.get(order_id)
    if order is None:
        return {
            "status": "error",
            "error": "order_not_found",
            "message": f"No order found with id '{order_id}'.",
        }
    return {
        "status": "success",
        "order_id": order["order_id"],
        "customer_name": order["customer_name"],
        "customer_email": order["customer_email"],
        "item_id": order["item_id"],
        "item_name": order["item_name"],
        "amount": order["amount"],
        "order_status": order["status"],
        "exchange_eligible": order["exchange_eligible"],
    }


def check_inventory(item_id):
    """Check warehouse stock for an item id. Returns count and availability."""
    if item_id not in _INVENTORY:
        return {
            "status": "error",
            "error": "item_not_found",
            "message": f"No inventory record for item '{item_id}'.",
        }
    stock = _INVENTORY[item_id]
    return {
        "status": "success",
        "item_id": item_id,
        "stock_count": stock,
        "available": stock > 0,
    }


def process_refund(order_id, reason):
    """Issue a (fake) financial refund to the order's original payment method."""
    order = _ORDERS.get(order_id)
    if order is None:
        return {
            "status": "error",
            "error": "order_not_found",
            "message": f"Cannot refund unknown order '{order_id}'.",
        }
    # Deterministic fake reference derived from the order id.
    refund_reference = f"REF-{order_id.split('-')[-1]}"
    return {
        "status": "success",
        "order_id": order_id,
        "refund_reference": refund_reference,
        "amount_refunded": order["amount"],
        "reason": reason,
    }


def notify_customer(email, message):
    """Send a (fake) confirmation email: prints it and returns the recipient."""
    print("=" * 60)
    print(f"EMAIL TO: {email}")
    print("-" * 60)
    print(message)
    print("=" * 60)
    return {
        "status": "success",
        "delivered_to": email,
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(">>> lookup_order('ORD-1001')  (exchange path)")
    print(lookup_order("ORD-1001"))
    print()

    print(">>> lookup_order('ORD-9999')  (error path)")
    print(lookup_order("ORD-9999"))
    print()

    print(">>> check_inventory('ITM-TSHIRT')  (in stock)")
    print(check_inventory("ITM-TSHIRT"))
    print()

    print(">>> check_inventory('ITM-HEADPHONES')  (out of stock)")
    print(check_inventory("ITM-HEADPHONES"))
    print()

    print(">>> process_refund('ORD-1002', 'replacement unavailable')")
    print(process_refund("ORD-1002", "replacement unavailable"))
    print()

    print(">>> notify_customer(...)")
    print(notify_customer("asha.mehta@example.com", "Hi Asha, your exchange is confirmed."))
