from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from peft import PeftModel
from PIL import Image
from transformers import (
    AutoModelForTokenClassification,
    AutoProcessor,
)

from src.extraction.entity_decoder import decode_bio_spans
from src.extraction.field_normalizer import (
    normalize_layoutlmv3_output,
)
from src.extraction.sroie_preprocessor import (
    ID_TO_LABEL,
    LABEL_LIST,
    LABEL_TO_ID,
)

BASE_MODEL_NAME = "microsoft/layoutlmv3-base"


class LayoutLMv3Extractor:
    def __init__(
        self,
        model_dir: str | Path = "models/layoutlmv3_lora_weighted",
        device: str | None = None,
    ) -> None:
        self.model_dir = Path(model_dir)

        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Model directory does not exist: {self.model_dir}"
            )

        if device is None:
            device = (
                "cuda"
                if torch.cuda.is_available()
                else "cpu"
            )

        self.device = torch.device(device)

        self.processor = AutoProcessor.from_pretrained(
            BASE_MODEL_NAME,
            apply_ocr=False,
        )

        base_model = AutoModelForTokenClassification.from_pretrained(
            BASE_MODEL_NAME,
            num_labels=len(LABEL_LIST),
            id2label=ID_TO_LABEL,
            label2id=LABEL_TO_ID,
            ignore_mismatched_sizes=True,
        )

        self.model = PeftModel.from_pretrained(
            base_model,
            self.model_dir,
        )

        self.model.to(self.device)
        self.model.eval()

    def predict(
        self,
        image: Image.Image,
        words: list[str],
        bboxes: list[list[int]],
    ) -> dict[str, Any]:
        encoding = self.processor(
            images=image,
            text=words,
            boxes=bboxes,
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors="pt",
        )

        model_inputs = {
            key: value.to(self.device)
            for key, value in encoding.items()
        }

        with torch.no_grad():
            logits = self.model(
                **model_inputs
            ).logits

        probabilities = torch.softmax(
            logits,
            dim=-1,
        )[0]

        prediction_ids = torch.argmax(
            probabilities,
            dim=-1,
        ).tolist()

        prediction_scores = torch.max(
            probabilities,
            dim=-1,
        ).values.tolist()

        word_ids = encoding.word_ids(batch_index=0)

        word_labels: dict[int, str] = {}
        word_scores: dict[int, float] = {}

        for token_index, word_id in enumerate(word_ids):
            if word_id is None:
                continue

            # Use only the first subtoken belonging to a word.
            if word_id not in word_labels:
                word_labels[word_id] = ID_TO_LABEL[
                    prediction_ids[token_index]
                ]
                word_scores[word_id] = round(
                    float(prediction_scores[token_index]),
                    4,
                )

        aligned_labels = [
            word_labels.get(word_index, "O")
            for word_index in range(len(words))
        ]

        aligned_scores = [
            word_scores.get(word_index, 0.0)
            for word_index in range(len(words))
        ]

        spans = decode_bio_spans(
            words=words,
            labels=aligned_labels,
            scores=aligned_scores,
        )

        raw_text = " ".join(words)

        extracted_fields = normalize_layoutlmv3_output(
            spans=spans,
            raw_text=raw_text,
        )

        return {
            "extracted_fields": extracted_fields,
            "word_labels": aligned_labels,
            "word_scores": aligned_scores,
            "spans": spans,
        }