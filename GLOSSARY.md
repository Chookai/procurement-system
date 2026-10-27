# Procurement

Language for a mocked procurement demonstration inspired by Asian Bulk Logistics.

## Language

**ABL**:
Asian Bulk Logistics, the logistics company whose public business scenario inspires the demonstration. ABL is not an assumed customer or participant in the demo.
_Avoid_: ADL, ABL Freight Logistics, ABL Consolidators

**Goods receipt (GR)**:
A record confirming physical goods received against a purchase order.
_Avoid_: Service acceptance

**Service acceptance**:
A record confirming work performed under a purchase order has been accepted by the responsible person.
_Avoid_: Goods receipt

**Supplier invoice**:
A supplier's request for payment for supplied goods or services. Reviewing an invoice does not mean it has been paid or formally reconciled.
_Avoid_: Customer invoice, payment

**Purchase requisition (PR)**:
An internal request to authorize the purchase of goods or services.
_Avoid_: Purchase order

**Purchase order (PO)**:
An order issued to a selected supplier describing the goods or services being purchased and their agreed commercial terms.
_Avoid_: Purchase requisition

**Requester**:
The person who raises a purchase requisition for a business need.

**Approver**:
The person authorized to approve a purchase requisition under the applicable spending rules.

**Procurement buyer**:
The person responsible for confirming the supplier and price and issuing the purchase order.

**Invoice reviewer**:
The person who reviews a supplier invoice and records its review outcome.

**PO revision**:
An issued version of a purchase order that replaces its previous commercial terms while preserving earlier versions.

**PO change proposal**:
Proposed replacement terms that await approval or issuance and do not yet replace the current issued purchase order.

**Outstanding quantity**:
The ordered quantity still awaiting acceptance; damaged or rejected quantities do not fulfil the order.
