# Engineering skills setup — approved snapshot

Status: approved and applied on 22 October 2026. The user approved this configuration. This file preserves the reviewed snapshot; AGENTS.md and the three configuration documents are now authoritative.

## Approved AGENTS.md

```markdown
# Procurement workspace

## Agent skills

### Issue tracker

Before creating, reading or updating specs and tickets, read `docs/agents/issue-tracker.md`. Work is tracked as local Markdown under `.scratch/`.

### Triage labels

Before assigning issue readiness, read `docs/agents/triage-labels.md`. Use the five default labels; keep execution progress separate.

### Domain docs

Before exploring a domain area, read `docs/agents/domain.md`. This is a single-context project using root `GLOSSARY.md` and `docs/adr/`.
```

## Approved docs/agents/issue-tracker.md

```markdown
# Issue tracker: Local Markdown

Specs and tickets live under `.scratch/<feature-slug>/`.

- Spec: `spec.md` within the feature directory.
- Tickets: `issues/<NN>-<slug>.md`, one file per ticket, numbered from 01.
- `Status:` records triage readiness using the configured label vocabulary.
- `Progress:` records execution: Not started, In progress or Done.
- `Blocked by:` lists ticket filename numbers. A prerequisite is satisfied when its Progress is Done.
- Comments append under `## Comments`.

When a skill says publish, create or update the appropriate local Markdown file. Fetch a ticket by reading its referenced file. A generated HTML register is a read-only view of those files; regenerate it after Markdown changes with `python3 tools/build-ticket-register.py`. Do not treat browser presentation state or a downloaded copy as a tracker update.

The current backlog is `.scratch/procurement-mvp/issues/`. A draft ticket is not automatically implementation-ready.
```

## Approved docs/agents/triage-labels.md

```markdown
# Triage labels

| Canonical role | Local Status value | Meaning |
|---|---|---|
| needs-triage | needs-triage | Scope and priority need review. |
| needs-info | needs-info | A decision or information is missing. |
| ready-for-agent | ready-for-agent | Specified and ready for agent implementation. |
| ready-for-human | ready-for-human | Requires human implementation. |
| wontfix | wontfix | Reviewed and deliberately declined. |

Use these strings when a skill assigns a readiness label. Readiness is distinct from execution progress. Deferred work remains in the backlog; deferral alone does not mean wontfix.
```

## Approved docs/agents/domain.md

```markdown
# Domain documentation

This project uses a single context: root `GLOSSARY.md` and `docs/adr/`.

Before exploring a domain area, read the glossary and relevant ADRs. Use canonical terms in specifications, tickets, APIs and tests. Surface a conflict with an existing ADR rather than silently overriding it. If a document is absent, continue; create terms and decisions lazily through domain-modeling as they become settled.

The architecture direction document contains accepted directions alongside proposals. Preserve those statuses. A diagram or a prototype is not evidence that every architectural choice is accepted.
```

## Review

The setup has been applied. Local Markdown is the issue tracker, the five default readiness labels are configured, and the existing single-context glossary/ADR layout is retained. Architecture and milestone decisions remain at their existing proposal status.
