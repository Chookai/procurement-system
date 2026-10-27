# PROC-015: Validate local Floci adapters and real Azure development contracts

Status: needs-triage
Progress: Not started
Type: Infrastructure
Priority: Normal
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 01, 04, 11

## Summary

Make local development reproducible and verify emulator assumptions against a small real Azure development environment.

## Proposed acceptance criteria

- [ ] Pin required images/packages and document supported SDK operations.
- [ ] Run the required storage and database contracts locally.
- [ ] Confirm pgvector extension availability rather than assuming it.
- [ ] Run equivalent limited development smoke checks in Azure when access is configured.
- [ ] Report emulator/managed-service differences explicitly.

## Open questions

- Real Azure subscription access and deployment approval are required before provisioning.

## References

- docs/architecture-direction.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.
