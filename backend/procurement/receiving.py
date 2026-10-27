"""Issued-revision receiving and receipt-aware change validation.

The caller owns the PR row lock and transaction for every mutation.
"""

from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb


def receipt_history(connection, requisition_id):
    rows = connection.execute(
        "SELECT * FROM receipts WHERE requisition_id=%s ORDER BY number",
        (requisition_id,),
    ).fetchall()
    return [
        {
            **row,
            "id": str(row["id"]),
            "requisition_id": str(row["requisition_id"]),
            "purchase_order_id": str(row["purchase_order_id"]),
            "number": f"{'GR' if row['kind'] == 'goods' else 'SA'}-{row['number']:04d}",
            "received_on": row["received_on"].isoformat(),
            "recorded_at": row["recorded_at"].isoformat(),
        }
        for row in rows
    ]


def fulfilment(connection, requisition_id, order):
    if not order:
        return None
    receipts = receipt_history(connection, requisition_id)
    lines = []
    for index, item in enumerate(order["snapshot"]["items"]):
        totals = {key: Decimal("0") for key in ("accepted", "damaged", "rejected")}
        for receipt in receipts:
            for line in receipt["lines"]:
                if line["line_index"] == index:
                    for key in totals:
                        totals[key] += Decimal(line[key])
        ordered = Decimal(item["quantity"])
        lines.append(
            {
                "line_index": index,
                "description": item["description"],
                "ordered": format(ordered, ".2f"),
                **{key: format(value, ".2f") for key, value in totals.items()},
                "outstanding": format(ordered - totals["accepted"], ".2f"),
            }
        )
    status = (
        "complete"
        if all(Decimal(line["outstanding"]) == 0 for line in lines)
        else "partial"
        if any(Decimal(line["accepted"]) > 0 for line in lines)
        else "awaiting"
    )
    return {
        "status": status,
        "po_revision": order["revision"],
        "kind": order["snapshot"]["kind"],
        "lines": lines,
    }


def record_receipt(connection, pr, order, user, payload):
    if not order:
        raise HTTPException(409, "An issued PO is required before receiving")
    if order["revision"] != payload["po_revision"]:
        raise HTTPException(
            409, "The issued PO revision changed. Refresh before receiving"
        )
    summary = fulfilment(connection, pr["id"], order)
    for line in payload["lines"]:
        index = line["line_index"]
        if index >= len(summary["lines"]):
            raise HTTPException(422, "Receipt references an unknown issued PO line")
        quantities = [Decimal(line[key]) for key in ("accepted", "damaged", "rejected")]
        if order["snapshot"]["kind"] == "service":
            if quantities[1] or any(q != q.to_integral_value() for q in quantities):
                raise HTTPException(
                    422,
                    "Services require whole milestones and cannot record damaged goods",
                )
        if sum(quantities) > Decimal(summary["lines"][index]["outstanding"]):
            raise HTTPException(
                409, "Receipt quantities exceed the outstanding issued quantity"
            )
    connection.execute(
        "INSERT INTO receipts (id,requisition_id,purchase_order_id,po_revision,recorded_by,received_on,reference,notes,kind,lines,po_snapshot) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            uuid4(),
            pr["id"],
            order["id"],
            order["revision"],
            user["id"],
            payload["received_on"],
            payload["reference"],
            payload["notes"],
            order["snapshot"]["kind"],
            Jsonb(payload["lines"]),
            Jsonb(order["snapshot"]),
        ),
    )


def validate_replacement(connection, requisition_id, current, proposed):
    """Run when proposing, approving AND issuing, since receiving may continue."""
    if not current or not receipt_history(connection, requisition_id):
        return
    old = current["snapshot"]
    if any(proposed[key] != old[key] for key in ("kind", "supplier")):
        raise HTTPException(
            409,
            "After receiving starts, keep the purchase type and supplier; use a separate PR for a different purchase",
        )
    if len(proposed["items"]) < len(old["items"]):
        raise HTTPException(
            409, "After receiving starts, preserve existing PO line references"
        )
    summary = fulfilment(connection, requisition_id, current)
    for index, item in enumerate(old["items"]):
        replacement = proposed["items"][index]
        if replacement["description"] != item["description"]:
            raise HTTPException(
                409,
                "After receiving starts, preserve existing line descriptions and order; append a new line for changed scope",
            )
        if Decimal(replacement["quantity"]) < Decimal(
            summary["lines"][index]["accepted"]
        ):
            raise HTTPException(
                409,
                "Proposed quantity is below the quantity already accepted. Return this proposal for changes",
            )
