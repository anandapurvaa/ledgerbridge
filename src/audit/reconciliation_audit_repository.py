# src/audit/reconciliation_audit_repository.py
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from google.cloud import bigquery

from src.matching.schemas import InvoiceRecord


class ReconciliationAuditRepository:
    def __init__(
        self,
        project_id: str | None = None,
        dataset_id: str = "ledgerbridge",
        table_id: str = "reconciliation_audit",
    ) -> None:
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id or self.client.project
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.full_table_id = (
            f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        )

    def find_prior_successful_invoice(
        self,
        invoice: InvoiceRecord,
    ) -> dict[str, Any] | None:
        """
        Find a previous accepted/reconciled instance of this invoice.

        `matched` is included now. You can later add statuses such as
        `approved_for_payment` or `dispute_sent` as the workflow grows.
        """
        query = f"""
            SELECT
                audit_event_id,
                event_timestamp,
                invoice_id,
                vendor,
                invoice_date,
                amount,
                currency,
                quantity,
                fx_rate,
                reconciliation_status,
                matched_ledger_invoice_id,
                run_id,
                source,
                details_json
            FROM `{self.full_table_id}`
            WHERE invoice_id = @invoice_id
              AND vendor = @vendor
              AND invoice_date = @invoice_date
              AND amount = @amount
              AND currency = @currency
              AND reconciliation_status = "matched"
            ORDER BY event_timestamp DESC
            LIMIT 1
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "invoice_id",
                    "STRING",
                    invoice.invoice_id,
                ),
                bigquery.ScalarQueryParameter(
                    "vendor",
                    "STRING",
                    invoice.vendor,
                ),
                bigquery.ScalarQueryParameter(
                    "invoice_date",
                    "DATE",
                    invoice.invoice_date,
                ),
                bigquery.ScalarQueryParameter(
                    "amount",
                    "FLOAT64",
                    invoice.amount,
                ),
                bigquery.ScalarQueryParameter(
                    "currency",
                    "STRING",
                    invoice.currency,
                ),
            ]
        )

        rows = list(
            self.client.query(
                query,
                job_config=job_config,
            ).result()
        )

        if not rows:
            return None

        return dict(rows[0].items())

    def write_event(
        self,
        invoice: InvoiceRecord,
        reconciliation_status: str,
        run_id: str,
        source: str,
        matched_ledger_invoice_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        audit_event_id = str(uuid.uuid4())

        row = {
            "audit_event_id": audit_event_id,
            "event_timestamp": datetime.now(timezone.utc).isoformat(),
            "invoice_id": invoice.invoice_id,
            "vendor": invoice.vendor,
            "invoice_date": invoice.invoice_date,
            "amount": invoice.amount,
            "currency": invoice.currency,
            "quantity": invoice.quantity,
            "fx_rate": invoice.fx_rate,
            "reconciliation_status": reconciliation_status,
            "matched_ledger_invoice_id": matched_ledger_invoice_id,
            "run_id": run_id,
            "source": source,
            "details_json": json.dumps(details or {}),
        }

        errors = self.client.insert_rows_json(
            self.full_table_id,
            [row],
        )

        if errors:
            raise RuntimeError(
                f"Failed to insert audit event: {errors}"
            )

        return audit_event_id