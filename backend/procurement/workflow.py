import copy
import hashlib
import json
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .amounts import money
from .invoicing import (
    invoice_history,
    invoice_command,
    review_checks,
    validate_invoice_replacement,
)
from .receiving import fulfilment, receipt_history, record_receipt, validate_replacement


def can_read(user, record):
    return record["owner_id"] == user["id"] or (
        user["role"] != "requester" and record["status"] != "draft"
    )


def get_record(connection, id, user, lock=False):
    row = connection.execute(
        "SELECT * FROM requisitions WHERE id=%s" + (" FOR UPDATE" if lock else ""),
        (id,),
    ).fetchone()
    if not row or not can_read(user, row):
        raise HTTPException(404, "Purchase requisition not found")
    return row


def view(connection, row):
    events = connection.execute(
        "SELECT e.action,e.version,e.details,e.created_at,u.name AS actor FROM audit_events e JOIN users u ON u.id=e.actor_id WHERE requisition_id=%s ORDER BY e.id",
        (row["id"],),
    ).fetchall()
    return {
        "id": str(row["id"]),
        "number": f"PR-{row['number']:04d}",
        "owner_id": row["owner_id"],
        "status": row["status"],
        "version": row["version"],
        "currency": "MYR",
        "total": format(row["total_myr"], ".2f"),
        **row["data"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "purchase_order": purchase_order_for_pr(connection, row["id"]),
        "receipts": receipt_history(connection, row["id"]),
        "fulfilment": fulfilment(
            connection, row["id"], purchase_order_for_pr(connection, row["id"])
        ),
        "invoices": invoice_history(connection, row["id"]),
        "invoice_checks": review_checks(
            connection,
            row["id"],
            purchase_order_for_pr(connection, row["id"]),
            invoice_history(connection, row["id"]),
        ),
        "po_history": order_history(connection, row["id"]),
        "po_proposals": proposal_history(connection, row["id"]),
        "events": [
            {**event, "created_at": event["created_at"].isoformat()} for event in events
        ],
    }


def command(db, user, key, operation, payload, id=None):
    fingerprint = hashlib.sha256(
        json.dumps([operation, str(id), payload], sort_keys=True).encode()
    ).hexdigest()
    with db.connect() as connection:
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (user["id"] + ":" + key,),
        )
        previous = connection.execute(
            "SELECT * FROM commands WHERE actor_id=%s AND key=%s", (user["id"], key)
        ).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise HTTPException(
                    409, "Idempotency key was already used for a different command"
                )
            return previous["response"]
        reason = payload.get("reason", "").strip()
        if operation == "create":
            if user["role"] != "requester":
                raise HTTPException(403, "Only a requester can create a PR")
            id = uuid4()
            connection.execute(
                "INSERT INTO requisitions (id,owner_id,status,data,total_myr) VALUES (%s,%s,%s,%s,%s)",
                (id, user["id"], "draft", Jsonb(payload), money(payload)),
            )
        else:
            row = get_record(connection, id, user, lock=True)
            if operation in ("issue_po", "propose_po", "issue_po_revision"):
                allowed = user["role"] == "buyer"
            elif operation in ("capture_invoice", "review_invoice"):
                allowed = user["role"] == "invoice_reviewer"
            elif operation == "receive":
                allowed = user["role"] == "receiver"
            elif operation in ("edit", "submit"):
                allowed = user["role"] == "requester" and row["owner_id"] == user["id"]
            else:
                allowed = user["role"] == "approver" and row["owner_id"] != user["id"]
            if not allowed:
                raise HTTPException(403, "This account cannot perform that action")
            if row["version"] != payload["expected_version"]:
                raise HTTPException(409, "This PR changed. Refresh before trying again")
            valid_states = (
                ("approved",)
                if operation
                in (
                    "issue_po",
                    "receive",
                    "capture_invoice",
                    "review_invoice",
                    "propose_po",
                    "approve_po",
                    "return_po",
                    "issue_po_revision",
                )
                else (
                    ("draft", "returned")
                    if operation in ("edit", "submit")
                    else ("submitted",)
                )
            )
            if row["status"] not in valid_states:
                raise HTTPException(409, "Action is not available in the current state")
            if operation == "return" and not reason:
                raise HTTPException(422, "A return reason is required")
            if operation in (
                "propose_po",
                "approve_po",
                "return_po",
                "issue_po_revision",
            ):
                proposal_command(connection, row, user, operation, payload)
                connection.execute(
                    "UPDATE requisitions SET version=version+1,updated_at=now() WHERE id=%s",
                    (id,),
                )
            elif operation in ("capture_invoice", "review_invoice"):
                invoice_command(
                    connection,
                    row,
                    purchase_order_for_pr(connection, id),
                    order_history(connection, id),
                    user,
                    operation,
                    payload,
                )
                connection.execute(
                    "UPDATE requisitions SET version=version+1,updated_at=now() WHERE id=%s",
                    (id,),
                )
            elif operation == "receive":
                record_receipt(
                    connection,
                    row,
                    purchase_order_for_pr(connection, id),
                    user,
                    payload,
                )
                connection.execute(
                    "UPDATE requisitions SET version=version+1,updated_at=now() WHERE id=%s",
                    (id,),
                )
            elif operation == "issue_po":
                if open_proposal(connection, id):
                    raise HTTPException(
                        409, "Resolve the open PO proposal before direct issuance"
                    )
                issue_order(connection, row, user, payload)
                connection.execute(
                    "UPDATE requisitions SET version=version+1,updated_at=now() WHERE id=%s",
                    (id,),
                )
            elif operation == "edit":
                data = {
                    key: value
                    for key, value in payload.items()
                    if key != "expected_version"
                }
                connection.execute(
                    "UPDATE requisitions SET data=%s,total_myr=%s,version=version+1,updated_at=now() WHERE id=%s",
                    (Jsonb(data), money(data), id),
                )
            else:
                status = {
                    "submit": "submitted",
                    "approve": "approved",
                    "return": "returned",
                }[operation]
                connection.execute(
                    "UPDATE requisitions SET status=%s,version=version+1,updated_at=now() WHERE id=%s",
                    (status, id),
                )
        row = connection.execute(
            "SELECT * FROM requisitions WHERE id=%s", (id,)
        ).fetchone()
        details = {"reason": reason} if reason else {}
        if operation in ("capture_invoice", "review_invoice"):
            invoices = invoice_history(connection, id)
            details["invoice"] = (
                invoices[-1]
                if operation == "capture_invoice"
                else next(
                    invoice
                    for invoice in invoices
                    if invoice["id"] == payload["invoice_id"]
                )
            )
        if operation == "receive":
            details["receipt"] = receipt_history(connection, id)[-1]
        if operation in ("create", "edit"):
            details["snapshot"] = row["data"]
        if operation in ("propose_po", "approve_po", "return_po", "issue_po_revision"):
            details["proposal"] = proposal_history(connection, id)[0]
        if operation in ("issue_po", "issue_po_revision"):
            details["purchase_order"] = purchase_order_for_pr(connection, id)
        connection.execute(
            "INSERT INTO audit_events (requisition_id,actor_id,action,version,details) VALUES (%s,%s,%s,%s,%s)",
            (id, user["id"], operation, row["version"], Jsonb(details)),
        )
        result = view(connection, row)
        connection.execute(
            "INSERT INTO commands (actor_id,key,fingerprint,response) VALUES (%s,%s,%s,%s)",
            (user["id"], key, fingerprint, Jsonb(result)),
        )
        return result


def order_view(row):
    return {
        "id": str(row["id"]),
        "number": f"PO-{row['number']:04d}",
        "requisition_id": str(row["requisition_id"]),
        "status": "issued",
        "revision": 1,
        "issued_by": row["issued_by"],
        "issued_at": row["issued_at"].isoformat(),
        "total": format(row["total_myr"], ".2f"),
        "currency": "MYR",
        "snapshot": row["snapshot"],
    }


def original_order_for_pr(connection, id):
    row = connection.execute(
        "SELECT * FROM purchase_orders WHERE requisition_id=%s", (id,)
    ).fetchone()
    return order_view(row) if row else None


def get_purchase_order(connection, id, user):
    row = connection.execute(
        "SELECT * FROM purchase_orders WHERE id=%s", (id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Purchase order not found")
    get_record(connection, row["requisition_id"], user)
    return purchase_order_for_pr(connection, row["requisition_id"])


def issue_order(connection, pr, user, payload):
    if purchase_order_for_pr(connection, pr["id"]):
        raise HTTPException(409, "A PO has already been issued for this PR")
    if len(payload["unit_prices"]) != len(pr["data"]["items"]):
        raise HTTPException(422, "Provide one unit price for each approved line")
    snapshot = copy.deepcopy(pr["data"])
    for item, price in zip(snapshot["items"], payload["unit_prices"]):
        if Decimal(str(price)) > Decimal(str(item["unit_price"])):
            raise HTTPException(
                409,
                "Price exceeds the approved line estimate. Reapproval is required: submit a PO proposal",
            )
        item["unit_price"] = format(Decimal(str(price)), ".2f")
    snapshot.update(
        {
            "supplier": payload["supplier"],
            "delivery_terms": payload["delivery_terms"],
            "approved_pr_version": pr["version"],
            "pr_number": f"PR-{pr['number']:04d}",
        }
    )
    connection.execute(
        "INSERT INTO purchase_orders (id,requisition_id,issued_by,snapshot,total_myr) VALUES (%s,%s,%s,%s,%s)",
        (uuid4(), pr["id"], user["id"], Jsonb(snapshot), money(snapshot)),
    )


def order_history(connection, requisition_id):
    original = original_order_for_pr(connection, requisition_id)
    if not original:
        return []
    rows = connection.execute(
        "SELECT * FROM po_revisions WHERE purchase_order_id=%s ORDER BY revision",
        (original["id"],),
    ).fetchall()
    return [original] + [
        {
            **original,
            "revision": row["revision"],
            "issued_by": row["issued_by"],
            "issued_at": row["issued_at"].isoformat(),
            "snapshot": row["snapshot"],
            "total": format(row["total_myr"], ".2f"),
        }
        for row in rows
    ]


def purchase_order_for_pr(connection, id):
    history = order_history(connection, id)
    return history[-1] if history else None


def proposal_history(connection, id):
    rows = connection.execute(
        "SELECT * FROM po_proposals WHERE requisition_id=%s ORDER BY created_at DESC,id DESC",
        (id,),
    ).fetchall()
    return [
        {
            **row,
            "id": str(row["id"]),
            "requisition_id": str(row["requisition_id"]),
            "created_at": row["created_at"].isoformat(),
            "decided_at": row["decided_at"].isoformat() if row["decided_at"] else None,
            "total_myr": format(row["total_myr"], ".2f"),
        }
        for row in rows
    ]


def open_proposal(connection, id):
    return connection.execute(
        "SELECT * FROM po_proposals WHERE requisition_id=%s AND status IN ('pending','approved')",
        (id,),
    ).fetchone()


def proposal_command(connection, pr, user, operation, payload):
    current = purchase_order_for_pr(connection, pr["id"])
    revision = current["revision"] if current else 0
    if operation == "propose_po":
        if open_proposal(connection, pr["id"]):
            raise HTTPException(
                409, "There is already a PO proposal awaiting review or issuance"
            )
        snapshot = {
            key: value
            for key, value in payload.items()
            if key not in ("expected_version", "reason")
        }
        snapshot.update(
            pr_number=f"PR-{pr['number']:04d}", source_pr_version=pr["version"]
        )
        validate_order_replacement(connection, pr["id"], current, snapshot)
        connection.execute(
            "INSERT INTO po_proposals (id,requisition_id,base_revision,proposed_by,snapshot,total_myr,reason,status) VALUES (%s,%s,%s,%s,%s,%s,%s,'pending')",
            (
                uuid4(),
                pr["id"],
                revision,
                user["id"],
                Jsonb(snapshot),
                money(snapshot),
                payload["reason"],
            ),
        )
        return
    proposal = open_proposal(connection, pr["id"])
    if (
        not proposal
        or str(proposal["id"]) != payload["proposal_id"]
        or proposal["base_revision"] != revision
    ):
        raise HTTPException(
            409, "This proposal is no longer available. Refresh before trying again"
        )
    if operation in ("approve_po", "return_po"):
        if proposal["proposed_by"] == user["id"]:
            raise HTTPException(403, "You cannot approve or return your own proposal")
        if operation == "approve_po" and proposal["status"] != "pending":
            raise HTTPException(409, "Only a pending proposal can be approved")
        if operation == "approve_po":
            validate_order_replacement(
                connection, pr["id"], current, proposal["snapshot"]
            )
        if operation == "return_po" and not payload.get("reason", "").strip():
            raise HTTPException(422, "A return reason is required")
        connection.execute(
            "UPDATE po_proposals SET status=%s,decided_by=%s,decided_at=now(),decision_reason=%s WHERE id=%s",
            (
                "approved" if operation == "approve_po" else "returned",
                user["id"],
                payload.get("reason", ""),
                proposal["id"],
            ),
        )
        return
    if proposal["status"] != "approved":
        raise HTTPException(409, "Ben must approve the proposed terms before issuance")
    validate_order_replacement(connection, pr["id"], current, proposal["snapshot"])
    if current:
        connection.execute(
            "INSERT INTO po_revisions (id,purchase_order_id,revision,proposal_id,issued_by,snapshot,total_myr) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (
                uuid4(),
                current["id"],
                revision + 1,
                proposal["id"],
                user["id"],
                Jsonb(proposal["snapshot"]),
                proposal["total_myr"],
            ),
        )
    else:
        connection.execute(
            "INSERT INTO purchase_orders (id,requisition_id,issued_by,snapshot,total_myr) VALUES (%s,%s,%s,%s,%s)",
            (
                uuid4(),
                pr["id"],
                user["id"],
                Jsonb(proposal["snapshot"]),
                proposal["total_myr"],
            ),
        )
    connection.execute(
        "UPDATE po_proposals SET status='issued' WHERE id=%s", (proposal["id"],)
    )


def validate_order_replacement(connection, requisition_id, current, proposed):
    validate_replacement(connection, requisition_id, current, proposed)
    validate_invoice_replacement(connection, requisition_id, current, proposed)
