from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Contract):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class Line(Contract):
    description: str = Field(min_length=2, max_length=300)
    quantity: Annotated[
        Decimal, Field(gt=0, le=100_000, max_digits=9, decimal_places=2)
    ]
    unit_price: Annotated[
        Decimal, Field(gt=0, le=1_000_000, max_digits=12, decimal_places=2)
    ]


class RequisitionData(Contract):
    title: str = Field(min_length=3, max_length=150)
    kind: Literal["goods", "service"]
    purpose: str = Field(min_length=5, max_length=2000)
    vessel: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=120)
    required_date: date
    supplier_suggestion: str = Field(default="", max_length=150)
    items: list[Line] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def service_milestones(self):
        if self.kind == "service" and any(
            item.quantity != item.quantity.to_integral_value() for item in self.items
        ):
            raise ValueError("Service milestone quantities must be whole numbers")
        return self


class Edit(RequisitionData):
    expected_version: int = Field(ge=1)


class Transition(Contract):
    expected_version: int = Field(ge=1)
    reason: str = Field(default="", max_length=1000)


class IssuePurchaseOrder(Contract):
    expected_version: int = Field(ge=1)
    supplier: str = Field(min_length=2, max_length=150)
    unit_prices: list[
        Annotated[Decimal, Field(gt=0, le=1_000_000, max_digits=12, decimal_places=2)]
    ] = Field(min_length=1, max_length=20)
    delivery_terms: str = Field(default="", max_length=2000)


class ProposePurchaseOrder(RequisitionData):
    expected_version: int = Field(ge=1)
    supplier: str = Field(min_length=2, max_length=150)
    delivery_terms: str = Field(default="", max_length=2000)
    reason: str = Field(min_length=1, max_length=1000)


class ProposalDecision(Transition):
    proposal_id: UUID


Quantity = Annotated[Decimal, Field(ge=0, le=100_000, max_digits=9, decimal_places=2)]


class ReceiptLine(Contract):
    line_index: int = Field(ge=0, le=19)
    accepted: Quantity = Decimal("0")
    damaged: Quantity = Decimal("0")
    rejected: Quantity = Decimal("0")


class RecordReceipt(Contract):
    expected_version: int = Field(ge=1)
    po_revision: int = Field(ge=1)
    received_on: date
    reference: str = Field(min_length=2, max_length=150)
    notes: str = Field(default="", max_length=2000)
    lines: list[ReceiptLine] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def receipt_quantities(self):
        if len({line.line_index for line in self.lines}) != len(self.lines):
            raise ValueError("Each PO line may appear only once per receipt")
        if any(
            line.accepted + line.damaged + line.rejected == 0 for line in self.lines
        ):
            raise ValueError("Each recorded line needs a quantity greater than zero")
        if any(line.damaged or line.rejected for line in self.lines) and not self.notes:
            raise ValueError("Explain damaged or rejected quantities in notes")
        return self


class InvoiceLine(Contract):
    line_index: int = Field(ge=0, le=19)
    quantity: Annotated[
        Decimal, Field(gt=0, le=100_000, max_digits=9, decimal_places=2)
    ]
    unit_price: Annotated[
        Decimal, Field(gt=0, le=1_000_000, max_digits=12, decimal_places=2)
    ]


class CaptureInvoice(Contract):
    expected_version: int = Field(ge=1)
    po_revision: int = Field(ge=1)
    supplier: str = Field(min_length=2, max_length=150)
    invoice_number: str = Field(min_length=1, max_length=100)
    invoice_date: date
    evidence_reference: str = Field(min_length=2, max_length=300)
    lines: list[InvoiceLine] = Field(min_length=1, max_length=20)
    receipt_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def unique_invoice_references(self):
        if len({line.line_index for line in self.lines}) != len(self.lines):
            raise ValueError("Each invoice line may reference a PO line only once")
        if len(set(self.receipt_ids)) != len(self.receipt_ids):
            raise ValueError("Receipt evidence must not contain duplicate references")
        return self


class ReviewInvoice(Contract):
    expected_version: int = Field(ge=1)
    invoice_id: UUID
    outcome: Literal["reviewed", "needs_clarification", "rejected"]
    reason: str = Field(min_length=1, max_length=2000)
