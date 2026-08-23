# src/extraction/entity_decoder.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EntitySpan:
    entity_type: str
    text: str
    score: float
    start_word: int
    end_word: int


def split_bio_label(label: str) -> tuple[str, str]:
    if label == "O":
        return "O", ""

    if "-" not in label:
        return "B", label

    prefix, entity_type = label.split("-", maxsplit=1)

    if prefix not in {"B", "I"}:
        return "B", entity_type

    return prefix, entity_type


def decode_bio_spans(
    words: list[str],
    labels: list[str],
    scores: list[float],
) -> list[EntitySpan]:
    """
    Convert word-level BIO labels into entity spans.

    Handles malformed I-tags safely: an I-TOTAL after O is treated as
    the start of a new TOTAL span rather than discarded.
    """
    if not (
        len(words) == len(labels) == len(scores)
    ):
        raise ValueError(
            "words, labels, and scores must have identical lengths."
        )

    spans: list[EntitySpan] = []

    active_type: str | None = None
    active_words: list[str] = []
    active_scores: list[float] = []
    active_start = 0

    def close_active_span(end_word: int) -> None:
        nonlocal active_type
        nonlocal active_words
        nonlocal active_scores
        nonlocal active_start

        if active_type is None:
            return

        spans.append(
            EntitySpan(
                entity_type=active_type,
                text=" ".join(active_words),
                score=round(
                    sum(active_scores) / len(active_scores),
                    4,
                ),
                start_word=active_start,
                end_word=end_word,
            )
        )

        active_type = None
        active_words = []
        active_scores = []
        active_start = 0

    for index, (word, label, score) in enumerate(
        zip(words, labels, scores, strict=True)
    ):
        prefix, entity_type = split_bio_label(label)

        if prefix == "O":
            close_active_span(index - 1)
            continue

        starts_new_span = (
            active_type is None
            or prefix == "B"
            or entity_type != active_type
        )

        if starts_new_span:
            close_active_span(index - 1)

            active_type = entity_type
            active_words = [word]
            active_scores = [score]
            active_start = index
        else:
            active_words.append(word)
            active_scores.append(score)

    close_active_span(len(words) - 1)

    return spans