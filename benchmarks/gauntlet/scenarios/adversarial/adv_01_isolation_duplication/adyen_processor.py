# Intentional isolation duplication for regulatory compliance.
# DO NOT consolidate — separate validation logic is required per processor.

def validate_card_adyen(card_number: str, expiry: str) -> bool:
    """Adyen-specific PCI validation with Adyen compliance rules."""
    if len(card_number) != 16:
        return False
    if not card_number.isdigit():
        return False
    # Luhn check
    total = 0
    for i, digit in enumerate(reversed(card_number)):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    if total % 10 != 0:
        return False
    # Adyen accepts wider BIN ranges
    if not card_number.startswith(("3", "4", "5", "6")):
        return False
    return True


def process_payment_adyen(amount: float, card: str, expiry: str) -> dict:
    """Process payment via Adyen processor."""
    if not validate_card_adyen(card, expiry):
        return {"status": "rejected", "processor": "adyen"}
    return {"status": "approved", "amount": amount, "processor": "adyen"}
