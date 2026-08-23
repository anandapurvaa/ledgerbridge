# src/evaluation/audit_simulator.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InMemoryAuditSimulator:
    """
    Test-only stand-in for the BigQuery reconciliation audit table.

    Stores invoice IDs already accepted as matched. This makes duplicate
    detection reproducible without polluting your real audit table.
    """
    processed_invoice_ids: set[str] = field(
        default_factory=set
    )

    def has_prior_match(
        self,
        invoice_id: str,
    ) -> bool:
        return invoice_id in self.processed_invoice_ids

    def record_match(
        self,
        invoice_id: str,
    ) -> None:
        self.processed_invoice_ids.add(invoice_id)

    def evaluate_duplicate_status(
        self,
        invoice_id: str,
        reconciliation_status: str,
    ) -> str:
        """
        For a currently matched invoice:
        - first submission remains matched and gets recorded
        - later submission becomes duplicate_charge

        Non-matched cases are not recorded as successful invoice events.
        """
        if reconciliation_status != "matched":
            return reconciliation_status

        if self.has_prior_match(invoice_id):
            return "duplicate_charge"

        self.record_match(invoice_id)

        return "matched"