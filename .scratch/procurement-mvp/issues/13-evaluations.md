# PROC-013: Run versioned retrieval, answer and agent evaluations

> Archived migration snapshot (27 October 2026). Track current work in [PROC-013 / GitHub #14](https://github.com/Chookai/procurement-system/issues/14).

Status: needs-triage
Progress: Not started
Type: Evaluation
Priority: High
Milestone: Milestone 1
Owner: Unassigned
Blocked by: 02, 11, 12

## Summary

Turn the twelve seed cases into an executable regression harness with a real corpus and holdout cases.

## Proposed acceptance criteria

- [ ] Create the synthetic source corpus and structured snapshots required by the cases.
- [ ] Report retrieval quality separately from answer support and completeness.
- [ ] Check exact quantities, permissions and tool actions deterministically.
- [ ] Record corpus/dataset, prompts, parser, model and retrieval versions per run.
- [ ] Critical failures fail the run even when aggregate quality is high.
- [ ] Mocks are never reported as real RAG scores.

## Open questions

- Calibrate candidate quality targets and latency/cost budgets using the real development baseline, then freeze gates before scoring an independent holdout.
- Review passage labels, support rubrics and holdout coverage once the corpus exists.

## References

- evals/cases.jsonl
- learnings/rag-evaluation-plan.md

## Comments

Drafted from the procurement discovery conversation. Acceptance criteria and priorities require review; this ticket is not implementation-ready solely because it exists.

23 October 2026: Added the separate `learnings/` teaching workspace with a general/Azure lesson and reference. The canonical evaluation contract moved to `learnings/rag-evaluation-plan.md`; an old-path pointer remains. Educational widgets do not implement this ticket or establish real evaluation scores.

23 October 2026: actual baseline calibration and gate freezing are tracked here; PROC-002 now records the completed agreement of that protocol. Runtime/provider contracts passed separately and do not count as retrieval or answer-quality results.
