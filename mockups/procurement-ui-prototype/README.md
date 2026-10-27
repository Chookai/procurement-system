# Throwaway procurement UI prototype

Question: which workspace best supports a small team's procurement handoffs while making assistant evidence easy to inspect?

Three structurally different variants on `/prototype/procurement`, selected with `?variant=A`, `B`, or `C`: register plus assistant, workflow board, and task inbox. The bottom switcher also supports Left/Right arrow keys outside editable controls. It is development-only.

Use the header's Dark/Light toggle, or append `&theme=dark` to open any layout in dark mode. Theme and layout choices survive refresh through the URL; purchase data remains in memory and resets on refresh.

From the workspace root run `npm run prototype`, then open http://localhost:5173/prototype/procurement?variant=A. Install dependencies once with `npm --prefix mockups/procurement-ui-prototype install` if absent. `npm run prototype:build` checks bundling; this is not a production application.

All people, records and responses are synthetic. State is in memory, shared across variants, and reset on refresh or Reset demo. Use the role selector or record's handoff button to switch PIC. The switcher footer exposes the current role, selected record and workflow state. No backend, model call, OCR, authentication, or durable persistence is implemented.

Start with Main engine pump seals, submit as Aina, approve as Ben, issue as Chloe, receive as Dinesh, and review an invoice as Eva. Try accepting six of ten items to inspect partial fulfilment. The assistant and source viewer use the same in-memory record.

The root DESIGN.md records the design direction. No variant has won yet. This workspace has no Git repository or implementation issue, so archival to a throwaway branch is pending until there is a winner and a repository. Do not promote this code unchanged into production.
