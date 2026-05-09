# Self-contained Containerfile — builds from this project folder only.
# docker build -t gnomon -f Containerfile .
FROM python:3.11-slim

WORKDIR /app

# Vendored harness_core (copied into every project for independence)
COPY harness_core ./harness_core
RUN pip install --no-cache-dir -e ./harness_core

COPY pyproject.toml ./pyproject.toml
COPY src ./src
COPY tests ./tests
RUN pip install --no-cache-dir -e '.[dev]'

ENV PYTHONUNBUFFERED=1
EXPOSE 8011

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8011/healthz', timeout=2)" || exit 1

CMD ["uvicorn", "gnomon.app:app", "--host", "0.0.0.0", "--port", "8011"]
