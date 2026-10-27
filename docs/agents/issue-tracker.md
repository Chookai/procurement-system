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
