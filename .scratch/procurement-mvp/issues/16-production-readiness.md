# PROC-016: Define and verify the later production-readiness milestone

> Archived migration snapshot (27 October 2026). Track current work in [PROC-016 / GitHub #17](https://github.com/Chookai/procurement-system/issues/17).

Status: needs-triage
Progress: Not started
Type: Milestone
Priority: Normal
Milestone: Later
Owner: Unassigned
Blocked by: 02, 05, 13, 14, 15

## Summary

Plan the operational evidence needed before calling the system production-ready.

## Proposed acceptance criteria

- [ ] Define actual Azure deployment, identity, secret and network requirements.
- [ ] Exercise backup restoration, recovery, retry exhaustion and telemetry.
- [ ] Set measured concurrency, latency, cost and indexing-lag budgets.
- [ ] Document release/rollback and incident handling.
- [ ] Adopt external queue transport, caching or worker scaling only when justified.

## Open questions

- This is a separate later milestone, not a completion claim for the first journey.

## References

- docs/architecture-direction.md
- learnings/rag-evaluation-plan.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.
