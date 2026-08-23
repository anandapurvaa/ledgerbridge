# src/config.py
from __future__ import annotations

import os


PROJECT_ID = os.getenv(
    "LEDGERBRIDGE_PROJECT_ID",
    "cloudprojects-506123",
)

DATASET_ID = os.getenv(
    "LEDGERBRIDGE_DATASET_ID",
    "ledgerbridge",
)

ENVIRONMENT = os.getenv(
    "LEDGERBRIDGE_ENVIRONMENT",
    "synthetic",
)

LEDGER_TABLE_ID = os.getenv(
    "LEDGERBRIDGE_LEDGER_TABLE",
    f"{PROJECT_ID}.{DATASET_ID}.synthetic_evaluation_ledger",
)

RECONCILIATION_AUDIT_TABLE_ID = os.getenv(
    "LEDGERBRIDGE_RECONCILIATION_AUDIT_TABLE",
    f"{PROJECT_ID}.{DATASET_ID}."
    "synthetic_reconciliation_audit",
)

DRAFT_APPROVAL_TABLE_ID = os.getenv(
    "LEDGERBRIDGE_DRAFT_APPROVAL_TABLE",
    f"{PROJECT_ID}.{DATASET_ID}."
    "synthetic_draft_approvals",
)

DEFAULT_REVIEWER_ID = os.getenv(
    "LEDGERBRIDGE_REVIEWER_ID",
    "demo_operator",
)