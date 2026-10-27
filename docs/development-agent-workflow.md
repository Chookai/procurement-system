# Development workflow: plan here → implement in Kilo → verify here

Accepted user direction, 27 October 2026. Planning, architecture decisions, specifications and local Markdown tickets stay in this conversation with the orchestrator. The user takes one ready ticket to Kilo Desktop with a cheaper model for implementation and initial testing. Verification returns here; the orchestrator owns the verification result and presents the evidence for the user's decision.

The existing application was built here before this handoff choice. No Kilo implementation or cross-harness integration has been tested yet. The interactive record is `learnings/reference/agent-workflow-report.html`.

## Responsibilities

| Stage | Owner | Required output |
|---|---|---|
| Plan and specify | User + orchestrator here | One approved, bounded ticket; acceptance and negative cases; constraints; required checks |
| Implement | Kilo Desktop + user-selected cheaper model | Focused branch/change, implementation tests, initial results and candidate commit |
| Verify | Orchestrator here; fresh-context review when needed | Independently executed checks, additional scenarios, acceptance comparison, reproducible findings and limits |
| Repair | Kilo Desktop | Fixes tied to findings, regression evidence and a new candidate commit |
| Decide | User | Inspect sensitive behavior and evidence; decide whether to accept/merge |

Fresh-context review may use a separate reviewer subagent here supplied with the spec and fixed code snapshot, rather than the implementation conversation. It is a review mechanism, not an additional implementation owner. Re-running the same tests in this long-running planning conversation alone is not an independent adversarial review.

Kilo's exact model, provider, authentication and filesystem/command permissions still need configuration in Kilo. This document records the user's process; it does not assert any particular Kilo integration has been installed or validated. Prior pi/Claude Code research is preserved in `development-agent-workflow-2026-10-23.md` as history, not an active instruction to use those harnesses.

## Manual handoff first

1. Prepare one implementation-ready local ticket here. Include scope, non-goals, acceptance examples, protected rules and relevant checks. Readiness is distinct from execution progress.
2. Start Kilo from the intended checkout/feature branch. Explicitly provide `AGENTS.md`, the ticket/spec and relevant glossary/ADRs. Do not assume another harness automatically loads these instructions.
3. Kilo implements and tests. It must not relax approved acceptance criteria, disable checks, edit credentials into source or silently expand scope. Changes to tests/CI/review rules must be called out for independent inspection.
4. Freeze the handoff with a candidate commit. Record the base and candidate SHAs, branch, ticket path, changed files, exact commands/exits, artifacts and incomplete checks. Stop Kilo editing while that snapshot is verified.
5. Return here with the ticket path, candidate SHA and evidence locations. Local commits are sufficient if both tools use this repository; separate clones need an explicit commit transfer/remote. A branch name or summary alone is insufficient.
6. Verify the fixed candidate in an isolated checkout when needed. Run required checks; add independent negative/adversarial cases. Read application code without repairing it during the verification pass. Supplemental tests and reports belong in the verifier's workspace/output area.
7. Send confirmed findings back to Kilo. Prefer a small reproduction and a test that fails on the defective version. Static concerns that cannot be executed remain clearly labelled, with a concrete code path and limits.
8. A repair creates a new SHA. Re-run affected checks and any required regression suite. After three repair/review rounds, reassess the design or ticket instead of expanding unrelated cleanup indefinitely.
9. Present the evidence to the user for acceptance. Keep human inspection for authorization, money/quantity rules, evidence immutability, migrations, CI and future agent action permissions. No automatic merge/deployment is configured.

## Verification evidence

Each result must identify its ticket, base/candidate commit, environment/lockfiles, commands with actual exit codes, results/artifacts, additional scenarios, findings, skipped or unavailable checks, and remaining limitations. Capture outputs from commands; do not treat either harness's narrative as execution evidence.

Use `passed`, `failed` and `not_run` for individual checks. A missing database/browser, a missing artifact or an unavailable provider is not a pass. Only explicitly required checks count toward the candidate verdict; irrelevant checks can be excluded with a reason in the approved ticket. Fresh context and a different model improve scrutiny but do not guarantee correctness.

Keep the approved spec/review rules anchored to the trusted base. The candidate must not redefine its own acceptance oracle. A verifier reports findings and evidence; it cannot replace the user's required acceptance or authorize procurement actions in the application.

### Implementer handoff template

```text
Ticket/spec path:
Approved scope and non-goals:
Base commit SHA:
Feature branch / checkout:
Acceptance examples and negative cases:
Required checks:
Protected rules / sensitive paths:

Return after implementation:
Candidate commit SHA:
Changed files:
Commands, exit codes and artifact paths:
Checks not run / unresolved questions:
Risks and how to undo the change:
```

### Return-to-verifier template

```text
Verify ticket <path> against base <SHA> and candidate <SHA>.
Implementation is frozen. Read trusted instructions/spec from the base.
Run the required checks and devise independent negative cases.
Do not repair application code or weaken tests during this pass.
For each finding: severity, file/line, expected/actual behavior,
reproduction or concrete code path, and evidence.
Return check results, artifacts, limits and whether required evidence
supports acceptance. New commits require appropriate rechecks.
```

## Maintained HTML records

Keep `learnings/reference/agent-workflow-report.html` as the workflow/index report. For each actual Kilo candidate, write a separate verification report under `learnings/reports/<ticket>-<short-sha>.html` and link it from the report log. Include the tested snapshot, requirements, actual execution evidence, findings and limitations. A later candidate gets a new entry rather than overwriting the earlier verdict. No Kilo candidate has been submitted yet, and no automatic report generator or verifier dispatcher is installed; reports can be authored here as part of each verification.

## Current automation boundaries

- Local Git baseline: `a592399`; existing application plus prepared GitHub Actions.
- Local job-equivalent verification passed: 75 backend tests, Linux frontend/prototype builds and documentation checks. These are historical checks, not a result for a future Kilo change.
- Hosted CI awaits a GitHub repository connection and first run.
- Existing browser scripts are local tools; portable fixture-based CI browser coverage is still proposed.
- `REVIEW.md`, a trusted verification runner and the portable browser CI job are proposed additions, not installed by this document update.
- No Kilo connector, automatic task dispatch, fresh review session, automatic repairs, merge or Azure deployment was launched.
- Production RAG retrieval/answer/citation/action evaluations remain separate from code verification and are not yet implemented.

This direction concerns development agents. The procurement application's OpenRouter/Agent Framework baseline and deferred Foundry decision remain unchanged.
