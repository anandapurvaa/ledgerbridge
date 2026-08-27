FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgomp1 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src ./src
COPY data/demo_invoices ./data/demo_invoices
COPY models/layoutlmv3_lora_weighted ./models/layoutlmv3_lora_weighted

EXPOSE 8080

CMD ["python", "-m", "src.ui.app"]