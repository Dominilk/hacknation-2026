FROM python:3.13-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# todo: is global static identity the right call?
RUN git config --global user.email "ai@weave.at"
RUN git config --global user.name "Weave AI"

WORKDIR /app

COPY pyproject.toml ./
COPY shared/ shared/
COPY core/ core/

RUN pip install --no-cache-dir uv && uv sync --package core

CMD ["uv", "run", "--package", "core", "uvicorn", "core.server:app", "--host", "0.0.0.0", "--port", "8000"]
