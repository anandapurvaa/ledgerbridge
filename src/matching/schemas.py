# src/matching/schemas.py
from typing import Any, Literal

from pydantic import BaseModel, Field


class InvoiceRecord(BaseModel):
    invoice_id: str
    invoice_date: str
    vendor: str
    amount: float
    currency: str
    quantity: int
    fx_rate: float
    line_items: Any = None


class MatchCandidate(BaseModel):
    ledger_record: InvoiceRecord
    semantic_score: float
    rank: int


class ReconciliationResult(BaseModel):
    status: Literal[
        "matched",
        "duplicate_charge",
        "fx_mismatch",
        "quantity_mismatch",
        "amount_mismatch",
        "currency_mismatch",
        "unmatched",
        "ambiguous",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    best_match: InvoiceRecord | None = None
    candidate_matches: list[MatchCandidate] = Field(default_factory=list)
    discrepancy_details: dict[str, Any] = Field(default_factory=dict)