# Issue tracker: GitHub

Specs and tickets live in https://github.com/Chookai/procurement-system/issues. GitHub is the source of truth. Read the current issue before implementing or verifying work.

## Operations

Use the connected GitHub tools when available, or `gh` with `--repo Chookai/procurement-system`:

- Create: `gh issue create --repo Chookai/procurement-system --title "..." --body-file <file>`.
- Read: `gh issue view <number> --repo Chookai/procurement-system --json number,title,body,state,labels,comments`.
- List: `gh issue list --repo Chookai/procurement-system --state open --json number,title,body,state,labels`.
- Comment: `gh issue comment <number> --repo Chookai/procurement-system --body-file <file>`.
- Apply readiness: `gh issue edit <number> --repo Chookai/procurement-system --add-label <label>`; replace an old readiness label when changing readiness.
- Complete: update execution progress, then `gh issue close <number> --repo Chookai/procurement-system --reason completed`.

When a skill says publish, create a GitHub issue. When it says fetch a ticket, read the GitHub issue. Supply issue URLs/numbers and fixed base/candidate commit SHAs in Kilo/verifier handoffs.

## Readiness, execution and dependencies

The five configured labels describe readiness, not execution. Keep `Progress: Not started`, `In progress` or `Done` in the issue body; close completed tickets. Keep completion evidence in the issue or linked reports. The parent specification stays open until the full milestone, including RAG/evaluation and user inspection, is complete.

Link tickets to the parent specification issue. Use native GitHub sub-issues/dependencies where available; otherwise use a task list plus `Part of #<parent>` and `Blocked by: #<number>` references. A dependency is satisfied when its issue is completed/closed. Readiness alone does not remove a blocker.

## Migration archive

The existing `.scratch/procurement-mvp/` files and local tickets HTML are historical migration snapshots, not an active second tracker. Preserve their legacy PROC IDs and consult `docs/github-issue-migration.md` for GitHub links. Create/update work in GitHub, rather than adding new local Markdown tickets. Canonical domain/architecture/reference docs remain in the repository and can be linked from issues.

## Pull requests as a triage surface

**PRs as a request surface: no.**
