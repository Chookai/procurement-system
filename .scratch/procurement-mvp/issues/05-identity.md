# PROC-005: Enforce role permissions behind the API

Status: ready-for-agent
Progress: In progress
Type: Security
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 01, 02, 04

## Summary

Replace the prototype role switcher with a verifiable identity boundary and server-side permissions.

Accepted local approach: five seeded users, server-verified signed tokens and backend role checks. Registration and production identity integration are outside this phase.

## Proposed acceptance criteria

- [x] Requester, approver, buyer, receiver and invoice reviewer permissions are enforced by the backend.
- [x] A requester cannot approve their own PR.
- [ ] UI and agent tools use the same authorization checks.
- [x] Unauthorized reads and writes fail without exposing restricted content.
- [x] Unsigned, modified or expired tokens do not authenticate a request; the browser cannot choose its effective role by editing request data.
- [x] Seeded accounts support the five fictional PIC roles without a registration flow.

## Open questions

The local login/session, visibility and role contracts are documented. Agent-tool integration remains unimplemented and must reuse the verified backend boundary when PROC-012 is built.

## References

- docs/first-application-slice.md

- docs/adr/0001-human-authorization.md
- docs/adr/0003-seeded-local-identity.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

23 October 2026: the user accepted the seeded local identity approach. Implementation has not started.

23 October 2026: Human API authorization is implemented and tested for this PR slice. The agent-tool acceptance criterion remains unchecked, so this broader ticket stays In progress. Completed downstream PR tickets use the already verified human API portion; they do not establish that future agent tools are safe. This does not close the overall milestone or implement PO, fulfilment, invoices or RAG.
