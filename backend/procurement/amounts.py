from decimal import Decimal, ROUND_HALF_UP


def money(data):
    return sum(
        (Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        for item in data["items"]
    )
