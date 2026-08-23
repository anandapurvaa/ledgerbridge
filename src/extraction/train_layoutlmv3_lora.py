# src/extraction/train_layoutlmv3_lora.py
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
    set_seed,
)

from src.extraction.class_weights import (
    calculate_class_weights,
    format_class_weights,
)
from src.extraction.weighted_trainer import (
    WeightedTokenClassificationTrainer,
)
from src.extraction.layoutlmv3_dataset import (
    BASE_MODEL_NAME,
    create_encoded_sroie,
    create_processor,
)
from src.extraction.metrics import (
    compute_token_classification_metrics,
)
from src.extraction.sroie_preprocessor import (
    ID_TO_LABEL,
    LABEL_LIST,
    LABEL_TO_ID,
)

DEFAULT_MODEL_DIR = Path("models/layoutlmv3_lora")
DEFAULT_ARTIFACT_DIR = Path("artifacts/extraction")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fine-tune LayoutLMv3 on SROIE using LoRA "
            "for receipt field extraction."
        )
    )

    parser.add_argument(
        "--epochs",
        type=float,
        default=1.0,
        help="Use 1 for smoke testing; use 8-15 for real GPU training.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_MODEL_DIR,
    )

    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
    )

    return parser.parse_args()


def create_model() -> torch.nn.Module:
    base_model = AutoModelForTokenClassification.from_pretrained(
        BASE_MODEL_NAME,
        num_labels=len(LABEL_LIST),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
        ignore_mismatched_sizes=True,
    )

    lora_config = LoraConfig(
        task_type=TaskType.TOKEN_CLS,
        r=8,
        lora_alpha=16,
        lora_dropout=0.10,
        target_modules=[
            "query",
            "value",
        ],
        modules_to_save=[
            "classifier",
        ],
        bias="none",
    )

    model = get_peft_model(
        base_model,
        lora_config,
    )

    model.print_trainable_parameters()

    return model


def main() -> None:
    args = parse_args()

    set_seed(args.seed)

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.artifact_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    use_cuda = torch.cuda.is_available()

    print(f"CUDA available: {use_cuda}")

    if use_cuda:
        print(
            "GPU: "
            f"{torch.cuda.get_device_name(0)}"
        )
    else:
        print(
            "Running on CPU. Use this only for a short smoke test."
        )

    dataset = create_encoded_sroie(
        max_length=args.max_length,
    )

    processor = create_processor()
    model = create_model()

    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=(
            args.gradient_accumulation_steps
        ),
        num_train_epochs=args.epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        fp16=use_cuda,
        report_to="none",
        remove_unused_columns=False,
        save_total_limit=2,
        dataloader_num_workers=0,
    )

    data_collator = DataCollatorForTokenClassification(
        tokenizer=processor.tokenizer,
        padding=False,
    )

    class_weights = calculate_class_weights(
        dataset["train"],
    )

    print("\nClass weights:")
    print(
        json.dumps(
            format_class_weights(class_weights),
            indent=2,
        )
    )

    trainer = WeightedTokenClassificationTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        processing_class=processor,
        data_collator=data_collator,
        compute_metrics=compute_token_classification_metrics,
        class_weights=class_weights,
    )

    trainer.train()

    evaluation_metrics = trainer.evaluate()

    trainer.save_model(
        str(args.output_dir),
    )

    processor.save_pretrained(
        str(args.output_dir),
    )

    metrics_path = (
        args.artifact_dir
        / "layoutlmv3_lora_metrics.json"
    )

    with metrics_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            evaluation_metrics,
            file,
            indent=2,
        )

    print("\nFinal evaluation metrics:")
    print(
        json.dumps(
            evaluation_metrics,
            indent=2,
        )
    )

    print(
        f"\nSaved LoRA adapter and processor to: "
        f"{args.output_dir}"
    )

    print(
        f"Saved evaluation metrics to: "
        f"{metrics_path}"
    )


if __name__ == "__main__":
    main()