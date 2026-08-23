# src/extraction/weighted_trainer.py
from __future__ import annotations

from typing import Any

import torch
from torch.nn import CrossEntropyLoss
from transformers import Trainer


class WeightedTokenClassificationTrainer(Trainer):
    """
    Trainer that uses class-weighted CrossEntropyLoss for token labels.
    """

    def __init__(
        self,
        *args: Any,
        class_weights: torch.Tensor,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            *args,
            **kwargs,
        )

        self.class_weights = class_weights

    def compute_loss(
        self,
        model: torch.nn.Module,
        inputs: dict[str, Any],
        return_outputs: bool = False,
        num_items_in_batch: int | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, Any]:
        labels = inputs.pop("labels")

        outputs = model(**inputs)
        logits = outputs.logits

        loss_function = CrossEntropyLoss(
            weight=self.class_weights.to(
                logits.device
            ),
            ignore_index=-100,
        )

        loss = loss_function(
            logits.view(-1, model.config.num_labels),
            labels.view(-1),
        )

        return (
            (loss, outputs)
            if return_outputs
            else loss
        )