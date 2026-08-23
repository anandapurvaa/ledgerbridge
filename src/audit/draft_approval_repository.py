# src/audit/draft_approval_repository.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.cloud import bigquery

from src.config import DRAFT_APPROVAL_TABLE_ID


OPEN_REVIEW_ACTION = "draft_approved_no_email_sent"


class DraftApprovalRepository:
    """
    Stores local operator approvals for dispute drafts.

    This repository never sends email. It records approval events in
    BigQuery and checks whether an invoice already has an open review.
    """

    def __init__(
        self,
        table_id: str = DRAFT_APPROVAL_TABLE_ID,
    ) -> None:
        self.table_id = table_id
        self.client = bigquery.Client()

    def ensure_table_exists(self) -> None:
        schema = [
            bigquery.SchemaField(
                "approval_event_id",
                "STRING",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "approved_at",
                "TIMESTAMP",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "reviewer_id",
                "STRING",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "action",
                "STRING",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "reconciliation_audit_event_id",
                "STRING",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "invoice_id",
                "STRING",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "reconciliation_status",
                "STRING",
                mode="NULLABLE",
            ),
            bigquery.SchemaField(
                "final_draft",
                "STRING",
                mode="REQUIRED",
            ),
            bigquery.SchemaField(
                "environment",
                "STRING",
                mode="REQUIRED",
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

    def find_open_review(
        self,
        invoice_id: str,
        environment: str,
    ) -> dict[str, Any] | None:
        """
        Return the latest active draft-approval event for one invoice.

        Every `draft_approved_no_email_sent` record remains open until a
        future close/cancel/send workflow is implemented.
        """
        self.ensure_table_exists()

        query = f"""
            SELECT
                approval_event_id,
                approved_at,
                reviewer_id,
                reconciliation_audit_event_id,
                reconciliation_status
            FROM `{self.table_id}`
            WHERE invoice_id = @invoice_id
              AND environment = @environment
              AND action = @open_review_action
            ORDER BY approved_at DESC
            LIMIT 1
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "invoice_id",
                    "STRING",
                    invoice_id,
                ),
                bigquery.ScalarQueryParameter(
                    "environment",
                    "STRING",
                    environment,
                ),
                bigquery.ScalarQueryParameter(
                    "open_review_action",
                    "STRING",
                    OPEN_REVIEW_ACTION,
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

    def record_approval(
        self,
        reconciliation_audit_event_id: str,
        invoice_id: str,
        reconciliation_status: str,
        final_draft: str,
        reviewer_id: str,
        environment: str,
    ) -> str:
        """
        Save an approval event that opens review for the invoice.
        """
        self.ensure_table_exists()

        approval_event_id = str(uuid4())

        row = {
            "approval_event_id": approval_event_id,
            "approved_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "reviewer_id": reviewer_id,
            "action": OPEN_REVIEW_ACTION,
            "reconciliation_audit_event_id": (
                reconciliation_audit_event_id
            ),
            "invoice_id": invoice_id,
            "reconciliation_status": reconciliation_status,
            "final_draft": final_draft,
            "environment": environment,
        }

        errors = self.client.insert_rows_json(
            self.table_id,
            [row],
            row_ids=[approval_event_id],
        )

        if errors:
            raise RuntimeError(
                "Unable to write draft approval record: "
                f"{errors}"
            )

        return approval_event_id