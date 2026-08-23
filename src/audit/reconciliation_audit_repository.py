# src/audit/reconciliation_audit_repository.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.cloud import bigquery

from src.config import RECONCILIATION_AUDIT_TABLE_ID
from src.matching.schemas import InvoiceRecord


class ReconciliationAuditRepository:
    """
    Stores immutable reconciliation events in the configured BigQuery table.

    It accepts both the existing audit-writer arguments and a structured
    reconciliation-result form. It also exposes history queries for the UI.
    """

    def __init__(
        self,
        table_id: str = RECONCILIATION_AUDIT_TABLE_ID,
    ) -> None:
        self.table_id = table_id
        self.client = bigquery.Client()

    def ensure_table_exists(self) -> None:
        schema = [
            bigquery.SchemaField(
                "audit_event_id",
                "STRING",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "event_timestamp",
                "TIMESTAMP",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "run_id",
                "STRING",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "invoice_id",
                "STRING",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "invoice_date",
                "DATE",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "vendor",
                "STRING",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "amount",
                "FLOAT",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "currency",
                "STRING",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "quantity",
                "INTEGER",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "fx_rate",
                "FLOAT",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "reconciliation_status",
                "STRING",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "confidence",
                "FLOAT",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "best_match_invoice_id",
                "STRING",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "discrepancy_details_json",
                "STRING",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "investigation_json",
                "STRING",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "dispute_letter_draft",
                "STRING",
                mode="NULLABLE",
            ),
        ]

        table = bigquery.Table(
            self.table_id,
            schema=schema,
        )

        self.client.create_table(
            table,
            exists_ok=True,
        )

    def write_event(
        self,
        invoice: InvoiceRecord,
        run_id: str | None = None,
        reconciliation_status: str | None = None,
        confidence: float | None = None,
        best_match: dict[str, Any] | None = None,
        discrepancy_details: dict[str, Any] | None = None,
        investigation: dict[str, Any] | None = None,
        dispute_letter_draft: str = "",
        reconciliation_result: dict[str, Any] | None = None,
        **_: Any,
    ) -> str:
        """
        Insert one reconciliation audit row and return its event ID.

        `**_` absorbs non-persisted legacy fields passed by older writer
        node versions during repository migration.
        """
        self.ensure_table_exists()

        if reconciliation_result is not None:
            reconciliation_status = reconciliation_result.get(
                "status",
                reconciliation_status or "unmatched",
            )

            confidence = reconciliation_result.get(
                "confidence",
                confidence if confidence is not None else 0.0,
            )

            best_match = reconciliation_result.get(
                "best_match",
                best_match or {},
            )

            discrepancy_details = reconciliation_result.get(
                "discrepancy_details",
                discrepancy_details or {},
            )

        audit_event_id = str(uuid4())

        best_match = best_match or {}
        discrepancy_details = discrepancy_details or {}
        investigation = investigation or {}

        event = {
            "audit_event_id": audit_event_id,
            "event_timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "run_id": run_id or str(uuid4()),
            "invoice_id": invoice.invoice_id,
            "invoice_date": (
                str(invoice.invoice_date)
                if invoice.invoice_date
                else None
            ),
            "vendor": invoice.vendor,
            "amount": float(invoice.amount),
            "currency": invoice.currency,
            "quantity": int(invoice.quantity),
            "fx_rate": float(invoice.fx_rate),
            "reconciliation_status": (
                reconciliation_status or "unmatched"
            ),
            "confidence": float(confidence or 0.0),
            "best_match_invoice_id": best_match.get(
                "invoice_id"
            ),
            "discrepancy_details_json": json.dumps(
                discrepancy_details,
                default=str,
                sort_keys=True,
            ),
            "investigation_json": json.dumps(
                investigation,
                default=str,
                sort_keys=True,
            ),
            "dispute_letter_draft": (
                dispute_letter_draft or None
            ),
        }

        errors = self.client.insert_rows_json(
            self.table_id,
            [event],
            row_ids=[audit_event_id],
        )

        if errors:
            raise RuntimeError(
                "Unable to write reconciliation audit event: "
                f"{errors}"
            )

        return audit_event_id

    def find_prior_successful_invoice(
        self,
        invoice: InvoiceRecord,
    ) -> dict[str, Any] | None:
        """
        Find the latest successful match for the same invoice identity.
        """
        query = f"""
            SELECT
                audit_event_id,
                event_timestamp,
                run_id
            FROM `{self.table_id}`
            WHERE invoice_id = @invoice_id
              AND vendor = @vendor
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
                    "amount",
                    "FLOAT64",
                    float(invoice.amount),
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

        return dict(rows[0])

    def list_history(
        self,
        root_cause: str | None = None,
        severity: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """
        Return recent reconciliation events for the review-history page.

        `root_cause` and `severity` are extracted from the stored
        investigation JSON. Passing None disables that individual filter.
        """
        self.ensure_table_exists()

        query = f"""
            SELECT
                audit_event_id,
                event_timestamp,
                invoice_id,
                invoice_date,
                vendor,
                amount,
                currency,
                quantity,
                fx_rate,
                reconciliation_status,
                confidence,
                best_match_invoice_id,
                discrepancy_details_json,
                investigation_json,
                dispute_letter_draft
            FROM `{self.table_id}`
            WHERE (
                @root_cause = ""
                OR JSON_VALUE(
                    investigation_json,
                    "$.root_cause"
                ) = @root_cause
            )
            AND (
                @severity = ""
                OR JSON_VALUE(
                    investigation_json,
                    "$.severity"
                ) = @severity
            )
            ORDER BY event_timestamp DESC
            LIMIT @limit
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "root_cause",
                    "STRING",
                    root_cause or "",
                ),
                bigquery.ScalarQueryParameter(
                    "severity",
                    "STRING",
                    severity or "",
                ),
                bigquery.ScalarQueryParameter(
                    "limit",
                    "INT64",
                    min(max(int(limit), 1), 500),
                ),
            ]
        )

        rows = self.client.query(
            query,
            job_config=job_config,
        ).result()

        return [dict(row) for row in rows]