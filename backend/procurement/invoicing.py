"""Immutable invoice capture and accountable human review, without payment actions."""

from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from .amounts import money
from .receiving import receipt_history


def normalized(value):
    return " ".join(value.split()).casefold()


def invoice_history(connection, requisition_id):
    rows = connection.execute(
        "SELECT * FROM invoices WHERE requisition_id=%s ORDER BY number",
        (requisition_id,),
    ).fetchall()
    result = []
    for row in rows:
        reviews = connection.execute(
            "SELECT r.outcome,r.reason,r.checks,r.created_at,u.name AS actor FROM invoice_reviews r JOIN users u ON u.id=r.actor_id WHERE invoice_id=%s ORDER BY r.id",
            (row["id"],),
        ).fetchall()
        result.append(
            {
                key: value
                for key, value in row.items()
                if key not in ("supplier_key", "number_key", "total_myr")
            }
        )
        result[-1].update(
            id=str(row["id"]),
            requisition_id=str(row["requisition_id"]),
            purchase_order_id=str(row["purchase_order_id"]),
            number=f"INV-{row['number']:04d}",
            total=format(row["total_myr"], ".2f"),
            currency="MYR",
            invoice_date=row["invoice_date"].isoformat(),
            recorded_at=row["recorded_at"].isoformat(),
            status=reviews[-1]["outcome"] if reviews else "awaiting_review",
            reviews=[
                {**review, "created_at": review["created_at"].isoformat()}
                for review in reviews
            ],
        )
    return result


def review_checks(connection, requisition_id, order, invoices):
    if not order:
        return {}
    receipts = receipt_history(connection, requisition_id)

    def identity(snapshot, index):
        return (
            snapshot["kind"],
            normalized(snapshot["supplier"]),
            index,
            snapshot["items"][index]["description"],
        )

    checks = {}
    claimed = {}
    for invoice in invoices:
        if invoice["status"] != "rejected":
            for line in invoice["lines"]:
                key = identity(invoice["po_snapshot"], line["line_index"])
                claimed[key] = claimed.get(key, Decimal("0")) + Decimal(
                    line["quantity"]
                )
    for invoice in invoices:
        warnings = []
        if normalized(invoice["supplier"]) != normalized(
            invoice["po_snapshot"]["supplier"]
        ):
            warnings.append("Supplier differs from the linked issued PO")
        lines = []
        for line in invoice["lines"]:
            index = line["line_index"]
            po_line = invoice["po_snapshot"]["items"][index]
            key = identity(invoice["po_snapshot"], index)
            accepted = sum(
                (
                    Decimal(receipt_line["accepted"])
                    for receipt in receipts
                    for receipt_line in receipt["lines"]
                    if receipt_line["line_index"] == index
                    and identity(receipt["po_snapshot"], index) == key
                ),
                Decimal("0"),
            )
            current_matches = (
                index < len(order["snapshot"]["items"])
                and identity(order["snapshot"], index) == key
            )
            if not current_matches:
                warnings.append(
                    f"Line {index + 1}: historical scope differs from the current PO; inspect original evidence"
                )
            quantity = Decimal(line["quantity"])
            if quantity > Decimal(po_line["quantity"]):
                warnings.append(
                    f"Line {index + 1}: billed quantity exceeds linked PO quantity"
                )
            if Decimal(line["unit_price"]) != Decimal(po_line["unit_price"]):
                warnings.append(
                    f"Line {index + 1}: billed unit price differs from linked PO"
                )
            if quantity > accepted:
                warnings.append(
                    f"Line {index + 1}: billed quantity exceeds accepted quantity"
                )
            if claimed.get(key, Decimal("0")) > accepted:
                warnings.append(
                    f"Line {index + 1}: combined non-rejected invoices exceed accepted quantity"
                )
            if current_matches and claimed.get(key, Decimal("0")) > Decimal(
                order["snapshot"]["items"][index]["quantity"]
            ):
                warnings.append(
                    f"Line {index + 1}: combined non-rejected invoices exceed current ordered quantity"
                )
            lines.append(
                {
                    "line_index": index,
                    "description": po_line["description"],
                    "invoiced": line["quantity"],
                    "invoice_unit_price": line["unit_price"],
                    "po_unit_price": po_line["unit_price"],
                    "linked_ordered": po_line["quantity"],
                    "accepted": format(accepted, ".2f"),
                    "combined_claimed": format(claimed.get(key, Decimal("0")), ".2f"),
                }
            )
        checks[invoice["id"]] = {
            "warnings": warnings,
            "lines": lines,
            "current_po_revision": order["revision"],
            "basis": "Current accepted totals across this PO; compared with captured invoice and linked issued terms. Advisory checks, not formal reconciliation.",
        }
    return checks


def invoice_command(connection, pr, current, history, user, operation, payload):
    if not current:
        raise HTTPException(
            409, "An issued PO is required before invoice capture or review"
        )
    if operation == "capture_invoice":
        order = next(
            (order for order in history if order["revision"] == payload["po_revision"]),
            None,
        )
        if not order:
            raise HTTPException(422, "Select an issued PO revision")
        for line in payload["lines"]:
            if line["line_index"] >= len(order["snapshot"]["items"]):
                raise HTTPException(422, "Invoice references an unknown issued PO line")
            if (
                order["snapshot"]["kind"] == "service"
                and Decimal(line["quantity"])
                != Decimal(line["quantity"]).to_integral_value()
            ):
                raise HTTPException(
                    422, "Service invoice quantities must be whole milestones"
                )
        receipts = {
            receipt["id"]: receipt for receipt in receipt_history(connection, pr["id"])
        }
        if any(id not in receipts for id in payload["receipt_ids"]):
            raise HTTPException(
                422, "Receipt evidence must belong to this purchase order"
            )
        try:
            connection.execute(
                "INSERT INTO invoices (id,requisition_id,purchase_order_id,po_revision,recorded_by,supplier,supplier_key,invoice_number,number_key,invoice_date,evidence_reference,lines,total_myr,po_snapshot,receipt_evidence) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid4(),
                    pr["id"],
                    current["id"],
                    order["revision"],
                    user["id"],
                    payload["supplier"],
                    normalized(payload["supplier"]),
                    payload["invoice_number"],
                    normalized(payload["invoice_number"]),
                    payload["invoice_date"],
                    payload["evidence_reference"],
                    Jsonb(payload["lines"]),
                    money({"items": payload["lines"]}),
                    Jsonb(order["snapshot"]),
                    Jsonb([receipts[id] for id in payload["receipt_ids"]]),
                ),
            )
        except UniqueViolation as error:
            raise HTTPException(
                409, "This supplier invoice number is already captured"
            ) from error
        return
    invoices = invoice_history(connection, pr["id"])
    invoice = next(
        (invoice for invoice in invoices if invoice["id"] == payload["invoice_id"]),
        None,
    )
    if not invoice:
        raise HTTPException(404, "Supplier invoice not found on this purchase order")
    if invoice["status"] in ("reviewed", "rejected"):
        raise HTTPException(
            409, "This invoice review is final; its history cannot be overwritten"
        )
    checks = review_checks(connection, pr["id"], current, invoices)[invoice["id"]]
    connection.execute(
        "INSERT INTO invoice_reviews (invoice_id,actor_id,outcome,reason,checks) VALUES (%s,%s,%s,%s,%s)",
        (
            invoice["id"],
            user["id"],
            payload["outcome"],
            payload["reason"],
            Jsonb(checks),
        ),
    )


def validate_invoice_replacement(connection, requisition_id, current, proposed):
    if (
        not current
        or not connection.execute(
            "SELECT 1 FROM invoices WHERE requisition_id=%s LIMIT 1", (requisition_id,)
        ).fetchone()
    ):
        return
    old = current["snapshot"]
    if (
        any(proposed[key] != old[key] for key in ("kind", "supplier"))
        or len(proposed["items"]) < len(old["items"])
        or any(
            proposed["items"][i]["description"] != item["description"]
            for i, item in enumerate(old["items"])
        )
    ):
        raise HTTPException(
            409,
            "Invoice evidence exists: preserve supplier, purchase type and existing line identities; append new lines or use a separate PR",
        )
