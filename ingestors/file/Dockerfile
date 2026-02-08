FROM python:3.13-slim

# RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY shared/ shared/
COPY ingestors/common ingestors/common/
COPY ingestors/file ingestors/file/

RUN pip install --no-cache-dir uv && uv sync --package file

WORKDIR /app/ingestors/file
CMD ["uv", "run", "python", "main.py"]
