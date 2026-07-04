FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/
COPY pyproject.toml .
COPY models/ ./models/

RUN pip install --no-cache-dir -e .

RUN mkdir -p data/uploads data/generated models outputs

ENV PYTHONPATH=/app/src

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "mauripay.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
