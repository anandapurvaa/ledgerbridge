# src/matching/embedding_matcher.py
from __future__ import annotations

from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.matching.schemas import InvoiceRecord, MatchCandidate


class LedgerEmbeddingMatcher:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.model = SentenceTransformer(model_name)
        self.index: faiss.Index | None = None
        self.ledger_records: list[InvoiceRecord] = []

    @staticmethod
    def record_to_text(record: InvoiceRecord) -> str:
        line_items = record.line_items or []

        return (
            f"vendor: {record.vendor} | "
            f"invoice id: {record.invoice_id} | "
            f"date: {record.invoice_date} | "
            f"amount: {record.amount:.2f} {record.currency} | "
            f"quantity: {record.quantity} | "
            f"fx rate: {record.fx_rate:.4f} | "
            f"line items: {line_items}"
        )

    def build_index(self, rows: list[dict[str, Any]]) -> None:
        self.ledger_records = [InvoiceRecord.model_validate(row) for row in rows]

        if not self.ledger_records:
            raise ValueError("Cannot build a FAISS index from an empty ledger.")

        texts = [self.record_to_text(record) for record in self.ledger_records]

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

    def search(
        self,
        invoice: InvoiceRecord,
        top_k: int = 5,
    ) -> list[MatchCandidate]:
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        top_k = min(top_k, len(self.ledger_records))

        query_embedding = self.model.encode(
            [self.record_to_text(invoice)],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype("float32")

        scores, indices = self.index.search(query_embedding, top_k)

        candidates: list[MatchCandidate] = []

        for rank, (score, index) in enumerate(
            zip(scores[0], indices[0], strict=True),
            start=1,
        ):
            candidates.append(
                MatchCandidate(
                    ledger_record=self.ledger_records[int(index)],
                    semantic_score=round(float(score), 4),
                    rank=rank,
                )
            )

        return candidates