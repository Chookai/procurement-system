# Procurement system discovery

## Confirmed direction

- Scenario inspiration: PT Asian Bulk Logistics (ABL), identified through https://abl.co.id/. The user clarified on 22 October 2026 that this is a fully mocked demonstration, not a system being delivered to ABL. No real ABL users, internal processes, suppliers, transactions, or integrations are assumed.
- First release covers PR, PO, GR, and supplier invoice flow.
- AI is central to the intended product and tracks the procurement flow within the agreed human-authorization boundary.
- Future scope includes RFQ, RFP, single-stage bidding, multi-stage bidding, reconciliation after invoicing, and payments.
- The first release must make the initial procurement flow work before those later capabilities are added.
- Both physical goods and services are in scope. Goods receipt records delivered items; service acceptance records confirmation of completed work.
- The first priority is visibility into every purchase's status, documents, responsible person, and next action, demonstrated in one fictional marine operations team.
- Version one captures supplier invoices and links them to purchase orders and receipts, with human review before an invoice is marked reviewed. Formal reconciliation remains a later phase.
- AI prepares drafts, extracts document data, tracks progress, flags issues, and sends reminders. People approve spending, issue purchase orders, and confirm receipt or service acceptance.
- Roles distinguish requester, approver, procurement buyer, receiver/service acceptor, and invoice reviewer. One person may hold multiple roles, but requesters cannot approve their own requests. Approval routing is configurable by value and department; demonstration thresholds remain to be selected.
- Requesters describe needs and may suggest suppliers. Procurement confirms supplier and price before issuing a purchase order. External quotations can be attached without implementing RFQ or bidding.
- Purchase orders support multiple partial goods receipts, milestone-based service acceptances, and multiple linked invoices.
- Forms, document screens, and task lists work alongside an AI assistant on the same records. Changes identify their author and time.
- Invoice-review outcomes are reviewed, needs clarification, and rejected, with reasons. Reviewed does not authorize payment. A single invoice does not automatically close purchases with outstanding deliveries or unresolved invoices.

## Selected demonstration setup

The user delegated selection of the most suitable scenario and confirmed that everything is mocked.

- Fictional organization: Demo Marine Logistics, inspired by ABL's publicly described maritime operations; this name does not identify an ABL entity.
- One marine operations team, with vessel spare-parts purchases and vessel-maintenance service purchases.
- Synthetic people, vessels, suppliers, quotations, receipts, invoices, and activity history.
- MYR as the demonstration currency, explicitly requested on 22 October 2026. Amounts and approval limits are illustrative and do not represent ABL policy. The earlier IDR 50 million threshold is not a currency conversion or an agreed MYR threshold.
- The first flow mockup uses simulated extraction and agent responses, and no live external integration. The broader project aims to implement a production-ready RAG-backed agent using synthetic procurement data, with local Azure architecture practice through Floci and measured scaling. Mock responses are a first-stage artifact, not the final RAG implementation.
- Human approval, PO issuance, receipt confirmation, and invoice review are demonstrated through fictional user roles.

## Discovery status

Interview in progress using grill-with-docs, grilling, and domain-modeling. The user authorized starting a flow mockup. Production architecture and RAG implementation choices remain proposals until settled.

## Additional accepted behavior

- PR drafts can start through a form, document upload, or assistant conversation. Drafts are editable; a human submits them. Capture goods/services, quantity, estimated cost, purpose, vessel/location, and required date.
- A scope change or value increase requires reapproval before PO issuance. Changes to issued POs create a version with a reason and preserved history.
- Accepted goods are distinct from damaged or rejected goods; only accepted quantities count toward fulfillment. Unexpected deliveries go to procurement for review.
- Budget visibility is included; hard budget enforcement is deferred.
- The answer labelled Q18 is interpreted as acceptance of Q17: interactive workspace, role switching, persistent demo changes, reset, seeded success/exception cases, and proactive simulated AI notices with inspectable evidence. These are planned workspace capabilities, not claims about the initial flow diagram.
- Start with one small team and one named PIC per step. Fictional PICs selected for the mockup: Aina (request), Ben (approval), Chloe (PO), Dinesh (receipt/service acceptance), Eva (invoice review).
- RAG evaluation is a project requirement from the beginning, including retrieval, generated answers, and agent action boundaries.
- Q19 accepted: Python/FastAPI backend and React/TypeScript frontend.
- Q20 accepted: hosted model access with OpenRouter credentials supplied by the user and Microsoft Agent Framework. The initial Foundry request was superseded on 22 October 2026: exclude Foundry from the first phase.
- The architecture proposal must include frontend, backend, database, queue, and cache. The proposal now includes these components and separates the initial footprint from later scaling additions.
- The user requested a clickable initial UI prototype using the Atlassian Design System and a design document. The throwaway prototype is in `mockups/procurement-ui-prototype`; `DESIGN.md` records the design direction.
- Three layouts are available for comparison: purchase register with assistant, workflow board, and task inbox. No winning layout has been selected. Official Atlassian tokens, CSS reset and buttons are used; other components are prototype implementations.
- The current throwaway UI uses in-memory synthetic records and simulated assistant responses. Refresh/reset discards changes; durable persistence remains planned for the subsequent application implementation.

## Open root decisions

- MYR approval threshold and whether the small-team version needs a separate additional approver.
- Exact generation/embedding models, provider capability tests and OpenRouter credential configuration; mockup remains fully simulated.
- Exact Floci and Agent Framework versions, compatible local service subset, retrieval backend, and Azure deployment architecture. Application languages/frameworks are accepted.
- Cancellation, return-to-requester, and invoice resubmission details.
- Demonstration success measures and final architecture confirmation.

Glossary entries will be recorded as terminology is agreed. Architecture decision records will be added when a durable decision with a meaningful trade-off is settled.

## Company context

Source: [ABL official website](https://abl.co.id/), reviewed 22 October 2026. The website identifies PT Asian Bulk Logistics and lists transshipment, barging, ocean-going vessels, rail freight, stevedoring, and port management among its services. This describes company context, not an agreed procurement rollout scope.

Potential discovery examples include vessel spare parts, consumables, and maintenance services. These are interview scenarios, not confirmed purchasing categories. On 22 October 2026, the user accepted goods and services, visibility as the first priority, the invoice boundary, and the AI authority boundary described above.

## First-milestone architecture confirmation

On 22 October 2026 the user accepted the recommended small baseline, with Foundry excluded initially: React/TypeScript, FastAPI, one in-process Microsoft Agent Framework agent, PostgreSQL with full-text/pgvector, Floci Blob storage, and database-backed ingestion jobs with one worker. Redis and external queue transport remain later additions. Exact models, adapter/version compatibility, local identity and milestone evaluation targets still need resolution. The user also requires inspecting the implementation code at the end of the phase before milestone closure.

On 23 October 2026 the user confirmed the initial local identity approach: five seeded users, server-verified signed tokens, backend role checks, and no registration in this phase. This resolves the local identity choice above; compatibility verification, model choices and milestone evaluation targets remain open.
