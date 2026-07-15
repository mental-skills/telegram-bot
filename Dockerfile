FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]"

COPY app ./app
COPY assets ./assets
COPY content ./content
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./

CMD ["python", "-m", "app.main"]
