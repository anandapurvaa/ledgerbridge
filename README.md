# LedgerBridge

LedgerBridge is an invoice reconciliation console for a controlled synthetic accounts-payable workflow. It accepts an invoice image, extracts structured invoice fields, queries a BigQuery-backed ledger, applies reconciliation rules, detects duplicate submissions, produces an investigation and draft response for exceptions, records immutable audit events, and supports controlled review approval.

> **Current scope:** This is a synthetic/demo workflow. It does **not** send email or initiate payment actions.

## Highlights

- Upload invoice images through a Gradio operator console.
- Hybrid extraction combining OCR heuristics with LayoutLMv3 LoRA evidence.
- Ledger lookup through a BigQuery MCP client.
- Exact invoice-ID prioritization and semantic candidate retrieval.
- Rule-based reconciliation for identity, amount, quantity, currency, and FX-rate checks.
- Duplicate invoice detection using prior successful audit events.
- Investigation and dispute-draft generation for exceptions.
- BigQuery reconciliation audit trail and persistent draft-approval records.
- One-open-review protection per invoice in each environment.
- Review-history page with root-cause and severity filters.
- Automated unit tests for routing, graph structure, matching, investigation, drafting, audit writing, and approval rules.

## Workflow

```text
Invoice image
  -> Hybrid extraction
  -> BigQuery ledger query
  -> Matcher and reconciliation rules
  -> Duplicate detection
  -> [matched] Write audit event
  -> [exception] Investigation -> Resolution draft -> Write audit event
  -> Optional local draft approval -> BigQuery approval event
```

The LangGraph routes clean matches directly to audit. Amount mismatches, quantity mismatches, FX mismatches, ambiguous results, unmatched cases, and duplicate charges pass through investigation and resolution drafting.

## Main components

| Area | Location | Purpose |
|---|---|---|
| UI | `src/ui/app.py` | Gradio console with reconciliation and review-history tabs |
| Graph | `src/agents/graph_builder.py` | LangGraph workflow definition |
| Routing | `src/agents/graph_routes.py` | Conditional routing after extraction and duplicate detection |
| Extraction | `src/extraction/` | OCR, validation, LayoutLMv3 inference, hybrid extraction, ledger-aware repair |
| Matching | `src/matching/` | Embedding retrieval, schemas, and reconciliation rules |
| Audit | `src/audit/` | BigQuery reconciliation and approval repositories |
| Services | `src/services/` | Draft approval business rules |
| Synthetic data | `src/synthetic/` | Synthetic ledger and invoice-image generation |
| Evaluation | `src/evaluation/` | Extraction, matching, and end-to-end evaluation scripts |
| Tests | `tests/` | Unit and integration-oriented tests |

## Reconciliation outcomes

| Status | Meaning | Downstream path |
|---|---|---|
| `matched` | Invoice and ledger record agree within configured tolerances | Audit event only |
| `amount_mismatch` | Invoice and ledger amounts differ | Investigation and draft |
| `quantity_mismatch` | Quantity differs | Investigation and draft |
| `fx_mismatch` | FX rate differs | Investigation and draft |
| `ambiguous` | No stable identity or close competing candidates | Investigation and draft |
| `unmatched` | No suitable ledger match | Investigation and draft |
| `duplicate_charge` | A prior successful reconciliation exists for the same invoice identity | Investigation and draft |

## Prerequisites

- Python 3.12 recommended.
- A Google Cloud project with BigQuery enabled.
- Application Default Credentials locally, for example:

```powershell
gcloud auth application-default login
```

- Access to the configured BigQuery dataset and tables.

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Configuration

LedgerBridge reads configuration from environment variables. The repository includes defaults oriented toward the synthetic environment.

Create a local `.env` file in the project root if needed:

```text
LEDGERBRIDGE_ENVIRONMENT=synthetic
LEDGERBRIDGE_PROJECT_ID=cloudprojects-506123
LEDGERBRIDGE_DATASET_ID=ledgerbridge
LEDGERBRIDGE_LEDGER_TABLE=cloudprojects-506123.ledgerbridge.synthetic_evaluation_ledger
LEDGERBRIDGE_RECONCILIATION_AUDIT_TABLE=cloudprojects-506123.ledgerbridge.synthetic_reconciliation_audit
LEDGERBRIDGE_DRAFT_APPROVAL_TABLE=cloudprojects-506123.ledgerbridge.synthetic_draft_approvals
LEDGERBRIDGE_REVIEWER_ID=demo_operator
```

Do not commit `.env`, service-account keys, or other credentials.

## BigQuery tables

| Table | Purpose |
|---|---|
| `synthetic_evaluation_ledger` | Source ledger records used for matching |
| `synthetic_reconciliation_audit` | Immutable graph-run audit events |
| `synthetic_draft_approvals` | Local approval events for exception drafts |

### Audit behavior

Every graph execution writes a reconciliation event. An approval click writes a separate approval event containing the final editable draft, invoice ID, reviewer ID, reconciliation audit ID, approval timestamp, environment, and action `draft_approved_no_email_sent`.

An approval is treated as an **open review**. A second approval for the same invoice ID in the same environment is blocked until a future close/cancel/send workflow is added.

## Run the console

```powershell
python -m src.ui.app
```

Open the local URL printed by Gradio, upload an image from:

```text
data/synthetic/invoice_images/
```

Useful examples:

```text
data/synthetic/invoice_images/matched_00012.png
data/synthetic/invoice_images/amount_mismatch_00023.png
data/synthetic/invoice_images/duplicate_charge_00086.png
```

For duplicate behavior, process a valid matched invoice once so it creates a successful audit event, then process the same image again. The second run should become `duplicate_charge`.

## Demo workflow

A command-line full-workflow demo is also available:

```powershell
python -m src.agents.demo_full_workflow
```

The demo sends an image through extraction, BigQuery lookup, matching, duplicate detection, investigation/drafting when applicable, and audit writing.

## Review history

The **Review history** tab reads events from the reconciliation audit table. It can filter records by:

- Root cause, including `amount_mismatch`, `ambiguous_match`, `duplicate_charge`, and `unmatched`.
- Severity: `low`, `medium`, or `high`.

It is an audit-history view; it does not modify ledger records or send vendor communication.

## Testing

Run the currently active agent and service tests:

```powershell
python -m pytest tests/agents tests/services -v
```

The active suite covers graph routing, compilation, audit writer behavior, duplicate detection, extractor error handling, matcher identity prioritization, investigation, resolution drafting, and approval rules.

Legacy structured-input graph tests are intentionally archived as files that do not start with `test_`. The production graph now starts from `invoice_image_path`, not directly supplied structured fields.

Optional coverage report:

```powershell
python -m pytest tests/agents tests/services -v --cov=src --cov-report=term-missing --cov-report=html
```

## Synthetic data and model artifacts

- Synthetic invoice images: `data/synthetic/invoice_images/`
- Synthetic manifests: `data/synthetic/manifest/`
- Held-out evaluation cases: `data/evaluation/heldout_reconciliation_cases.json`
- Raw SROIE and FUNSD data: `data/raw/`
- LoRA model artifacts: `models/layoutlmv3_lora*`

The project keeps model and synthetic-data generation separate from runtime reconciliation code.

## Important limitations

- The system is designed and validated around synthetic invoice templates and a synthetic ledger.
- LayoutLMv3 model labels are not a complete invoice schema; OCR heuristics provide critical fields such as invoice ID, currency, quantity, and FX rate.
- The UI does not send email. Draft approval only persists an audit record.
- BigQuery duplicate/open-review checks are appropriate for this local demo but are not transactional locks for multi-user production concurrency.
- Production deployment should use a dedicated service account, private Cloud Run access, least-privilege BigQuery IAM, Secret Manager for secrets, and a transactional lock/state store if concurrent reviewers are expected.

## Suggested next steps

1. Add the project deployment files: `Dockerfile`, `.dockerignore`, and hardened `.gitignore`.
2. Make the Gradio launch configuration Cloud Run-compatible.
3. Deploy privately to Cloud Run with a dedicated service identity.
4. Add image-based end-to-end tests with audit writes mocked or directed to a dedicated test table.
5. Add close/cancel/send-review state transitions before enabling any outbound communication.

## License

This repository currently has no declared license. Add one before public distribution.
