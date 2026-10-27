"""Public HTTP contracts against real PostgreSQL; no mocked persistence."""

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from procurement.app import create_app
from procurement.config import Settings
from procurement.identity import COOKIE


@pytest.fixture(scope="module")
def application():
    settings = Settings(
        schema="test_procurement_" + uuid4().hex,
        secret="integration-test-secret-" + "x" * 40,
    )
    app = create_app(settings)
    with TestClient(app):
        yield app
    with app.state.db.connect() as connection:
        connection.execute(
            sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(settings.schema))
        )


@pytest.fixture
def client(application):
    with application.state.db.connect() as connection:
        connection.execute(
            "TRUNCATE commands,audit_events,requisitions,sessions RESTART IDENTITY CASCADE"
        )
    with TestClient(application) as client:
        yield client


def sign_in(client, user="aina"):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login", json={"username": user, "password": "harbor-demo"}
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def data():
    return {
        "title": "Pump seals for maintenance",
        "kind": "goods",
        "purpose": "Replace worn pump seals",
        "vessel": "MV Harbor One",
        "location": "Port Klang",
        "required_date": "2026-12-01",
        "supplier_suggestion": "Demo Marine Supply",
        "items": [
            {"description": "Pump seal", "quantity": "10", "unit_price": "200.00"}
        ],
    }


def mutate(client, path, payload, headers, key=None, method="post"):
    return getattr(client, method)(
        "/api/v1" + path,
        json=payload,
        headers={**headers, "Idempotency-Key": key or str(uuid4())},
    )


def draft(client):
    headers = sign_in(client)
    response = mutate(client, "/requisitions", data(), headers)
    assert response.status_code == 201, response.text
    return response.json(), headers


def submitted(client):
    record, headers = draft(client)
    response = mutate(
        client, f"/requisitions/{record['id']}/submit", {"expected_version": 1}, headers
    )
    assert response.status_code == 200, response.text
    return response.json(), headers


def test_login_rejects_bad_credentials_and_role_injection(client):
    response = client.post(
        "/api/v1/auth/login", json={"username": "aina", "password": "wrong"}
    )
    assert response.status_code == 401
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "aina", "password": "harbor-demo", "role": "approver"},
    )
    assert response.status_code == 422
    sign_in(client)
    assert (
        client.get("/api/v1/auth/me", headers={"X-Role": "approver"}).json()["user"][
            "role"
        ]
        == "requester"
    )


def test_workflow_and_audit_survive_application_recreation(client, application):
    record, headers = submitted(client)
    headers = sign_in(client, "ben")
    response = mutate(
        client,
        f"/requisitions/{record['id']}/approve",
        {"expected_version": 2},
        headers,
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert (
        result["status"] == "approved"
        and result["total"] == "2000.00"
        and result["version"] == 3
    )
    assert [(e["action"], e["actor"]) for e in result["events"]] == [
        ("create", "Aina"),
        ("submit", "Aina"),
        ("approve", "Ben"),
    ]
    token = client.cookies.get(COOKIE)
    with TestClient(create_app(application.state.settings)) as restarted:
        restarted.cookies.set(COOKIE, token, path="/api")
        persisted = restarted.get(f"/api/v1/requisitions/{record['id']}")
        assert persisted.status_code == 200
        assert persisted.json() == result


def test_return_reason_edit_and_resubmit(client):
    record, headers = submitted(client)
    headers = sign_in(client, "ben")
    path = f"/requisitions/{record['id']}"
    assert (
        mutate(
            client, path + "/return", {"expected_version": 2, "reason": " "}, headers
        ).status_code
        == 422
    )
    returned = mutate(
        client,
        path + "/return",
        {"expected_version": 2, "reason": "Clarify quantity"},
        headers,
    )
    assert returned.json()["status"] == "returned"
    headers = sign_in(client)
    edited = mutate(
        client,
        path,
        {**data(), "title": "Updated pump seals", "expected_version": 3},
        headers,
        method="put",
    )
    assert edited.status_code == 200 and edited.json()["version"] == 4
    resubmitted = mutate(client, path + "/submit", {"expected_version": 4}, headers)
    assert resubmitted.json()["status"] == "submitted"
    assert [e["action"] for e in resubmitted.json()["events"]] == [
        "create",
        "submit",
        "return",
        "edit",
        "submit",
    ]
    assert resubmitted.json()["events"][2]["details"]["reason"] == "Clarify quantity"


def test_all_five_roles_are_enforced(client):
    record, headers = submitted(client)
    path = f"/requisitions/{record['id']}/approve"
    for user in ["aina", "chloe", "dinesh", "eva"]:
        headers = sign_in(client, user)
        assert mutate(client, path, {"expected_version": 2}, headers).status_code == 403
    headers = sign_in(client, "ben")
    assert mutate(client, path, {"expected_version": 2}, headers).status_code == 200
    for user in ["ben", "chloe", "dinesh", "eva"]:
        headers = sign_in(client, user)
        assert mutate(client, "/requisitions", data(), headers).status_code == 403


def test_drafts_are_not_visible_to_other_roles(client):
    record, headers = draft(client)
    for user in ["ben", "chloe", "dinesh", "eva"]:
        sign_in(client, user)
        assert client.get(f"/api/v1/requisitions/{record['id']}").status_code == 404
        assert client.get("/api/v1/requisitions").json()["items"] == []


def test_self_approval_is_rejected_even_if_account_has_approver_role(
    client, application
):
    record, headers = submitted(client)
    with application.state.db.connect() as connection:
        connection.execute(
            "UPDATE requisitions SET owner_id=%s WHERE id=%s", ("ben", record["id"])
        )
    headers = sign_in(client, "ben")
    assert (
        mutate(
            client,
            f"/requisitions/{record['id']}/approve",
            {"expected_version": 2},
            headers,
        ).status_code
        == 403
    )


def test_idempotent_retries_do_not_duplicate_record_or_audit(client):
    headers = sign_in(client)
    key = str(uuid4())
    first = mutate(client, "/requisitions", data(), headers, key)
    repeat = mutate(client, "/requisitions", data(), headers, key)
    assert first.json() == repeat.json()
    assert len(client.get("/api/v1/requisitions").json()["items"]) == 1
    assert (
        mutate(
            client,
            "/requisitions",
            {**data(), "title": "Different purchase"},
            headers,
            key,
        ).status_code
        == 409
    )
    record = first.json()
    key = str(uuid4())
    path = f"/requisitions/{record['id']}/submit"
    first = mutate(client, path, {"expected_version": 1}, headers, key)
    repeat = mutate(client, path, {"expected_version": 1}, headers, key)
    assert first.json() == repeat.json() and len(first.json()["events"]) == 2


def test_stale_version_and_invalid_transitions_are_rejected(client):
    record, headers = draft(client)
    path = f"/requisitions/{record['id']}"
    assert (
        mutate(
            client, path, {**data(), "expected_version": 7}, headers, method="put"
        ).status_code
        == 409
    )
    mutate(client, path + "/submit", {"expected_version": 1}, headers)
    assert (
        mutate(
            client, path, {**data(), "expected_version": 2}, headers, method="put"
        ).status_code
        == 409
    )
    assert (
        mutate(client, path + "/submit", {"expected_version": 2}, headers).status_code
        == 409
    )


def test_csrf_and_foreign_origin_are_rejected(client):
    headers = sign_in(client)
    assert mutate(client, "/requisitions", data(), {}).status_code == 403
    assert (
        mutate(
            client,
            "/requisitions",
            data(),
            {**headers, "Origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    assert client.get("/api/v1/requisitions").json()["items"] == []


def test_tokens_must_be_signed_unexpired_and_unrevoked(client, application):
    headers = sign_in(client)
    original = client.cookies.get(COOKIE)
    claims = jwt.decode(
        original,
        application.state.settings.secret,
        algorithms=["HS256"],
        audience="harbor-api",
        issuer="harbor-local",
    )
    tokens = [
        original[:-8] + "xxxxxxxx",
        jwt.encode(
            {**claims, "exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
            application.state.settings.secret,
            algorithm="HS256",
        ),
        jwt.encode(claims, "wrong-secret-" + ("z" * 40), algorithm="HS256"),
    ]
    for token in tokens:
        client.cookies.clear()
        client.cookies.set(COOKIE, token, path="/api")
        assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.clear()
    client.cookies.set(COOKIE, original, path="/api")
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    client.cookies.set(COOKIE, original, path="/api")
    assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize(
    "field,value",
    [
        ("quantity", "0"),
        ("quantity", "1.001"),
        ("unit_price", "-1"),
        ("unit_price", "0.001"),
    ],
)
def test_invalid_quantities_and_amounts(client, field, value):
    headers = sign_in(client)
    body = data()
    body["items"][0][field] = value
    assert mutate(client, "/requisitions", body, headers).status_code == 422


def test_exact_decimal_totals_and_whole_service_milestones(client):
    headers = sign_in(client)
    body = data()
    body["items"] = [
        {"description": "Small part", "quantity": "3", "unit_price": "0.10"}
    ]
    assert mutate(client, "/requisitions", body, headers).json()["total"] == "0.30"
    body["kind"] = "service"
    body["items"][0]["quantity"] = "1.5"
    assert mutate(client, "/requisitions", body, headers).status_code == 422


def test_competing_approvals_only_commit_once(client, application):
    record, headers = submitted(client)
    headers = sign_in(client, "ben")
    token = client.cookies.get(COOKIE)

    def approve(_):
        with TestClient(application) as another:
            another.cookies.set(COOKIE, token, path="/api")
            return mutate(
                another,
                f"/requisitions/{record['id']}/approve",
                {"expected_version": 2},
                headers,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(approve, range(2))) == [200, 409]
    result = client.get(f"/api/v1/requisitions/{record['id']}").json()
    assert len([e for e in result["events"] if e["action"] == "approve"]) == 1


def test_default_signing_key_persists_across_fresh_application_settings(
    application, monkeypatch, tmp_path
):
    from procurement import config

    monkeypatch.setattr(config, "BACKEND", tmp_path)
    monkeypatch.delenv("SESSION_SIGNING_KEY", raising=False)
    first = Settings(schema=application.state.settings.schema)
    with TestClient(create_app(first)) as browser:
        sign_in(browser)
        token = browser.cookies.get(COOKIE)
    second = Settings(schema=application.state.settings.schema)
    assert first.secret == second.secret and len(second.secret) >= 32
    with TestClient(create_app(second)) as restarted:
        restarted.cookies.set(COOKIE, token, path="/api")
        assert restarted.get("/api/v1/auth/me").json()["user"]["id"] == "aina"


def approved(client):
    record, _ = submitted(client)
    headers = sign_in(client, "ben")
    response = mutate(
        client,
        f"/requisitions/{record['id']}/approve",
        {"expected_version": 2},
        headers,
    )
    assert response.status_code == 200
    return response.json()


def po_payload(version=3):
    return {
        "expected_version": version,
        "supplier": "Confirmed Marine Supply",
        "unit_prices": ["190.00"],
        "delivery_terms": "Deliver to Port Klang within seven days",
    }


def test_buyer_issues_a_separate_po_snapshot(client):
    record = approved(client)
    headers = sign_in(client, "chloe")
    result = mutate(
        client, f"/requisitions/{record['id']}/purchase-order", po_payload(), headers
    )
    assert result.status_code == 201, result.text
    pr = result.json()
    po = pr["purchase_order"]
    assert (
        pr["status"] == "approved" and pr["total"] == "2000.00" and pr["version"] == 4
    )
    assert (
        po["total"] == "1900.00"
        and po["snapshot"]["supplier"] == "Confirmed Marine Supply"
    )
    assert (
        po["snapshot"]["items"][0]["quantity"] == "10"
        and po["snapshot"]["approved_pr_version"] == 3
    )
    assert po["issued_by"] == "chloe" and po["status"] == "issued"
    assert (
        pr["events"][-1]["action"] == "issue_po"
        and pr["events"][-1]["actor"] == "Chloe"
    )
    assert client.get("/api/v1/purchase-orders/" + po["id"]).json() == po
    sign_in(client, "aina")
    assert client.get("/api/v1/purchase-orders/" + po["id"]).json() == po


def test_only_buyer_can_issue_and_only_from_approved_pr(client):
    record, _ = submitted(client)
    path = f"/requisitions/{record['id']}/purchase-order"
    headers = sign_in(client, "chloe")
    assert mutate(client, path, po_payload(version=2), headers).status_code == 409
    headers = sign_in(client, "ben")
    mutate(
        client,
        f"/requisitions/{record['id']}/approve",
        {"expected_version": 2},
        headers,
    )
    for user in ["aina", "ben", "dinesh", "eva"]:
        headers = sign_in(client, user)
        assert mutate(client, path, po_payload(), headers).status_code == 403
    headers = sign_in(client, "chloe")
    assert mutate(client, path, po_payload(version=2), headers).status_code == 409


def test_price_increases_and_scope_injection_are_not_issued(client):
    record = approved(client)
    headers = sign_in(client, "chloe")
    path = f"/requisitions/{record['id']}/purchase-order"
    increased = mutate(
        client, path, {**po_payload(), "unit_prices": ["200.01"]}, headers
    )
    assert increased.status_code == 409 and "Reapproval" in increased.json()["detail"]
    assert (
        mutate(
            client, path, {**po_payload(), "items": [{"quantity": "20"}]}, headers
        ).status_code
        == 422
    )
    assert (
        mutate(
            client, path, {**po_payload(), "unit_prices": ["190", "190"]}, headers
        ).status_code
        == 422
    )
    assert (
        mutate(client, path, {**po_payload(), "supplier": " "}, headers).status_code
        == 422
    )
    assert (
        mutate(
            client, path, {**po_payload(), "unit_prices": ["0"]}, headers
        ).status_code
        == 422
    )
    pr = client.get("/api/v1/requisitions/" + record["id"]).json()
    assert (
        pr["purchase_order"] is None and pr["version"] == 3 and len(pr["events"]) == 3
    )


def test_po_retry_replays_and_new_commands_cannot_issue_twice(client):
    record = approved(client)
    headers = sign_in(client, "chloe")
    path = f"/requisitions/{record['id']}/purchase-order"
    key = str(uuid4())
    first = mutate(client, path, po_payload(), headers, key)
    again = mutate(client, path, po_payload(), headers, key)
    assert (
        first.status_code == again.status_code == 201 and first.json() == again.json()
    )
    assert mutate(client, path, po_payload(version=4), headers).status_code == 409
    assert (
        mutate(
            client,
            path,
            {**po_payload(), "supplier": "Different supplier"},
            headers,
            key,
        ).status_code
        == 409
    )
    pr = client.get("/api/v1/requisitions/" + record["id"]).json()
    assert len([e for e in pr["events"] if e["action"] == "issue_po"]) == 1


def test_po_snapshot_survives_source_change_and_database_protects_it(
    client, application
):
    import psycopg

    record = approved(client)
    headers = sign_in(client, "chloe")
    po = mutate(
        client, f"/requisitions/{record['id']}/purchase-order", po_payload(), headers
    ).json()["purchase_order"]
    # Isolated fixture mutation demonstrates this is a copy, not live PR rendering.
    with application.state.db.connect() as connection:
        connection.execute(
            "UPDATE requisitions SET data=jsonb_set(data,'{title}',to_jsonb('Changed fixture title'::text)) WHERE id=%s",
            (record["id"],),
        )
    assert client.get("/api/v1/purchase-orders/" + po["id"]).json() == po
    with pytest.raises(psycopg.errors.RaiseException):
        with application.state.db.connect() as connection:
            connection.execute(
                "UPDATE purchase_orders SET total_myr=1 WHERE id=%s", (po["id"],)
            )
    token = client.cookies.get(COOKIE)
    with TestClient(create_app(application.state.settings)) as restarted:
        restarted.cookies.set(COOKIE, token, path="/api")
        assert restarted.get("/api/v1/purchase-orders/" + po["id"]).json() == po


def test_concurrent_po_commands_issue_exactly_one_order(client, application):
    record = approved(client)
    headers = sign_in(client, "chloe")
    token = client.cookies.get(COOKIE)

    def issue(_):
        with TestClient(application) as other:
            other.cookies.set(COOKIE, token, path="/api")
            return mutate(
                other,
                f"/requisitions/{record['id']}/purchase-order",
                po_payload(),
                headers,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(issue, range(2))) == [201, 409]
    with application.state.db.connect() as connection:
        assert (
            connection.execute(
                "SELECT count(*) AS n FROM purchase_orders WHERE requisition_id=%s",
                (record["id"],),
            ).fetchone()["n"]
            == 1
        )


def test_unrelated_requester_cannot_read_order(client, application):
    record = approved(client)
    headers = sign_in(client, "chloe")
    po = mutate(
        client, f"/requisitions/{record['id']}/purchase-order", po_payload(), headers
    ).json()["purchase_order"]
    with application.state.db.connect() as connection:
        connection.execute(
            "INSERT INTO users (id,name,role,password_hash) SELECT 'other','Other','requester',password_hash FROM users WHERE id='aina' ON CONFLICT DO NOTHING"
        )
    sign_in(client, "other")
    assert client.get("/api/v1/purchase-orders/" + po["id"]).status_code == 404
    assert client.get("/api/v1/requisitions").json()["items"] == []


def test_failed_audit_rolls_back_po_and_allows_same_key_retry(client, application):
    record = approved(client)
    headers = sign_in(client, "chloe")
    key = str(uuid4())
    path = f"/requisitions/{record['id']}/purchase-order"
    with application.state.db.connect() as connection:
        connection.execute(
            "CREATE FUNCTION fail_issue_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='issue_po' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END; $$"
        )
        connection.execute(
            "CREATE TRIGGER fail_issue BEFORE INSERT ON audit_events FOR EACH ROW EXECUTE FUNCTION fail_issue_audit()"
        )
    try:
        assert mutate(client, path, po_payload(), headers, key).status_code == 500
        pr = client.get("/api/v1/requisitions/" + record["id"]).json()
        assert (
            pr["purchase_order"] is None
            and pr["version"] == 3
            and len(pr["events"]) == 3
        )
    finally:
        with application.state.db.connect() as connection:
            connection.execute("DROP TRIGGER fail_issue ON audit_events")
            connection.execute("DROP FUNCTION fail_issue_audit()")
    assert mutate(client, path, po_payload(), headers, key).status_code == 201


def issued(client):
    record = approved(client)
    headers = sign_in(client, "chloe")
    return mutate(
        client, f"/requisitions/{record['id']}/purchase-order", po_payload(), headers
    ).json()


def proposal_payload(version):
    body = data()
    body["items"][0].update(
        quantity="12", unit_price="220.00", description="Upgraded pump seal"
    )
    return {
        **body,
        "expected_version": version,
        "supplier": "Replacement Marine Supply",
        "delivery_terms": "Priority delivery",
        "reason": "Two extra upgraded seals needed",
    }


def propose(client, record):
    headers = sign_in(client, "chloe")
    response = mutate(
        client,
        f"/requisitions/{record['id']}/po-proposals",
        proposal_payload(record["version"]),
        headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def proposal_action(client, record, action, user, reason="", key=None):
    headers = sign_in(client, user)
    return mutate(
        client,
        f"/requisitions/{record['id']}/po-proposals/{action}",
        {
            "expected_version": record["version"],
            "proposal_id": record["po_proposals"][0]["id"],
            "reason": reason,
        },
        headers,
        key,
    )


def test_revision_requires_review_then_exact_issuance_preserving_history(
    client, application
):
    record = issued(client)
    original = record["purchase_order"]
    proposed = propose(client, record)
    assert proposed["purchase_order"] == original
    assert proposed["po_proposals"][0]["total_myr"] == "2640.00"
    assert proposal_action(client, proposed, "issue", "chloe").status_code == 409
    reviewed = proposal_action(client, proposed, "approve", "ben").json()
    assert reviewed["purchase_order"] == original
    assert reviewed["po_proposals"][0]["status"] == "approved"
    result = proposal_action(client, reviewed, "issue", "chloe").json()
    po = result["purchase_order"]
    assert (
        po["id"] == original["id"] and po["revision"] == 2 and po["total"] == "2640.00"
    )
    assert po["snapshot"] == proposed["po_proposals"][0]["snapshot"]
    assert result["po_history"] == [original, po]
    assert result["total"] == "2000.00" and result["items"] == data()["items"]
    assert result["po_proposals"][0]["decided_by"] == "ben"
    assert result["po_proposals"][0]["status"] == "issued"
    assert [e["action"] for e in result["events"]][-3:] == [
        "propose_po",
        "approve_po",
        "issue_po_revision",
    ]
    token = client.cookies.get(COOKIE)
    with TestClient(create_app(application.state.settings)) as restarted:
        restarted.cookies.set(COOKIE, token, path="/api")
        assert restarted.get(f"/api/v1/requisitions/{record['id']}").json() == result
    assert client.get(f"/api/v1/purchase-orders/{po['id']}").json() == po
    third = propose(client, result)
    assert third["po_proposals"][0]["base_revision"] == 2
    third = proposal_action(client, third, "approve", "ben").json()
    third = proposal_action(client, third, "issue", "chloe").json()
    assert [p["revision"] for p in third["po_history"]] == [1, 2, 3]


def test_reapproval_can_authorize_first_order_above_original_estimate(client):
    record = propose(client, approved(client))
    headers = sign_in(client, "chloe")
    assert (
        mutate(
            client,
            f"/requisitions/{record['id']}/purchase-order",
            po_payload(record["version"]),
            headers,
        ).status_code
        == 409
    )
    record = proposal_action(client, record, "approve", "ben").json()
    result = proposal_action(client, record, "issue", "chloe").json()
    assert result["purchase_order"]["revision"] == 1
    assert result["purchase_order"]["total"] == "2640.00"


def test_return_preserves_terms_and_requires_new_review(client):
    record = issued(client)
    original = record["purchase_order"]
    proposed = propose(client, record)
    assert proposal_action(client, proposed, "return", "ben", " ").status_code == 422
    returned = proposal_action(
        client, proposed, "return", "ben", "Explain upgraded scope"
    ).json()
    assert returned["po_proposals"][0]["decision_reason"] == "Explain upgraded scope"
    assert returned["purchase_order"] == original
    assert proposal_action(client, returned, "issue", "chloe").status_code == 409
    replacement = propose(client, returned)
    assert len(replacement["po_proposals"]) == 2
    assert replacement["po_proposals"][0]["status"] == "pending"
    assert replacement["po_proposals"][1]["status"] == "returned"


def test_proposal_roles_stale_versions_and_single_open_proposal(client, application):
    record = issued(client)
    path = f"/requisitions/{record['id']}/po-proposals"
    for user in ("aina", "ben", "dinesh", "eva"):
        headers = sign_in(client, user)
        assert mutate(client, path, proposal_payload(4), headers).status_code == 403
    headers = sign_in(client, "chloe")
    assert mutate(client, path, proposal_payload(3), headers).status_code == 409
    proposed = propose(client, record)
    headers = sign_in(client, "chloe")
    assert mutate(client, path, proposal_payload(5), headers).status_code == 409
    for user in ("aina", "chloe", "dinesh", "eva"):
        assert proposal_action(client, proposed, "approve", user).status_code == 403
    reviewed = proposal_action(client, proposed, "approve", "ben").json()
    assert proposal_action(client, proposed, "approve", "ben").status_code == 409
    assert proposal_action(client, reviewed, "approve", "ben").status_code == 409
    for user in ("aina", "ben", "dinesh", "eva"):
        assert proposal_action(client, reviewed, "issue", user).status_code == 403
    # A role change must not permit the original proposer to self-approve.
    with application.state.db.connect() as connection:
        connection.execute(
            "UPDATE po_proposals SET status='pending' WHERE id=%s",
            (reviewed["po_proposals"][0]["id"],),
        )
        connection.execute("UPDATE users SET role='approver' WHERE id='chloe'")
    try:
        assert proposal_action(client, reviewed, "approve", "chloe").status_code == 403
    finally:
        with application.state.db.connect() as connection:
            connection.execute("UPDATE users SET role='buyer' WHERE id='chloe'")


def test_proposal_snapshot_and_revision_are_database_immutable(client, application):
    import psycopg

    record = propose(client, issued(client))
    proposal_id = record["po_proposals"][0]["id"]
    record = proposal_action(client, record, "approve", "ben").json()
    record = proposal_action(client, record, "issue", "chloe").json()
    for statement, identifier in [
        ("UPDATE po_proposals SET total_myr=1 WHERE id=%s", proposal_id),
        ("DELETE FROM po_proposals WHERE id=%s", proposal_id),
        ("UPDATE po_revisions SET total_myr=1 WHERE proposal_id=%s", proposal_id),
        ("DELETE FROM po_revisions WHERE proposal_id=%s", proposal_id),
    ]:
        with pytest.raises(psycopg.errors.RaiseException):
            with application.state.db.connect() as connection:
                connection.execute(statement, (identifier,))


def test_revision_issuance_retry_concurrency_and_payload_injection(client, application):
    record = propose(client, issued(client))
    record = proposal_action(client, record, "approve", "ben").json()
    headers = sign_in(client, "chloe")
    token = client.cookies.get(COOKIE)
    path = f"/requisitions/{record['id']}/po-proposals/issue"
    body = {
        "expected_version": record["version"],
        "proposal_id": record["po_proposals"][0]["id"],
    }
    assert (
        mutate(
            client, path, {**body, "supplier": "Injected terms"}, headers
        ).status_code
        == 422
    )
    assert (
        mutate(client, path, {**body, "proposal_id": str(uuid4())}, headers).status_code
        == 409
    )
    key = str(uuid4())

    def issue(_):
        with TestClient(application) as other:
            other.cookies.set(COOKIE, token, path="/api")
            return mutate(other, path, body, headers, key)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(issue, range(2)))
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()["po_history"]) == 2
    assert (
        mutate(
            client, path, {**body, "expected_version": record["version"] + 1}, headers
        ).status_code
        == 409
    )


def test_revision_failure_rolls_back_issuance_state_audit_and_retry(
    client, application
):
    record = propose(client, issued(client))
    record = proposal_action(client, record, "approve", "ben").json()
    with application.state.db.connect() as connection:
        connection.execute(
            "CREATE FUNCTION fail_revision_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='issue_po_revision' THEN RAISE EXCEPTION 'synthetic failure'; END IF; RETURN NEW; END; $$"
        )
        connection.execute(
            "CREATE TRIGGER fail_revision BEFORE INSERT ON audit_events FOR EACH ROW EXECUTE FUNCTION fail_revision_audit()"
        )
    key = str(uuid4())
    try:
        assert (
            proposal_action(client, record, "issue", "chloe", key=key).status_code
            == 500
        )
        assert client.get(f"/api/v1/requisitions/{record['id']}").json() == record
    finally:
        with application.state.db.connect() as connection:
            connection.execute("DROP TRIGGER fail_revision ON audit_events")
            connection.execute("DROP FUNCTION fail_revision_audit()")
    assert (
        proposal_action(client, record, "issue", "chloe", key=key).json()[
            "purchase_order"
        ]["revision"]
        == 2
    )


def test_proposal_validation_and_csrf(client):
    record = approved(client)
    path = f"/requisitions/{record['id']}/po-proposals"
    headers = sign_in(client, "chloe")
    assert mutate(client, path, proposal_payload(3), {}).status_code == 403
    for field, value in [("reason", " "), ("supplier", " "), ("items", [])]:
        assert (
            mutate(
                client, path, {**proposal_payload(3), field: value}, headers
            ).status_code
            == 422
        )
    body = proposal_payload(3)
    body["kind"] = "service"
    body["items"][0]["quantity"] = "1.5"
    assert mutate(client, path, body, headers).status_code == 422


def test_competing_distinct_revision_commands_commit_once(client, application):
    record = propose(client, issued(client))
    record = proposal_action(client, record, "approve", "ben").json()
    headers = sign_in(client, "chloe")
    token = client.cookies.get(COOKIE)

    def issue(_):
        with TestClient(application) as other:
            other.cookies.set(COOKIE, token, path="/api")
            return mutate(
                other,
                f"/requisitions/{record['id']}/po-proposals/issue",
                {
                    "expected_version": record["version"],
                    "proposal_id": record["po_proposals"][0]["id"],
                },
                headers,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(issue, range(2))) == [200, 409]
    saved = client.get(f"/api/v1/requisitions/{record['id']}").json()
    assert len(saved["po_history"]) == 2
    assert len([e for e in saved["events"] if e["action"] == "issue_po_revision"]) == 1


def test_proposals_require_approved_pr_and_share_parent_visibility(client, application):
    record, _ = submitted(client)
    headers = sign_in(client, "chloe")
    assert (
        mutate(
            client,
            f"/requisitions/{record['id']}/po-proposals",
            proposal_payload(2),
            headers,
        ).status_code
        == 409
    )
    headers = sign_in(client, "ben")
    record = mutate(
        client,
        f"/requisitions/{record['id']}/approve",
        {"expected_version": 2},
        headers,
    ).json()
    record = propose(client, record)
    with application.state.db.connect() as connection:
        connection.execute(
            "INSERT INTO users (id,name,role,password_hash) SELECT 'other','Other','requester',password_hash FROM users WHERE id='aina' ON CONFLICT DO NOTHING"
        )
    headers = sign_in(client, "other")
    assert client.get(f"/api/v1/requisitions/{record['id']}").status_code == 404
    assert (
        mutate(
            client,
            f"/requisitions/{record['id']}/po-proposals/approve",
            {
                "expected_version": record["version"],
                "proposal_id": record["po_proposals"][0]["id"],
            },
            headers,
        ).status_code
        == 404
    )
    sign_in(client, "aina")
    assert (
        client.get(f"/api/v1/requisitions/{record['id']}").json()["po_proposals"]
        == record["po_proposals"]
    )


def receive_payload(record, accepted="6", damaged="0", rejected="0", index=0):
    return {
        "expected_version": record["version"],
        "po_revision": record["purchase_order"]["revision"],
        "received_on": "2026-10-26",
        "reference": "DELIVERY-001",
        "notes": "Inspected delivery" if damaged != "0" or rejected != "0" else "",
        "lines": [
            {
                "line_index": index,
                "accepted": accepted,
                "damaged": damaged,
                "rejected": rejected,
            }
        ],
    }


def receive_record(client, record, accepted="6", damaged="0", rejected="0", key=None):
    headers = sign_in(client, "dinesh")
    return mutate(
        client,
        f"/requisitions/{record['id']}/receipts",
        receive_payload(record, accepted, damaged, rejected),
        headers,
        key,
    )


def compatible_proposal(client, record, quantity="12"):
    body = proposal_payload(record["version"])
    body["supplier"] = record["purchase_order"]["snapshot"]["supplier"]
    body["items"][0].update(
        description=record["purchase_order"]["snapshot"]["items"][0]["description"],
        quantity=quantity,
    )
    headers = sign_in(client, "chloe")
    response = mutate(
        client, f"/requisitions/{record['id']}/po-proposals", body, headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_multiple_goods_receipts_count_only_accepted_and_preserve_terms(
    client, application
):
    record = issued(client)
    original = record["purchase_order"]
    first = receive_record(client, record, "6", "2", "1")
    assert first.status_code == 201, first.text
    record = first.json()
    line = record["fulfilment"]["lines"][0]
    assert line == {
        "line_index": 0,
        "description": "Pump seal",
        "ordered": "10.00",
        "accepted": "6.00",
        "damaged": "2.00",
        "rejected": "1.00",
        "outstanding": "4.00",
    }
    assert record["fulfilment"]["status"] == "partial"
    assert record["purchase_order"] == original
    assert record["events"][-1]["actor"] == "Dinesh"
    record = receive_record(client, record, "4").json()
    assert record["fulfilment"]["status"] == "complete"
    assert len(record["receipts"]) == 2
    assert record["receipts"][0]["po_snapshot"] == original["snapshot"]
    assert all(receipt["po_revision"] == 1 for receipt in record["receipts"])
    assert receive_record(client, record, ".01").status_code == 409
    token = client.cookies.get(COOKIE)
    with TestClient(create_app(application.state.settings)) as restarted:
        restarted.cookies.set(COOKIE, token, path="/api")
        assert restarted.get(f"/api/v1/requisitions/{record['id']}").json() == record


def test_only_receiver_can_receive_issued_current_po(client):
    record = approved(client)
    headers = sign_in(client, "dinesh")
    body = {
        "expected_version": 3,
        "po_revision": 1,
        "received_on": "2026-10-26",
        "reference": "DN-1",
        "lines": [{"line_index": 0, "accepted": "1"}],
    }
    assert (
        mutate(
            client, f"/requisitions/{record['id']}/receipts", body, headers
        ).status_code
        == 409
    )
    headers = sign_in(client, "chloe")
    record = mutate(
        client, f"/requisitions/{record['id']}/purchase-order", po_payload(), headers
    ).json()
    body = receive_payload(record)
    path = f"/requisitions/{record['id']}/receipts"
    for user in ("aina", "ben", "chloe", "eva"):
        headers = sign_in(client, user)
        assert mutate(client, path, body, headers).status_code == 403
    headers = sign_in(client, "dinesh")
    assert mutate(client, path, body, {}).status_code == 403
    assert mutate(client, path, {**body, "po_revision": 2}, headers).status_code == 409
    assert (
        mutate(client, path, {**body, "expected_version": 3}, headers).status_code
        == 409
    )
    assert mutate(client, path, {**body, "kind": "service"}, headers).status_code == 422


def test_pending_change_does_not_increase_receivable_quantity(client):
    record = compatible_proposal(client, issued(client))
    assert record["po_proposals"][0]["snapshot"]["items"][0]["quantity"] == "12"
    assert receive_record(client, record, "11").status_code == 409
    record = receive_record(client, record, "6").json()
    original_receipt = record["receipts"][0]
    assert record["fulfilment"]["lines"][0]["outstanding"] == "4.00"
    assert record["po_proposals"][0]["status"] == "pending"
    record = proposal_action(client, record, "approve", "ben").json()
    record = proposal_action(client, record, "issue", "chloe").json()
    assert record["fulfilment"]["lines"][0]["outstanding"] == "6.00"
    assert record["receipts"][0] == original_receipt
    record = receive_record(client, record, "6").json()
    assert record["fulfilment"]["status"] == "complete"
    assert [r["po_revision"] for r in record["receipts"]] == [1, 2]


def test_receipt_after_approval_requires_issuance_revalidation_and_can_return(client):
    record = compatible_proposal(client, issued(client), quantity="8")
    record = proposal_action(client, record, "approve", "ben").json()
    record = receive_record(client, record, "9").json()
    rejected = proposal_action(client, record, "issue", "chloe")
    assert (
        rejected.status_code == 409 and "already accepted" in rejected.json()["detail"]
    )
    saved = client.get(f"/api/v1/requisitions/{record['id']}").json()
    assert saved == record and saved["purchase_order"]["revision"] == 1
    record = proposal_action(
        client, record, "return", "ben", "Nine accepted; update remaining quantity"
    ).json()
    assert record["po_proposals"][0]["status"] == "returned"
    record = compatible_proposal(client, record)
    record = proposal_action(client, record, "approve", "ben").json()
    record = proposal_action(client, record, "issue", "chloe").json()
    assert record["fulfilment"]["lines"][0]["outstanding"] == "3.00"


def test_receiving_freezes_counterparty_type_and_line_identity(client):
    record = receive_record(client, issued(client), "6").json()
    body = proposal_payload(record["version"])
    body["supplier"] = record["purchase_order"]["snapshot"]["supplier"]
    body["items"][0].update(description="Pump seal", quantity="12")
    headers = sign_in(client, "chloe")
    path = f"/requisitions/{record['id']}/po-proposals"
    for field, value in [("supplier", "Different Supplier"), ("kind", "service")]:
        assert mutate(client, path, {**body, field: value}, headers).status_code == 409
    for line in [
        {"description": "Different item", "quantity": "12", "unit_price": "200"},
        {"description": "Pump seal", "quantity": "5", "unit_price": "200"},
    ]:
        assert (
            mutate(client, path, {**body, "items": [line]}, headers).status_code == 409
        )
    # New scope can be appended without changing earlier receipt references.
    body["items"].append(
        {"description": "New extra item", "quantity": "2", "unit_price": "10"}
    )
    record = mutate(client, path, body, headers).json()
    record = proposal_action(client, record, "approve", "ben").json()
    record = proposal_action(client, record, "issue", "chloe").json()
    assert record["fulfilment"]["lines"][0]["accepted"] == "6.00"
    assert record["fulfilment"]["lines"][1]["accepted"] == "0.00"


@pytest.mark.parametrize(
    "line,notes",
    [
        ({"line_index": 0, "accepted": "-1"}, ""),
        ({"line_index": 0, "accepted": "1.001"}, ""),
        ({"line_index": 0, "accepted": "0"}, ""),
        ({"line_index": 0, "accepted": "1", "damaged": "1"}, " "),
        ({"line_index": 0, "accepted": "1", "rejected": "1"}, ""),
        ({"line_index": 1, "accepted": "1"}, ""),
    ],
)
def test_receipt_validation(client, line, notes):
    record = issued(client)
    headers = sign_in(client, "dinesh")
    body = {**receive_payload(record), "lines": [line], "notes": notes}
    assert (
        mutate(
            client, f"/requisitions/{record['id']}/receipts", body, headers
        ).status_code
        == 422
    )
    saved = client.get(f"/api/v1/requisitions/{record['id']}").json()
    assert saved["receipts"] == [] and saved["version"] == record["version"]


def test_receipt_total_duplicate_line_and_idempotency(client):
    record = issued(client)
    headers = sign_in(client, "dinesh")
    body = receive_payload(record, "6", "3", "2")
    path = f"/requisitions/{record['id']}/receipts"
    assert mutate(client, path, body, headers).status_code == 409
    body = receive_payload(record)
    assert (
        mutate(client, path, {**body, "lines": body["lines"] * 2}, headers).status_code
        == 422
    )
    key = str(uuid4())
    first = mutate(client, path, body, headers, key)
    again = mutate(client, path, body, headers, key)
    assert (
        first.status_code == again.status_code == 201 and first.json() == again.json()
    )
    assert len(first.json()["receipts"]) == 1
    assert (
        mutate(
            client, path, {**body, "reference": "Different note"}, headers, key
        ).status_code
        == 409
    )


def test_service_acceptance_supports_partial_whole_milestones(client):
    headers = sign_in(client)
    body = data()
    body["kind"] = "service"
    body["items"][0].update(description="Inspection milestone", quantity="3")
    record = mutate(client, "/requisitions", body, headers).json()
    path = f"/requisitions/{record['id']}"
    record = mutate(client, path + "/submit", {"expected_version": 1}, headers).json()
    headers = sign_in(client, "ben")
    record = mutate(client, path + "/approve", {"expected_version": 2}, headers).json()
    headers = sign_in(client, "chloe")
    record = mutate(client, path + "/purchase-order", po_payload(), headers).json()
    assert receive_record(client, record, "1.5").status_code == 422
    assert receive_record(client, record, "1", "1").status_code == 422
    record = receive_record(client, record, "1", "0", "1").json()
    assert record["receipts"][0]["number"].startswith("SA-")
    assert (
        record["fulfilment"]["status"] == "partial"
        and record["fulfilment"]["lines"][0]["outstanding"] == "2.00"
    )
    record = receive_record(client, record, "2").json()
    assert record["fulfilment"]["status"] == "complete"


def test_concurrent_receipts_cannot_over_accept(client, application):
    record = issued(client)
    headers = sign_in(client, "dinesh")
    token = client.cookies.get(COOKIE)

    def receive(_):
        with TestClient(application) as other:
            other.cookies.set(COOKIE, token, path="/api")
            return mutate(
                other,
                f"/requisitions/{record['id']}/receipts",
                receive_payload(record),
                headers,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(receive, range(2))) == [201, 409]
    saved = client.get(f"/api/v1/requisitions/{record['id']}").json()
    assert (
        saved["fulfilment"]["lines"][0]["accepted"] == "6.00"
        and len(saved["receipts"]) == 1
    )


def test_receipt_audit_failure_rolls_back_and_receipt_is_immutable(client, application):
    import psycopg

    record = issued(client)
    with application.state.db.connect() as connection:
        connection.execute(
            "CREATE FUNCTION fail_receipt_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='receive' THEN RAISE EXCEPTION 'synthetic failure'; END IF; RETURN NEW; END; $$"
        )
        connection.execute(
            "CREATE TRIGGER fail_receipt BEFORE INSERT ON audit_events FOR EACH ROW EXECUTE FUNCTION fail_receipt_audit()"
        )
    key = str(uuid4())
    try:
        assert receive_record(client, record, key=key).status_code == 500
        assert client.get(f"/api/v1/requisitions/{record['id']}").json() == record
    finally:
        with application.state.db.connect() as connection:
            connection.execute("DROP TRIGGER fail_receipt ON audit_events")
            connection.execute("DROP FUNCTION fail_receipt_audit()")
    saved = receive_record(client, record, key=key).json()
    for statement in [
        "UPDATE receipts SET notes='changed' WHERE id=%s",
        "DELETE FROM receipts WHERE id=%s",
    ]:
        with pytest.raises(psycopg.errors.RaiseException):
            with application.state.db.connect() as connection:
                connection.execute(statement, (saved["receipts"][0]["id"],))


def invoice_payload(record, number="SUP-001", quantity="6", price="200.00"):
    return {
        "expected_version": record["version"],
        "po_revision": record["purchase_order"]["revision"],
        "supplier": record["purchase_order"]["snapshot"]["supplier"],
        "invoice_number": number,
        "invoice_date": "2026-10-26",
        "evidence_reference": number + ".pdf",
        "receipt_ids": [receipt["id"] for receipt in record["receipts"]],
        "lines": [{"line_index": 0, "quantity": quantity, "unit_price": price}],
    }


def capture_invoice(client, record, number="SUP-001", quantity="6", price="200.00"):
    headers = sign_in(client, "eva")
    return mutate(
        client,
        f"/requisitions/{record['id']}/invoices",
        invoice_payload(record, number, quantity, price),
        headers,
    )


def review_invoice(
    client,
    record,
    outcome="reviewed",
    reason="Checked supplier document and receiving evidence",
    invoice_id=None,
    key=None,
):
    headers = sign_in(client, "eva")
    return mutate(
        client,
        f"/requisitions/{record['id']}/invoices/review",
        {
            "expected_version": record["version"],
            "invoice_id": invoice_id or record["invoices"][-1]["id"],
            "outcome": outcome,
            "reason": reason,
        },
        headers,
        key,
    )


def test_ten_ordered_six_accepted_invoice_1200_review_leaves_four(client, application):
    record = approved(client)
    headers = sign_in(client, "chloe")
    record = mutate(
        client,
        f"/requisitions/{record['id']}/purchase-order",
        {**po_payload(), "unit_prices": ["200"]},
        headers,
    ).json()
    record = receive_record(client, record).json()
    before = record["fulfilment"]
    receipt = record["receipts"][0]
    response = capture_invoice(client, record)
    assert response.status_code == 201, response.text
    record = response.json()
    invoice = record["invoices"][0]
    assert invoice["total"] == "1200.00" and invoice["status"] == "awaiting_review"
    assert invoice["receipt_evidence"] == [receipt]
    assert record["invoice_checks"][invoice["id"]]["warnings"] == []
    record = review_invoice(client, record).json()
    assert record["invoices"][0]["status"] == "reviewed"
    assert record["invoices"][0]["reviews"][0]["actor"] == "Eva"
    assert (
        record["fulfilment"] == before
        and record["fulfilment"]["lines"][0]["outstanding"] == "4.00"
    )
    assert not any(
        key in record["invoices"][0] for key in ("paid", "payment_status", "reconciled")
    )
    assert record["status"] == "approved"
    token = client.cookies.get(COOKIE)
    with TestClient(create_app(application.state.settings)) as restarted:
        restarted.cookies.set(COOKIE, token, path="/api")
        assert restarted.get(f"/api/v1/requisitions/{record['id']}").json() == record


def test_invoice_before_receipt_clarification_followup_preserves_review_checks(client):
    record = capture_invoice(client, issued(client)).json()
    invoice = record["invoices"][0]
    assert "exceeds accepted" in " ".join(
        record["invoice_checks"][invoice["id"]]["warnings"]
    )
    record = review_invoice(
        client, record, "needs_clarification", "Awaiting delivery evidence"
    ).json()
    original_review = record["invoices"][0]["reviews"][0]
    record = receive_record(client, record).json()
    record = review_invoice(
        client, record, "reviewed", "Delivery evidence now inspected"
    ).json()
    assert record["invoices"][0]["reviews"][0] == original_review
    assert len(record["invoices"][0]["reviews"]) == 2
    assert record["fulfilment"]["lines"][0]["outstanding"] == "4.00"
    assert (
        review_invoice(client, record, "rejected", "Overwrite attempt").status_code
        == 409
    )


def test_multiple_invoices_all_outcomes_and_combined_claim_warning(client):
    record = receive_record(client, issued(client)).json()
    record = capture_invoice(client, record, "SUP-A", "4", "190").json()
    first = record["invoices"][0]["id"]
    record = review_invoice(client, record).json()
    record = capture_invoice(client, record, "SUP-B", "4", "190").json()
    second = record["invoices"][1]["id"]
    assert "combined non-rejected invoices exceed accepted" in " ".join(
        record["invoice_checks"][second]["warnings"]
    )
    record = review_invoice(client, record, "rejected", "Overlapping claim").json()
    assert record["invoice_checks"][first]["lines"][0]["combined_claimed"] == "4.00"
    record = capture_invoice(client, record, "SUP-C", "2", "190").json()
    record = review_invoice(
        client, record, "needs_clarification", "Confirm work reference"
    ).json()
    assert [invoice["status"] for invoice in record["invoices"]] == [
        "reviewed",
        "rejected",
        "needs_clarification",
    ]
    assert record["fulfilment"]["lines"][0]["outstanding"] == "4.00"


def test_invoice_role_state_csrf_and_review_reason_boundaries(client):
    record = approved(client)
    headers = sign_in(client, "eva")
    payload = {
        "expected_version": 3,
        "po_revision": 1,
        "supplier": "Demo Supply",
        "invoice_number": "BEFORE-PO",
        "invoice_date": "2026-10-26",
        "evidence_reference": "invoice.pdf",
        "lines": [{"line_index": 0, "quantity": "6", "unit_price": "200"}],
    }
    assert (
        mutate(
            client, f"/requisitions/{record['id']}/invoices", payload, headers
        ).status_code
        == 409
    )
    headers = sign_in(client, "chloe")
    record = mutate(
        client, f"/requisitions/{record['id']}/purchase-order", po_payload(), headers
    ).json()
    path = f"/requisitions/{record['id']}/invoices"
    for user in ("aina", "ben", "chloe", "dinesh"):
        headers = sign_in(client, user)
        assert mutate(client, path, invoice_payload(record), headers).status_code == 403
    headers = sign_in(client, "eva")
    assert mutate(client, path, invoice_payload(record), {}).status_code == 403
    assert (
        mutate(
            client, path, {**invoice_payload(record), "paid": True}, headers
        ).status_code
        == 422
    )
    record = capture_invoice(client, record).json()
    for user in ("aina", "ben", "chloe", "dinesh"):
        headers = sign_in(client, user)
        assert (
            mutate(
                client,
                path + "/review",
                {
                    "expected_version": record["version"],
                    "invoice_id": record["invoices"][0]["id"],
                    "outcome": "reviewed",
                    "reason": "Checked",
                },
                headers,
            ).status_code
            == 403
        )
    for outcome in ("reviewed", "needs_clarification", "rejected"):
        assert review_invoice(client, record, outcome, " ").status_code == 422
    assert review_invoice(client, record, "paid", "Invalid outcome").status_code == 422
    assert review_invoice(client, record, invoice_id=str(uuid4())).status_code == 404


def test_duplicate_supplier_invoice_number_and_replays(client):
    record = issued(client)
    headers = sign_in(client, "eva")
    path = f"/requisitions/{record['id']}/invoices"
    body = invoice_payload(record)
    key = str(uuid4())
    first = mutate(client, path, body, headers, key)
    again = mutate(client, path, body, headers, key)
    assert (
        first.status_code == again.status_code == 201 and first.json() == again.json()
    )
    saved = first.json()
    assert (
        mutate(
            client,
            path,
            {
                **body,
                "expected_version": saved["version"],
                "invoice_number": "  sup-001 ",
            },
            headers,
        ).status_code
        == 409
    )
    assert (
        mutate(
            client, path, {**body, "invoice_number": "Different"}, headers, key
        ).status_code
        == 409
    )
    other = issued(client)
    assert capture_invoice(client, other, "SUP-001").status_code == 409
    assert (
        len(client.get(f"/api/v1/requisitions/{record['id']}").json()["invoices"]) == 1
    )


@pytest.mark.parametrize(
    "change",
    [
        {"lines": []},
        {"supplier": " "},
        {"invoice_number": " "},
        {"lines": [{"line_index": 0, "quantity": "0", "unit_price": "200"}]},
        {"lines": [{"line_index": 0, "quantity": "1.001", "unit_price": "200"}]},
        {"lines": [{"line_index": 0, "quantity": "1", "unit_price": "-1"}]},
        {"lines": [{"line_index": 1, "quantity": "1", "unit_price": "200"}]},
        {"po_revision": 99},
        {"receipt_ids": [str(uuid4())]},
    ],
)
def test_invoice_validation(client, change):
    record = issued(client)
    headers = sign_in(client, "eva")
    assert (
        mutate(
            client,
            f"/requisitions/{record['id']}/invoices",
            {**invoice_payload(record), **change},
            headers,
        ).status_code
        == 422
    )


def test_invoice_decimal_amounts_and_discrepancy_review_are_not_payment(client):
    record = issued(client)
    response = capture_invoice(client, record, quantity="3", price="0.10")
    assert response.status_code == 201
    record = response.json()
    assert record["invoices"][0]["total"] == "0.30"
    assert "unit price differs" in " ".join(
        record["invoice_checks"][record["invoices"][0]["id"]]["warnings"]
    )
    record = review_invoice(
        client,
        record,
        reason="Recorded review of discrepancy; no payment authorization",
    ).json()
    assert (
        record["invoices"][0]["status"] == "reviewed"
        and record["fulfilment"]["status"] == "awaiting"
    )


def test_invoice_guard_rechecks_changes_approved_before_capture(client):
    record = propose(
        client, issued(client)
    )  # Changes supplier and item identity, no receipts yet.
    record = proposal_action(client, record, "approve", "ben").json()
    record = capture_invoice(client, record).json()
    assert proposal_action(client, record, "issue", "chloe").status_code == 409
    record = proposal_action(
        client,
        record,
        "return",
        "ben",
        "Invoice evidence now exists; preserve linked scope",
    ).json()
    record = compatible_proposal(client, record)
    record = proposal_action(client, record, "approve", "ben").json()
    record = proposal_action(client, record, "issue", "chloe").json()
    assert (
        record["invoices"][0]["po_revision"] == 1
        and record["purchase_order"]["revision"] == 2
    )
    assert record["invoices"][0]["po_snapshot"]["items"][0]["unit_price"] == "190.00"


def test_historical_invoice_scope_is_flagged_instead_of_using_new_receipts(client):
    record = propose(client, issued(client))
    record = proposal_action(client, record, "approve", "ben").json()
    record = proposal_action(client, record, "issue", "chloe").json()
    record = receive_record(client, record).json()
    headers = sign_in(client, "eva")
    body = invoice_payload(record)
    body["po_revision"] = 1
    body["supplier"] = record["po_history"][0]["snapshot"]["supplier"]
    record = mutate(
        client, f"/requisitions/{record['id']}/invoices", body, headers
    ).json()
    checks = record["invoice_checks"][record["invoices"][0]["id"]]
    assert checks["lines"][0]["accepted"] == "0.00"
    assert "historical scope differs" in " ".join(checks["warnings"])


def test_foreign_receipts_and_foreign_invoice_review_are_rejected(client):
    first = receive_record(client, issued(client)).json()
    first = capture_invoice(client, first).json()
    second = issued(client)
    headers = sign_in(client, "eva")
    body = invoice_payload(second, "SUP-002")
    body["receipt_ids"] = [first["receipts"][0]["id"]]
    assert (
        mutate(
            client, f"/requisitions/{second['id']}/invoices", body, headers
        ).status_code
        == 422
    )
    second = capture_invoice(client, second, "SUP-002").json()
    assert (
        review_invoice(
            client, second, invoice_id=first["invoices"][0]["id"]
        ).status_code
        == 404
    )


def test_invoice_and_review_immutability_and_failed_audit_retry(client, application):
    import psycopg

    record = issued(client)
    headers = sign_in(client, "eva")
    path = f"/requisitions/{record['id']}/invoices"
    body = invoice_payload(record)
    key = str(uuid4())
    with application.state.db.connect() as connection:
        connection.execute(
            "CREATE FUNCTION fail_invoice_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action IN ('capture_invoice','review_invoice') THEN RAISE EXCEPTION 'synthetic failure'; END IF; RETURN NEW; END; $$"
        )
        connection.execute(
            "CREATE TRIGGER fail_invoice BEFORE INSERT ON audit_events FOR EACH ROW EXECUTE FUNCTION fail_invoice_audit()"
        )
    try:
        assert mutate(client, path, body, headers, key).status_code == 500
        assert client.get("/api/v1" + path.rsplit("/invoices", 1)[0]).json() == record
    finally:
        with application.state.db.connect() as connection:
            connection.execute("DROP TRIGGER fail_invoice ON audit_events")
            connection.execute("DROP FUNCTION fail_invoice_audit()")
    record = mutate(client, path, body, headers, key).json()
    key = str(uuid4())
    with application.state.db.connect() as connection:
        connection.execute(
            "CREATE FUNCTION fail_review_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='review_invoice' THEN RAISE EXCEPTION 'synthetic failure'; END IF; RETURN NEW; END; $$"
        )
        connection.execute(
            "CREATE TRIGGER fail_review BEFORE INSERT ON audit_events FOR EACH ROW EXECUTE FUNCTION fail_review_audit()"
        )
    try:
        assert review_invoice(client, record, key=key).status_code == 500
        assert client.get(f"/api/v1/requisitions/{record['id']}").json() == record
    finally:
        with application.state.db.connect() as connection:
            connection.execute("DROP TRIGGER fail_review ON audit_events")
            connection.execute("DROP FUNCTION fail_review_audit()")
    record = review_invoice(client, record, key=key).json()
    for statement in [
        "UPDATE invoices SET total_myr=1 WHERE id=%s",
        "DELETE FROM invoices WHERE id=%s",
        "UPDATE invoice_reviews SET reason='changed' WHERE invoice_id=%s",
        "DELETE FROM invoice_reviews WHERE invoice_id=%s",
    ]:
        with pytest.raises(psycopg.errors.RaiseException):
            with application.state.db.connect() as connection:
                connection.execute(statement, (record["invoices"][0]["id"],))


def test_competing_invoice_reviews_commit_one_outcome(client, application):
    record = capture_invoice(client, issued(client)).json()
    headers = sign_in(client, "eva")
    token = client.cookies.get(COOKIE)

    def review(outcome):
        with TestClient(application) as other:
            other.cookies.set(COOKIE, token, path="/api")
            return mutate(
                other,
                f"/requisitions/{record['id']}/invoices/review",
                {
                    "expected_version": record["version"],
                    "invoice_id": record["invoices"][0]["id"],
                    "outcome": outcome,
                    "reason": "Concurrent review",
                },
                headers,
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(review, ["reviewed", "rejected"])) == [200, 409]
    saved = client.get(f"/api/v1/requisitions/{record['id']}").json()
    assert len(saved["invoices"][0]["reviews"]) == 1


def test_service_invoice_requires_whole_milestones_and_keeps_acceptance_open(client):
    headers = sign_in(client)
    body = data()
    body["kind"] = "service"
    body["items"][0].update(description="Inspection milestone", quantity="3")
    record = mutate(client, "/requisitions", body, headers).json()
    path = f"/requisitions/{record['id']}"
    record = mutate(client, path + "/submit", {"expected_version": 1}, headers).json()
    headers = sign_in(client, "ben")
    record = mutate(client, path + "/approve", {"expected_version": 2}, headers).json()
    headers = sign_in(client, "chloe")
    record = mutate(client, path + "/purchase-order", po_payload(), headers).json()
    assert capture_invoice(client, record, quantity="1.5").status_code == 422
    record = capture_invoice(client, record, quantity="1", price="190").json()
    record = review_invoice(
        client, record, "needs_clarification", "Await milestone acceptance evidence"
    ).json()
    assert record["fulfilment"]["lines"][0]["outstanding"] == "3.00"
    assert record["invoices"][0]["total"] == "190.00"
