# PROC-002: Agree milestone acceptance and RAG release gates

Status: ready-for-agent
Progress: Done
Type: Decision
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 01

## Summary

Define measurable completion before converting this backlog into implementation-ready tickets.

## Proposed acceptance criteria

- [x] Specify the goods journey, restart durability and backend-permission completion gate.
- [x] Specify that partial receipt and reviewed invoice leave undelivered units outstanding.
- [x] Require a real retrieval-and-answer path with supported citations.
- [x] Define critical permission and unauthorized-action release gates.
- [x] Define a development-baseline calibration and holdout-freeze protocol; actual measurement is tracked in PROC-013.
- [x] Require user inspection of code, module map, request flow and evaluation results before milestone closure.

## Open questions

None for agreement of the completion contract. Actual model-quality calibration and performance measurement are implementation work tracked in PROC-013.

## References

- learnings/rag-evaluation-plan.md
- evals/cases.jsonl
- docs/milestone-1-definition-of-done.md
- .scratch/procurement-mvp/spec.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

22 October 2026: user explicitly requested an end-of-phase code inspection checkpoint. Foundry is excluded; the initial evaluation harness runs locally. Other milestone gates still need confirmation.

23 October 2026: drafted a concrete completion contract and specification for review. Proposed primary test seam: the HTTP API with real local storage/worker dependencies, deterministic model stubs for CI, separate real-provider RAG evaluations, and a few browser smoke journeys. User confirmation is pending; no ready-for-agent label or completed milestone is claimed.

23 October 2026: user approved the milestone plan, completion gates and testing boundary. Published the canonical specification as ready-for-agent. This decision ticket remains In progress / needs-info for actual baseline calibration and its architecture prerequisite; no implemented behavior or measured score is claimed.

23 October 2026: clarified the Decision ticket criteria as agreement of the contract, matching its title and summary. The approved contract completes this decision. Actual measurements move to PROC-013 rather than blocking the application needed to collect them. Earlier In progress comments are historical; no implemented behavior is claimed.
