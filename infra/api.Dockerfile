FROM docker.1panel.live/library/python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    PIP_TRUSTED_HOST=mirrors.aliyun.com

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY apps/api ./apps/api
COPY course_packs ./course_packs
COPY scripts/sync_knowledge_index.py ./scripts/sync_knowledge_index.py

RUN python -m pip install .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
