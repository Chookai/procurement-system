# Prototype review notes

This is a throwaway visual prototype, not production-ready code. No automated test suite was added.

The root `npm run prototype:build` command bundles successfully. The local development server runs on port 5173, and the prototype URL is `/prototype/procurement?variant=A`.

A browser-driven click-through exercised:

- Aina submitting the seeded draft, Ben approving, and Chloe issuing its PO.
- Dinesh accepting 6 of 10 units, Eva capturing MYR 1,200 and recording a reviewed invoice with a reason. The purchase remained partially received, with 4 outstanding and Dinesh next.
- The assistant explaining that partial state and opening its synthetic source preview.
- A purchase revision returning for approval while the issued PO preview retained its original 10-unit order.
- A/B/C layout switching without reloading the in-memory purchase state.
- The task inbox opening the correct purchase when preparing a PO. An event-ordering issue discovered here was corrected and the walkthrough repeated successfully.
- Creating a new PR from the simulated quotation and resetting the demo.
- Mobile page width of 390px with a 390px document width; tables retain their own horizontal scroll where needed.

The completed walkthrough reported no browser page errors. Desktop/mobile screenshots were inspected; this is not a full accessibility audit or exhaustive verification of every edge case. Production features such as authentication, persistence, real uploads/OCR, retrieval, model responses and payment are not implemented here.

Dark theme follow-up: the final build passed. Browser inspection covered A/B/C with `theme=dark`, dark dialog and input surfaces, a visible mobile theme toggle with no page overflow at 390px, dark theme retained on reload and variant changes, and a submitted PR staying submitted when switching to light. No page errors were reported. Official dark tokens were active; workflow data remains in memory and theme choice is URL-backed.

Preview images: `preview-A.png`, `preview-B.png`, `preview-C.png`, `preview-purchase.png`, and `preview-mobile.png`. The purchase image captures the partial-delivery scenario; the three layout images use fresh starting data.
