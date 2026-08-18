FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/riftcoach

RUN groupadd --system riftcoach \
    && useradd --system --gid riftcoach --home-dir /opt/riftcoach riftcoach

COPY pyproject.toml README.md LICENSE ./
COPY app ./app
RUN python -m pip install --no-cache-dir .

COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY skills ./skills
COPY prompt_programs ./prompt_programs
COPY data/rag_docs ./data/rag_docs
COPY scripts/run_review_worker.py ./scripts/run_review_worker.py
COPY scripts/run_packaging_smoke.py ./scripts/run_packaging_smoke.py

RUN mkdir -p /var/lib/riftcoach/runs /var/lib/riftcoach/ddragon \
    && chown -R riftcoach:riftcoach /opt/riftcoach /var/lib/riftcoach

USER riftcoach

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.api.composition:create_composed_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
