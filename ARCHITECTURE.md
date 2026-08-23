# LedgerBridge Architecture

## Purpose

LedgerBridge is a document-to-ledger reconciliation system for a controlled synthetic accounts-payable workflow. It receives an invoice image, extracts structured values, compares those values with BigQuery ledger records, detects exceptions and duplicates, produces investigation/draft outputs when required, and writes audit events.

The application is deliberately human-in-the-loop. It can prepare and approve a draft for review, but it does not send email or initiate payment activity.

## Logical architecture

```text
                         +---------------------------+
                         |     Gradio Operator UI     |
                         |  Reconcile + Review History|
                         +-------------+-------------+
                                       |
                                       v
                         +---------------------------+
                         |      LangGraph Workflow    |
                         +-------------+-------------+
                                       |
     +-------------------+-------------+--------------------+
     |                   |                                  |
     v                   v                                  v
+------------+    +--------------+                  +--------------+
| Extraction |    | Ledger Query |                  | Audit Storage|
| OCR/Hybrid |    | BigQuery MCP |                  |   BigQuery   |
+------------+    +--------------+                  +--------------+
     |                   |                                  |
     +-------------------+----------------------------------+
                         |
                         v
                 +---------------+
                 | Matcher/Rules |
                 +-------+-------+
                         |
                         v
                +-----------------+
                | Duplicate Check |
                +---+---------+---+
                    |         |
          matched   |         | exception
                    v         v
              +---------+  +----------------+  +-------------------+
              | Audit   |  | Investigator   |  | Resolution Drafter|
              +---------+  +-------+--------+  +---------+---------+
                                 |                     |
                                 +----------+----------+
                                            |
                                            v
                                      +-----------+
                                      | Audit     |
                                      +-----------+
```

## Runtime layers

### 1. Presentation layer

**Location:** `src/ui/`

`src/ui/app.py` is a Gradio application with two tabs:

- **Reconcile invoice:** upload image, view extracted invoice fields, reconciliation outcome, candidate records, investigation findings, editable draft, and approval state.
- **Review history:** query reconciliation audit history with root-cause and severity filters.

`src/ui/graph_runner.py` prepares initial graph state and invokes the compiled LangGraph workflow.

The UI is a presentation layer only. Business decisions, BigQuery operations, and open-review checks live below it.

### 2. Orchestration layer

**Location:** `src/agents/`

`graph_builder.py` constructs the LangGraph `StateGraph`.

```text
START
  -> extractor
  -> conditional: query_ledger or investigator
  -> query_ledger
  -> matcher
  -> duplicate_detection
  -> conditional: write_audit or investigator
  -> investigator
  -> resolution_drafter
  -> write_audit
  -> END
```

`graph_routes.py` owns routing rules:

- Incomplete extraction routes to investigation instead of ledger matching.
- `matched` routes directly to audit.
- Every other status routes through investigation and resolution drafting.

`AgentState` in `src/agents/state.py` is the shared graph state contract. Important fields include invoice image path, extraction output, ledger rows, candidate matches, reconciliation result, investigation, draft, and audit event ID.

### 3. Extraction layer

**Location:** `src/extraction/`

The runtime extractor uses a hybrid approach:

1. OCR reads text, word locations, and confidence values.
2. Heuristic extraction obtains invoice-critical fields from the synthetic template.
3. Field validation checks ID, vendor, date, amount, currency, quantity, and FX-rate plausibility.
4. LayoutLMv3 LoRA inference contributes learned document-layout evidence and can serve as a restricted fallback for selected fields.
5. Ledger-aware repair can conservatively repair extracted values when an exact invoice-ID candidate is available.

The design intentionally avoids relying solely on the LayoutLMv3 model for invoice identity, currency, quantity, and FX rate because the fine-tuning label schema is not a complete invoice schema.

### 4. Ledger and matching layer

**Locations:** `src/agents/nodes/query_ledger_node.py`, `src/matching/`, `src/mcp_servers/`

The query node retrieves the configured ledger table through the BigQuery MCP client. Table IDs come from trusted configuration, not browser/LLM input.

The matcher:

- Searches for an exact invoice-ID ledger candidate.
- Applies conservative ledger-aware repair when appropriate.
- Builds semantic candidates through the embedding matcher and FAISS.
- Promotes the exact identity candidate before semantic-only candidates.
- Runs reconciliation rules against the selected candidate.

Rules evaluate invoice identity and financial fields including amount, currency, quantity, and FX rate. Outputs include a status, confidence, best match, candidate matches, and discrepancy details.

### 5. Exception handling layer

**Location:** `src/agents/`

The investigator converts reconciliation evidence into a structured analyst assessment:

- Summary.
- Root cause.
- Severity.
- Recommended action.
- Dispute reason.

The resolution drafter creates a vendor-facing clarification/dispute draft only for exception paths. Clean matched invoices bypass this layer.

### 6. Audit and approval layer

**Location:** `src/audit/` and `src/services/`

Two independent BigQuery repositories provide persistence:

| Repository | Table | Purpose |
|---|---|---|
| `ReconciliationAuditRepository` | `synthetic_reconciliation_audit` | Immutable event for every completed graph run |
| `DraftApprovalRepository` | `synthetic_draft_approvals` | Approval event for the final editable draft |

The reconciliation audit stores invoice identity, extracted financial values, reconciliation status, confidence, best-match identity, discrepancy details, investigation JSON, draft text, run ID, and timestamp.

The approval table stores reviewer, approval timestamp, invoice ID, reconciliation audit event ID, final draft content, status, environment, and action.

`DraftApprovalService` applies business rules before writing:

- Draft must not be empty.
- Audit event ID must exist.
- Invoice ID must exist.
- Only one open review may exist for the invoice ID in the same environment.

An action of `draft_approved_no_email_sent` is treated as open. A future production workflow must add close/cancel/send state transitions.

## Data flow

```text
Image upload
  -> temporary Gradio file path
  -> graph initial state
  -> OCR and hybrid extraction
  -> structured invoice fields
  -> BigQuery ledger retrieval
  -> exact-ID + semantic candidate matching
  -> reconciliation classification
  -> duplicate audit lookup
  -> audit event
  -> optional investigation and draft
  -> optional draft approval event
  -> review-history BigQuery query
```

## Persistence model

### Ledger table

The synthetic ledger is a source-of-truth dataset for matching. Application runtime should only read it.

### Reconciliation audit table

The audit table is append-only from the application perspective. It supports:

- Duplicate detection through prior `matched` events.
- Review-history reporting.
- Traceability from UI result to graph outcome.
- Downstream audit and operational analysis.

### Draft approvals table

This table persists operator approval state across application restarts. It prevents a second open review from being created for an invoice in the same environment.

## Security boundaries

### Trusted configuration

Environment variables provide project, dataset, ledger-table, audit-table, approval-table, environment, and default reviewer values. Table identifiers are configuration-controlled rather than accepted from UI input.

### Authentication

Local development uses Application Default Credentials. Cloud deployment should use a dedicated Cloud Run service account.

### Authorization

A deployed service account should receive least-privilege permissions:

- Query-job permission in the project.
- Read access to the ledger dataset/table.
- Write and read access to reconciliation audit and approval tables.

### Secrets

Do not store service-account JSON keys, Hugging Face tokens, or API keys in source code. Use Secret Manager in deployment environments.

### Human control

The app does not send email. Approval records a local audit event only. Any future email workflow must require resolved recipient details, final body review, persisted approval, and a separate explicit send confirmation.

## Testing strategy

Tests are organized by domain:

```text
tests/agents/      graph routes, nodes, graph structure, matching
tests/audit/       audit repository behavior
tests/extraction/  OCR/extraction/validation/repair logic
tests/matching/    embedding matcher behavior
tests/services/    draft approval business rules
tests/synthetic/   generation and rendering helpers
tests/evaluation/  evaluation utilities
tests/ui/          graph-runner behavior
```

Active unit tests mock external repositories where appropriate so they do not create BigQuery rows. Legacy structured-input graph tests are archived because the production graph now begins with an invoice image path and extraction.

## Deployment target

The intended deployment target is a private Google Cloud Run service.

```text
User browser
  -> authenticated Cloud Run service
  -> Gradio application
  -> Cloud Run service identity
  -> BigQuery ledger + audit + approval tables
```

The deployment image must contain the application code and any model artifacts required for inference, or model artifacts must be loaded from a controlled artifact store at startup. Cloud Run environment variables configure the synthetic environment; Secret Manager supplies sensitive values.

## Design trade-offs

- **Hybrid extraction over model-only extraction:** improves schema completeness and template reliability.
- **Exact identity before semantic retrieval:** prevents near-identical vendor records from displacing a verified invoice-ID record.
- **BigQuery audit persistence:** provides durable operational history and duplicate detection but is not a transactional lock service.
- **Single-user open-review control:** sufficient for the prototype; multi-user production needs transactional review-state enforcement.
- **No email transmission:** keeps the current system safe for demonstrations and evaluation.
