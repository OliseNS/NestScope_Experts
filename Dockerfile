# NestScope — API (FastAPI) + Nestperts (Flask)
# Build: docker compose build
# Run:  docker compose up -d

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# System libraries for OpenCV, scientific stack, and common wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/labeller/projects /app/logs /app/models \
    && useradd --create-home --uid 1000 nestscope \
    && chown -R nestscope:nestscope /app

USER nestscope

EXPOSE 8000 5000

# Compose sets the command per service; this is a harmless default.
CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
