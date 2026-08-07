# Use Python 3.11 slim image
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/app/third_party/am-platform-security

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY third_party/am-platform-security/ third_party/am-platform-security/
RUN pip install --no-cache-dir ./third_party/am-platform-security

COPY . .

RUN mkdir -p user_tokens && chown -R 1000:1000 /app

USER 1000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/api/v1/health')"

CMD ["python", "app_api.py"]
