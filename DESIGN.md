# Harbor procurement design

Status: initial design direction and throwaway UI exploration. The first real application uses the recommended register/detail layout as a delivery-team choice after implementation was authorized. The three prototype alternatives remain available for comparison. Harbor is a working product name for the fictional Demo Marine Logistics workspace, not an ABL product or an Atlassian product.

## Design question

Which workspace makes it easiest for one small team to understand a purchase, identify the next responsible person, take the next action, and inspect the assistant's evidence?

The first flow is PR → approval → PO → goods receipt or service acceptance → supplier-invoice review. Use MYR throughout. RFQ/RFP, bidding, reconciliation and payment remain outside this first experience.

## Atlassian foundation

Use the [Atlassian Design System](https://atlassian.design/design-system) as the visual and interaction foundation. The prototype uses the official `@atlaskit/tokens`, `@atlaskit/css-reset`, and `@atlaskit/button` packages. The lockfile records the installed versions. Theme initialization uses the installed package's `set-global-theme` entry point.

Navigation, tables, tabs, status labels, modal shells, avatars and form controls are lightweight prototype implementations. They are not represented as complete Atlaskit components. Replace them with supported ADS components or validate their accessibility and interaction contracts when implementing the selected design. Custom icons use a small inline SVG set; they are not Atlassian brand assets.

Source guidance: [Foundations](https://atlassian.design/foundations), [components](https://atlassian.design/components), [spacing](https://atlassian.design/foundations/spacing), [typography](https://atlassian.design/foundations/typography), and [Rovo UI](https://atlassian.design/rovo-ui), reviewed 22 October 2026. Borrow the evidence and assistance principles without presenting this procurement assistant as Rovo.

## Character and layout

The workspace should feel calm, practical and familiar: a white work surface, a quiet navigation rail, compact information, clear blue actions, and restrained status color. Use borders and spacing for hierarchy. Reserve shadows for overlays, flags and the clearly separate prototype toolbar. Avoid decorative charts, hero imagery, oversized metrics and ungrounded AI confidence scores.

The shared shell includes global search, a team sidebar, the page heading and primary action, and a fictional role selector. A purchase detail surface connects commercial terms, fulfilment, invoices, source documents and activity. The working desktop shell uses a 60px header, approximately 224px navigation rail, 24–32px content gutters, and an approximately 294–330px assistant panel when space permits. These dimensions are product choices, not claims about mandated ADS sizes.

## Tokens, typography and spacing

Light and dark modes use the official Atlassian color themes. A labelled header toggle changes theme across all three layouts, record details, dialogs, source previews and the assistant without resetting workflow state. The URL `theme=light` or `theme=dark` makes the choice shareable and reload-stable; it is independent of `variant`. The default remains light. Native form controls follow CSS `color-scheme`. Accent avatar pairs, workspace identity and status colors use semantic tokens rather than light-only backgrounds. The distinct prototype toolbar retains a high-contrast treatment with a visible outline in dark mode.

Use semantic tokens rather than tying product meaning to a raw palette. CSS fallback values provide first-paint continuity; the official loaded theme supplies actual token values.

| Purpose | Token / CSS variable |
|---|---|
| Primary reading text | `color.text` / `--ds-text` |
| Supporting text | `color.text.subtle` / `--ds-text-subtle` |
| Surface and subdued region | `elevation.surface`, `elevation.surface.sunken` |
| Borders and focused controls | `color.border`, `color.border.focused` |
| Primary action | `color.background.brand.bold` |
| Selection | `color.background.selected`, `color.text.selected` |
| Status | Information, warning, success and danger semantic backgrounds/text |
| Assistant identity | Discovery tokens, confined to the assistant's small mark |

ADS spacing is based on 8px, with intermediate values such as 4px and 12px. Use 8px for tight icon/text groups, 16px for controls and compact regions, 24px between related sections and 32px for larger layout divisions. The prototype has local spacing aliases and some literal dimensions; production should map repeated spacing to ADS tokens/primitives.

Use a system sans-serif fallback in this prototype. ADS documents Atlassian Sans and Atlassian Mono as product typefaces; no Atlassian font asset is bundled or claimed here. Page titles are approximately 24–26px, section headings 15px, primary content 12–14px in this compact exploration, and secondary metadata 10–12px. Prototype-control labels can be smaller; production reading sizes must be reviewed against actual users and viewport sizes. Tabular numbers help compare MYR amounts.

## Three alternatives

| Variant | Information hierarchy | Main affordance | What to learn |
|---|---|---|---|
| A: purchase register | Shared overview → dense register → contextual assistant | Open a purchase from its row | Can the team scan ownership and exceptions quickly? Recommended starting point, not an accepted winner. |
| B: workflow board | Request/approval → ordering → delivery/review → reviewed | Open a stage card | Does stage visibility make handoffs easier than a table? |
| C: task inbox | Current PIC's worklist → focused purchase detail | Act on the current purchase | Is a task-first view better for daily work? |

All variants use the same in-memory records. The URL `?variant=A`, `B`, or `C` selects the layout. A floating development-only bottom toolbar cycles variants, with Left/Right keyboard support outside editable controls. It exposes the active PIC and record state, with an expanded state inspector. Refreshing resets the fictional dataset. Shared state across variants supports comparison without pretending the backend is implemented.

## Business interactions

- **PR:** enter a business need, goods/service type, vessel, quantity or milestone count, unit estimate, suggested supplier and required date. Create an editable draft before submission. A sample quotation button demonstrates a prefilled draft; it does not perform OCR.
- **Approval:** Ben approves or returns a submitted request. Aina cannot approve her own request. The MYR approval threshold is not invented or enforced in this prototype.
- **PO:** Chloe confirms the supplier and issues the order. Proposed changes return for approval, preserve previous purchase details and keep the issued PO snapshot until its revision is issued.
- **Receipt:** Dinesh confirms accepted goods or service milestones. Partial acceptance leaves the remaining quantity outstanding. Rejected/damaged goods do not count as accepted.
- **Invoice:** Eva can capture multiple invoices, including before full receipt. Review outcomes are reviewed, needs clarification and rejected, with a required reason. An invoice's reviewed status does not establish payment or close outstanding deliveries.

Handoffs name a person and the next action. Role switching is explicit demo behavior; some contextual action buttons switch to the relevant PIC and show that identity in the confirmation dialog. This is not authentication or server-side authorization. The production design needs real permission checks behind every mutation.

The detail progress tracker summarizes the ordinary journey. Delivery and invoicing can overlap; the register's single status is a compact priority summary, not the final production state model. For example, invoice clarification can take precedence in the status label while receipt counts still show outstanding goods. Keep those independent facts visible in detail.

## Assistant behavior and evidence

The assistant is adjacent to work, not a replacement for the purchase screens. It explains status, suggests a handoff and presents source links. It does not approve, issue, accept or pay on behalf of the user.

Every source chip opens an explicitly synthetic preview. Assistant responses use the selected record and are visibly simulated; no model or retrieval runs in this prototype. Unknown budget/approval policy must remain unknown. Do not display a fabricated answer or confidence percentage to fill missing evidence. Production citations must identify actual source versions and passages, and numeric/status facts must come from authorized structured records.

## Responsive and keyboard behavior

On wide screens, A places the assistant beside the register. At narrower desktop widths, the assistant moves below the work area. The board moves from four to two columns. At mobile widths the sidebar becomes horizontal navigation, the inbox stacks, forms remain labelled and tables scroll within their own region. Vertical page scrolling is expected.

Use semantic buttons and labelled controls, visible focus rings, a skip link, text in addition to status color, Escape to close overlays, and focus containment within dialogs. Avoid intercepting Left/Right keys while a form control is focused. These are initial safeguards; no claim of full accessibility certification is made.

## Running, validation and next decision

The engineering ticket register is a separate standalone HTML surface at `/tickets.html`. It uses the installed Atlassian light/dark color-token assets, a compact list/detail layout, readiness lozenges, distinct execution progress, prerequisite links and source-reference previews. Search and filters operate on a generated snapshot of local Markdown issues. The browser does not silently edit source files; regeneration is explicit. The register's Agent setup tab shows the active engineering configuration, generated from the approved instruction files. A pending setup is labelled as a draft when those files are absent.

Run `npm run prototype` at the workspace root and open `/prototype/procurement?variant=A` on port 5173. The README next to the prototype provides the dependency-install command. No application backend or API credential is required.

Evaluate the three layouts, then record the selected variant and any borrowed elements here. Rewrite the selected UI with proper component boundaries, production authentication, real workflow state and APIs. The prototype is a primary design reference, not production code. No Git repository or implementation issue exists in this workspace yet, so throwaway-branch archival and an issue pointer are pending rather than silently fabricated.
