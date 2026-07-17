FROM node:22.18.0-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package.json /frontend/package.json
COPY frontend/tsconfig.json /frontend/tsconfig.json
COPY frontend/vite.config.ts /frontend/vite.config.ts
COPY frontend/index.html /frontend/index.html
COPY frontend/src /frontend/src
COPY frontend/tests /frontend/tests

RUN npm install \
    && npm run build

FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY pyproject.toml /app/pyproject.toml
COPY --from=frontend-build /frontend/dist /app/frontend/dist

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir /app

RUN mkdir -p /data/pdfs && chown -R appuser:appuser /app /data

USER appuser

WORKDIR /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
