"""A/B experiment handlers — intentional divergence for experiment integrity.

variant_a and variant_b implement intentionally different patterns.
Unifying them would invalidate the running experiment.
Experiment tracked in: EXPERIMENTS.md#exp-042
"""


def handle_checkout_variant_a(cart: dict) -> dict:
    """Variant A: immediate charge, sync flow."""
    total = sum(item["price"] * item["qty"] for item in cart.get("items", []))
    if total <= 0:
        return {"status": "error", "message": "Empty cart"}
    # Variant A charges immediately
    charge_result = {"charged": total, "method": "sync"}
    return {"status": "success", "total": total, "charge": charge_result}


def handle_checkout_variant_b(cart: dict) -> dict:
    """Variant B: deferred charge, async flow with confirmation step."""
    items = cart.get("items", [])
    if not items:
        return {"error": True, "reason": "no_items"}
    total = 0.0
    for item in items:
        total += item["price"] * item["qty"]
    # Variant B defers charge and returns a confirmation token
    token = f"pending_{int(total * 100)}"
    return {"pending": True, "token": token, "amount": total}


def handle_checkout_variant_a_discount(cart: dict, discount_pct: float = 0.0) -> dict:
    """Variant A with discount logic — same sync pattern."""
    total = sum(item["price"] * item["qty"] for item in cart.get("items", []))
    total *= (1.0 - discount_pct / 100.0)
    if total <= 0:
        return {"status": "error", "message": "Nothing to charge"}
    return {"status": "success", "total": total, "charge": {"charged": total, "method": "sync"}}


def handle_checkout_variant_b_discount(cart: dict, discount_pct: float = 0.0) -> dict:
    """Variant B with discount logic — same async pattern."""
    items = cart.get("items", [])
    if not items:
        return {"error": True, "reason": "no_items"}
    total = sum(item["price"] * item["qty"] for item in items)
    total *= (1.0 - discount_pct / 100.0)
    token = f"pending_{int(total * 100)}"
    return {"pending": True, "token": token, "amount": total}
