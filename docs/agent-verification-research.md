# Research: verifying agent-written changes

Reviewed 27 October 2026. Research and proposals only; no reviewer, hook, CI gate or application change was installed. Baseline inspected: `a592399`.

## Guide takeaway

The Claude Code team describes layered verification: executable checks before a PR, fresh-context review, verification of candidate findings, security checks, risk-scaled human approval and rollback. It makes recurring defects part of reviewer evaluation, measures false positives as well as missed bugs, and limits review loops rather than continuously asking for more findings. Its adoption advice includes short repository-specific review guidance and evidence of testing and reversal. These are reported practices, not proof that the same outcomes will occur in our project. [Guide, published 15 October 2026](https://claude.dev/blog/solving-code-review-at-anthropic/).

## What the linked primary guidance establishes

- **Runnable verification is distinct from a completion claim.** The best-practices documentation recommends explicit pass/fail checks, actual command output or screenshots, review against a written specification, and a fresh reviewer that has not seen the author's conversation. Prompts are advisory; deterministic harness checks or CI enforce required steps. [Best practices: give Claude a check to run](https://code.claude.com/docs/en/best-practices#give-claude-a-check-to-run), [review against your spec](https://code.claude.com/docs/en/best-practices#review-against-your-spec).
- **“Verify findings” does not necessarily mean execute tests.** The public Code Review service checks candidate findings against surrounding code, filters/deduplicates them and ranks severity. Its documentation explicitly says it does not build or run the repository. It does not approve or block a PR, and its check does not conclude failure. A no-findings result is not a correctness/security guarantee. Review guidance comes from the base/default branch, rather than the PR's proposed instructions. [Code Review: how reviews work](https://code.claude.com/docs/en/code-review#how-reviews-work), [what a review can access](https://code.claude.com/docs/en/code-review#what-a-review-can-access), [who controls a review](https://code.claude.com/docs/en/code-review#who-controls-a-review).
- **Security review is another source of findings.** The linked security documentation describes a local command and PR action with filtering for false positives. Its findings do not establish that other tests, authorization checks or an approval policy have run. [Automated security reviews](https://support.claude.com/en/articles/11932705-automated-security-reviews-in-claude-code).

The article's internal blocking policy is therefore not something merely installing the public reviewer would reproduce. Our merge requirements must be implemented separately.

## Our proposed implementation

These are project-specific recommendations, not claims that the guide prescribes this exact architecture.

1. **Freeze the candidate commit.** Give an independent verifier the base SHA, candidate SHA, approved ticket/spec and trusted review rules. Do not use the author's explanation as the acceptance oracle. Any repair creates a new SHA requiring appropriate rechecks.
2. **Require a verification record.** Record those SHAs, environment/lockfile identities, commands, exit codes, test totals, skipped/blocked checks, artifact paths, new adversarial cases and unresolved findings. Mark results `passed`, `failed` or `not_run`; an unavailable database/browser is not a pass. Redact credentials. A result belongs to the tested commit, not merely a branch name.
3. **Separate detection from confirmation.** A reviewer proposes a concrete defect with file/line and expected/actual behavior. A verifier reproduces it with the smallest relevant executable case when feasible. Report static-only concerns as such; do not turn several agreeing model opinions into experimental evidence. Fix a confirmed defect with a regression test and prove the test catches the defective version.
4. **Protect the oracle.** The implementing agent must not weaken approved expectations, disable tests or rewrite review policy to obtain green results. Review changes to tests and gates independently. Keep requirements and verification policy anchored to a trusted baseline.
5. **Scale human scrutiny.** For this small project, retain a human decision before merge. Require focused human inspection of authorization/session code, quantities/money, immutable evidence, migrations, CI and future agent action permissions. A model's review is evidence, not a human approval.
6. **Evaluate the verifier.** Maintain a small set of known-bug and known-clean changes. Start with the selected-PR stale-invoice regression and an unauthorized procurement action. Check missed defects, false positives and reproduction success whenever reviewer prompts/tools/models change. Cap repair/review at three rounds before reconsidering the approach; recheck changed code and affected paths rather than repeatedly expanding unrelated cleanup.

Fresh context reduces exposure to the author's narrative; it does not guarantee statistically independent errors. Different models can help diversify scrutiny, but executable counterexamples remain necessary.

## Small first slice

Our prepared CI already covers frontend types/builds, documentation and 75 PostgreSQL-backed backend tests. It has no hosted run yet and does not run the local browser scripts. The stale-invoice display defect demonstrates why an API-green result alone cannot establish correct cross-selection UI behavior.

Start with a manual independent verification pass on one small committed change, plus a standard evidence record. Then make `tools/check-selected-pr.cjs` portable with deterministic fixtures and add that browser regression to hosted CI after a GitHub remote is connected. Add short trusted review guidance and a PR template covering testing, risk and reversal. Avoid an automated multi-agent voting/auto-merge system until these basics have measured reliability.

Future RAG verification needs its own labelled retrieval, grounded-answer, citation and unauthorized-action cases. Passing code tests or obtaining a favorable review cannot substitute for those release evaluations.
