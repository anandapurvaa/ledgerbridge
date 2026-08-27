from __future__ import annotations

import os
import random
import html
import json
import tempfile
from pathlib import Path
from typing import Any

import gradio as gr

from src.audit.reconciliation_audit_repository import (
    ReconciliationAuditRepository,
)
from src.services.draft_approval_service import (
    approve_draft_for_review,
)
from src.ui.graph_runner import run_reconciliation_graph


STYLE_PATH = Path(__file__).parent / "assets" / "style.css"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_INVOICES_DIR = PROJECT_ROOT / "data" / "demo_invoices"

DEMO_SCENARIOS = {
    "Clean match": "matched",
    "Amount mismatch": "amount_mismatch",
    "FX mismatch": "fx_mismatch",
    "Quantity mismatch": "quantity_mismatch",
    "Duplicate charge": "duplicate_charge",
}
CANDIDATE_HEADERS = [
    "Rank",
    "Invoice ID",
    "Vendor",
    "Invoice Date",
    "Amount",
    "Currency",
    "Quantity",
    "Semantic Score",
]

HISTORY_HEADERS = [
    "Timestamp (UTC)",
    "Invoice ID",
    "Vendor",
    "Status",
    "Root Cause",
    "Severity",
    "Amount",
    "Confidence",
    "Review Status",
    "Audit Event ID",
]

ROOT_CAUSE_OPTIONS = [
    "All root causes",
    "amount_mismatch",
    "ambiguous_match",
    "duplicate_charge",
    "unmatched",
]

SEVERITY_OPTIONS = [
    "All severities",
    "low",
    "medium",
    "high",
]


def save_draft_for_download(draft: str) -> str:
    output_path = Path(tempfile.gettempdir()) / (
        "ledgerbridge_dispute_draft.txt"
    )
    output_path.write_text(draft or "", encoding="utf-8")
    return str(output_path)


def format_money(
    amount: Any,
    currency: Any = "",
) -> str:
    try:
        number = float(amount)
    except (TypeError, ValueError):
        return "—"

    suffix = f" {currency}" if currency else ""
    return f"{number:,.2f}{suffix}"


def safe_html(value: Any) -> str:
    return html.escape(
        str(value if value not in (None, "") else "—")
    )


def parse_json_object(value: Any) -> dict[str, Any]:
    if not value:
        return {}

    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}

    return parsed if isinstance(parsed, dict) else {}


def build_candidate_table(
    candidate_matches: list[dict[str, Any]],
) -> list[list[Any]]:
    rows: list[list[Any]] = []

    for candidate in candidate_matches:
        record = candidate.get("ledger_record", {})
        score = candidate.get("semantic_score")

        rows.append(
            [
                candidate.get("rank", ""),
                record.get("invoice_id", "—"),
                record.get("vendor", "—"),
                record.get("invoice_date", "—"),
                format_money(
                    record.get("amount"),
                    record.get("currency", ""),
                ),
                record.get("currency", "—"),
                record.get("quantity", "—"),
                (
                    f"{score:.2%}"
                    if isinstance(score, (int, float))
                    else "—"
                ),
            ]
        )

    return rows


def build_invoice_fields_html(
    fields: dict[str, Any],
) -> str:
    metadata = fields.get("extraction_metadata", {})
    ocr_confidence = metadata.get("ocr_mean_confidence")

    if isinstance(ocr_confidence, (int, float)):
        ocr_confidence_display = f"{ocr_confidence:.1f}%"
    else:
        ocr_confidence_display = ocr_confidence

    definitions = [
        ("Invoice ID", fields.get("invoice_id"), True),
        ("Vendor", fields.get("vendor"), False),
        ("Invoice date", fields.get("invoice_date"), False),
        (
            "Invoice total",
            format_money(
                fields.get("amount"),
                fields.get("currency", ""),
            ),
            True,
        ),
        ("Currency", fields.get("currency"), False),
        ("Quantity", fields.get("quantity"), True),
        ("FX rate", fields.get("fx_rate"), True),
        ("OCR confidence", ocr_confidence_display, True),
        ("Extractor", metadata.get("extractor"), False),
    ]

    cards = [
        (
            "<div class='lb-field'>"
            f"<span class='lb-field-label'>{safe_html(label)}</span>"
            "<span class='lb-field-value"
            f"{' lb-mono' if mono else ''}'>"
            f"{safe_html(value)}</span>"
            "</div>"
        )
        for label, value, mono in definitions
    ]

    return (
        "<div class='lb-card'>"
        "<h3>Extracted invoice details</h3>"
        "<div class='lb-field-grid'>"
        f"{''.join(cards)}"
        "</div>"
        "</div>"
    )


def build_status_html(
    reconciliation: dict[str, Any],
) -> str:
    status = str(
        reconciliation.get("status", "unknown")
    ).lower()
    confidence = reconciliation.get("confidence", 0.0)

    try:
        confidence_display = f"{float(confidence):.1%}"
    except (TypeError, ValueError):
        confidence_display = "—"

    details = reconciliation.get("discrepancy_details", {})
    reason = details.get("reason")

    if not reason and status == "amount_mismatch":
        reason = (
            f"Invoice total "
            f"{format_money(details.get('invoice_amount'))}; "
            f"ledger total "
            f"{format_money(details.get('ledger_amount'))}; "
            f"variance "
            f"{format_money(details.get('amount_delta'))}."
        )

    if not reason and status == "matched":
        reason = (
            "Invoice identity and key financial fields agree "
            "within configured tolerances."
        )

    if not reason and status == "duplicate_charge":
        reason = (
            "A successful reconciliation for this invoice "
            "already exists in the audit trail."
        )

    if not reason:
        reason = "The invoice requires review."

    return (
        f"<div class='lb-status {safe_html(status)}'>"
        "<div class='lb-status-head'>"
        f"<h2>{safe_html(status.replace('_', ' ').title())}</h2>"
        "<span class='lb-status-confidence'>"
        "<span class='lb-status-confidence-label'>Confidence</span>"
        "<span class='lb-status-confidence-value'>"
        f"{safe_html(confidence_display)}</span>"
        "</span>"
        "</div>"
        f"<p>{safe_html(reason)}</p>"
        "</div>"
    )


def build_investigation_html(
    investigation: dict[str, Any],
) -> str:
    if not investigation:
        return (
            "<div class='lb-empty'>"
            "No investigation was needed. This invoice followed "
            "the clean-match workflow."
            "</div>"
        )

    summary = investigation.get(
        "summary",
        "Investigation completed.",
    )
    root_cause = str(
        investigation.get("root_cause", "Not specified")
    ).replace("_", " ").title()
    severity = str(
        investigation.get("severity", "Not specified")
    ).title()
    recommended_action = investigation.get(
        "recommended_action",
        "Review the reconciliation details.",
    )

    return (
        "<div class='lb-investigation'>"
        "<h4>Analyst assessment</h4>"
        "<p><strong>Summary:</strong> "
        f"{safe_html(summary)}</p>"
        "<p><strong>Root cause:</strong> "
        f"{safe_html(root_cause)}</p>"
        "<p><strong>Severity:</strong> "
        f"{safe_html(severity)}</p>"
        "<p><strong>Recommended action:</strong> "
        f"{safe_html(recommended_action)}</p>"
        "</div>"
    )


def build_audit_html(audit_event_id: str) -> str:
    if not audit_event_id:
        return (
            "<div class='lb-audit'>"
            "No audit event has been written yet."
            "</div>"
        )

    return (
        "<div class='lb-audit'>"
        "<strong>Audit event recorded:</strong> "
        f"<code>{safe_html(audit_event_id)}</code>"
        "</div>"
    )


def build_uploaded_file_html(
    invoice_file: str | None,
) -> str:
    if not invoice_file:
        return (
            "<div class='lb-upload-name lb-upload-empty'>"
            "No invoice file selected."
            "</div>"
        )

    filename = Path(invoice_file).name

    return (
        "<div class='lb-upload-name'>"
        "<span class='lb-upload-label'>Selected file</span>"
        f"<span class='lb-upload-value'>{safe_html(filename)}</span>"
        "</div>"
    )

def load_demo_invoice(
    scenario_label: str,
) -> tuple[str | None, str]:
    category = DEMO_SCENARIOS.get(scenario_label)

    if not category:
        return (
            None,
            (
                "<div class='lb-upload-name lb-upload-empty'>"
                "Choose a demo scenario first."
                "</div>"
            ),
        )

    candidates = sorted(
        DEMO_INVOICES_DIR.glob(f"{category}_*.png")
    )

    if not candidates:
        return (
            None,
            (
                "<div class='lb-upload-name lb-upload-empty'>"
                "No demo invoice is available for this scenario."
                "</div>"
            ),
        )

    selected_file = random.choice(candidates)

    return (
        str(selected_file),
        (
            "<div class='lb-upload-name lb-demo-selected'>"
            "<span class='lb-upload-label'>Demo invoice loaded</span>"
            f"<span class='lb-upload-value'>{safe_html(selected_file.name)}</span>"
            "</div>"
        ),
    )

def reconcile_invoice_ui(
    invoice_file: str | None,
    user_query: str,
):
    empty = (
        "<div class='lb-empty'>"
        "Upload an invoice image to begin reconciliation."
        "</div>"
    )

    if not invoice_file:
        return (
            empty,
            empty,
            [],
            empty,
            "",
            empty,
            "",
            "",
            "",
        )

    result = run_reconciliation_graph(
        invoice_image_path=Path(invoice_file),
        user_query=user_query or (
            "Reconcile this invoice and create a dispute "
            "draft if a discrepancy is found."
        ),
    )

    fields = result.get("extracted_fields", {})
    reconciliation = result.get("reconciliation_result", {})
    status = reconciliation.get("status", "")

    return (
        build_invoice_fields_html(fields),
        build_status_html(reconciliation),
        build_candidate_table(
            result.get("candidate_matches", [])
        ),
        build_investigation_html(
            result.get("investigation", {})
        ),
        result.get("dispute_letter_draft", ""),
        build_audit_html(result.get("audit_event_id", "")),
        json.dumps(fields, indent=2, default=str),
        result.get("audit_event_id", ""),
        fields.get("invoice_id", ""),
        status,
    )


def approve_draft_ui(
    draft: str,
    audit_event_id: str,
    invoice_id: str,
    reconciliation_status: str,
) -> str:
    try:
        approval_event_id = approve_draft_for_review(
            draft=draft,
            audit_event_id=audit_event_id,
            invoice_id=invoice_id,
            reconciliation_status=reconciliation_status,
        )
    except (ValueError, RuntimeError) as error:
        return (
            "<div class='lb-status error'>"
            "<h2>Approval failed</h2>"
            f"<p>{safe_html(error)}</p>"
            "</div>"
        )

    return (
        "<div class='lb-status matched'>"
        "<h2>Draft approved for review</h2>"
        "<p>The approval was recorded. No email has been sent.</p>"
        "<p><strong>Approval event ID:</strong> "
        f"<code>{safe_html(approval_event_id)}</code></p>"
        "</div>"
    )

def load_review_history(
    root_cause: str,
    severity: str,
) -> tuple[list[list[Any]], str]:
    """Load audit history using the selected optional filters."""
    selected_root_cause = (
        None
        if root_cause == "All root causes"
        else root_cause
    )
    selected_severity = (
        None
        if severity == "All severities"
        else severity
    )

    try:
        repository = ReconciliationAuditRepository()
        records = repository.list_history(
            root_cause=selected_root_cause,
            severity=selected_severity,
        )
    except Exception as error:
        return [], (
            "<div class='lb-status error'>"
            "<h2>Unable to load review history</h2>"
            f"<p>{safe_html(error)}</p>"
            "</div>"
        )

    rows: list[list[Any]] = []

    for record in records:
        investigation = parse_json_object(
            record.get("investigation_json")
        )
        timestamp = record.get("event_timestamp", "")
        confidence = record.get("confidence")

        try:
            confidence_display = f"{float(confidence):.1%}"
        except (TypeError, ValueError):
            confidence_display = "—"

        review_status = (
            "Review required"
            if investigation
            else "No review required"
        )

        rows.append(
            [
                str(timestamp),
                record.get("invoice_id", "—"),
                record.get("vendor", "—"),
                record.get("reconciliation_status", "—"),
                investigation.get("root_cause", "—"),
                investigation.get("severity", "—"),
                format_money(
                    record.get("amount"),
                    record.get("currency", ""),
                ),
                confidence_display,
                review_status,
                record.get("audit_event_id", "—"),
            ]
        )

    if rows:
        message = (
            "<div class='lb-audit'>"
            f"Showing <strong>{len(rows)}</strong> reconciliation "
            "event(s), newest first."
            "</div>"
        )
    else:
        message = (
            "<div class='lb-empty'>"
            "No reconciliation events match the selected filters."
            "</div>"
        )

    return rows, message


def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="LedgerBridge Reconciliation Console",
    ) as app:
        gr.HTML(
            """
            <section class="lb-hero">
                <span class="lb-hero-kicker">Reconciliation Console</span>
                <h1>LedgerBridge</h1>
                <p>
                    Invoice reconciliation workspace for extraction,
                    ledger verification, exception review, and
                    controlled draft approval.
                </p>
            </section>
            """
        )

        with gr.Tabs():
            with gr.Tab("Reconcile invoice"):
                invoice_id_state = gr.State("")
                reconciliation_status_state = gr.State("")
                audit_event_id_state = gr.State("")

                with gr.Row(equal_height=False):
                    with gr.Column(scale=1, min_width=330):
                        with gr.Group(elem_classes=["lb-card"]):
                            gr.Markdown("### Start a reconciliation")

                            # --- Demo scenario loader -----------------
                            with gr.Group(elem_classes=["lb-subpanel"]):
                                gr.HTML(
                                    "<div class='lb-demo-heading'>"
                                    "Select a demo scenario</div>"  #test
                                )

                                with gr.Row(
                                    equal_height=True,
                                    elem_classes=["lb-demo-row"],
                                ):
                                    demo_scenario = gr.Dropdown(
                                        choices=list(
                                            DEMO_SCENARIOS.keys()
                                        ),
                                        value="Amount mismatch",
                                        label="Demo scenario",
                                        show_label=False,
                                        container=False,
                                        elem_id="demo-scenario",
                                    )

                                    load_demo_button = gr.Button(
                                        "Load demo",
                                        variant="secondary",
                                        elem_id="load-demo-invoice",
                                    )

                                gr.HTML(
                                    "<div class='lb-demo-note'>"
                                    "Load a sample invoice, then "
                                    "select Run reconciliation."
                                    "</div>"
                                )

                            # --- Invoice upload ------------------------
                            with gr.Group(elem_classes=["lb-subpanel"]):
                                invoice_file = gr.File(
                                    label="Invoice image",
                                    file_types=["image"],
                                    type="filepath",
                                    elem_id="invoice-image-upload",
                                )

                                uploaded_file_name_html = gr.HTML(
                                    value=(
                                        "<div class='lb-upload-name "
                                        "lb-upload-empty'>"
                                        "No invoice file selected."
                                        "</div>"
                                    )
                                )

                            # --- Review instruction --------------------
                            with gr.Group(elem_classes=["lb-subpanel"]):
                                gr.HTML(
                                    "<div class='lb-component-label'>"
                                    "Review instruction</div>"
                                )

                                user_query = gr.Textbox(
                                    value=(
                                        "Reconcile this invoice and "
                                        "create a dispute draft if a "
                                        "discrepancy is found."
                                    ),
                                    lines=3,
                                    show_label=False,
                                    elem_id="review-instruction",
                                )

                            run_button = gr.Button(
                                "Run reconciliation",
                                variant="primary",
                                elem_id="run-reconciliation",
                            )

                            gr.Markdown(
                                """
                                **Workflow**

                                1. Extract invoice details  
                                2. Compare against the ledger  
                                3. Investigate exceptions  
                                4. Draft and approve a response when needed
                                """,
                                elem_id="workflow-steps",
                                elem_classes=["lb-workflow"],
                            )

                    with gr.Column(scale=3, min_width=650):
                        with gr.Row(equal_height=False):
                            with gr.Column(scale=3):
                                reconciliation_status_html = gr.HTML(
                                    value=(
                                        "<div class='lb-empty'>"
                                        "Upload an invoice and select "
                                        "<strong>Run reconciliation</strong>."
                                        "</div>"
                                    )
                                )

                            with gr.Column(scale=2):
                                audit_html = gr.HTML(
                                    value=(
                                        "<div class='lb-empty'>"
                                        "Audit status will appear here "
                                        "after processing."
                                        "</div>"
                                    )
                                )

                        gr.HTML(
                            "<div class='lb-section-title'>"
                            "Invoice details"
                            "</div>"
                        )

                        extracted_fields_html = gr.HTML(
                            value=(
                                "<div class='lb-empty'>"
                                "Extracted fields will appear here."
                                "</div>"
                            )
                        )

                        gr.HTML(
                            "<div class='lb-section-title'>"
                            "Ledger candidates"
                            "</div>"
                        )

                        candidate_matches_table = gr.Dataframe(
                            headers=CANDIDATE_HEADERS,
                            datatype=[
                                "number",
                                "str",
                                "str",
                                "str",
                                "str",
                                "str",
                                "number",
                                "str",
                            ],
                            value=[],
                            interactive=False,
                            wrap=True,
                            label="Top candidate matches",
                            elem_id="candidate-matches-table",
                            elem_classes=["lb-ledger-table"],
                        )

                        gr.HTML(
                            "<div class='lb-section-title'>"
                            "Exception review"
                            "</div>"
                        )

                        investigation_html = gr.HTML(
                            value=(
                                "<div class='lb-empty'>"
                                "Investigation findings appear for "
                                "mismatches, duplicates, or ambiguous cases."
                                "</div>"
                            )
                        )

                        gr.HTML(
                            "<div class='lb-section-title'>"
                            "Resolution draft"
                            "</div>"
                        )

                        dispute_draft = gr.Textbox(
                            label="Editable vendor communication",
                            placeholder=(
                                "A draft will appear here when a "
                                "discrepancy requires vendor communication."
                            ),
                            lines=14,
                            max_lines=30,
                            elem_id="resolution-draft",
                        )

                        with gr.Row():
                            download_button = gr.DownloadButton(
                                label="Download draft",
                            )

                            approve_button = gr.Button(
                                "Approve draft for review",
                                variant="primary",
                            )

                        approval_status_html = gr.HTML(value="")

                        with gr.Accordion(
                            "Technical details",
                            open=False,
                            elem_id="technical-details",
                        ):
                            technical_extraction_json = gr.Code(
                                label="Raw extraction output",
                                language="json",
                                interactive=False,
                            )

                invoice_file.change(
                    fn=build_uploaded_file_html,
                    inputs=[invoice_file],
                    outputs=[uploaded_file_name_html],
                )

                load_demo_button.click(
                    fn=load_demo_invoice,
                    inputs=[demo_scenario],
                    outputs=[invoice_file, uploaded_file_name_html],
                )

                run_button.click(
                    fn=reconcile_invoice_ui,
                    inputs=[invoice_file, user_query],
                    outputs=[
                        extracted_fields_html,
                        reconciliation_status_html,
                        candidate_matches_table,
                        investigation_html,
                        dispute_draft,
                        audit_html,
                        technical_extraction_json,
                        audit_event_id_state,
                        invoice_id_state,
                        reconciliation_status_state,
                    ],
                )

                download_button.click(
                    fn=save_draft_for_download,
                    inputs=[dispute_draft],
                    outputs=[download_button],
                )

                approve_button.click(
                    fn=approve_draft_ui,
                    inputs=[
                        dispute_draft,
                        audit_event_id_state,
                        invoice_id_state,
                        reconciliation_status_state,
                    ],
                    outputs=[approval_status_html],
                )

            with gr.Tab("Review history"):
                gr.Markdown("## Review history")
                gr.Markdown(
                    "Browse reconciliation events and filter them by "
                    "investigation root cause or severity."
                )

                with gr.Row():
                    history_root_cause = gr.Dropdown(
                        choices=ROOT_CAUSE_OPTIONS,
                        value="All root causes",
                        label="Root cause",
                    )

                    history_severity = gr.Dropdown(
                        choices=SEVERITY_OPTIONS,
                        value="All severities",
                        label="Severity",
                    )

                    history_refresh_button = gr.Button(
                        "Refresh history",
                        variant="primary",
                    )

                history_message_html = gr.HTML(
                    value=(
                        "<div class='lb-empty'>"
                        "Choose filters and select Refresh history."
                        "</div>"
                    )
                )

                history_table = gr.Dataframe(
                    headers=HISTORY_HEADERS,
                    datatype=[
                        "str",
                        "str",
                        "str",
                        "str",
                        "str",
                        "str",
                        "str",
                        "str",
                        "str",
                        "str",
                    ],
                    value=[],
                    interactive=False,
                    wrap=True,
                    label="Reconciliation review history",
                    elem_classes=["lb-ledger-table"],
                )

                history_refresh_button.click(
                    fn=load_review_history,
                    inputs=[history_root_cause, history_severity],
                    outputs=[history_table, history_message_html],
                )

    return app


if __name__ == "__main__":
    import os

    app = build_app()

    app.launch(
        server_name="0.0.0.0",
        server_port=int(
            os.environ.get("PORT", "8080")
        ),
        css_paths=[str(STYLE_PATH)],
        footer_links=[],
    )
