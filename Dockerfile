FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY api /app/api

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir /app/api

RUN mkdir -p /data/pdfs && chown -R appuser:appuser /app /data

USER appuser

WORKDIR /app/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
