FROM python:3.11-slim

WORKDIR /app

LABEL org.opencontainers.image.title="route53-updater"
LABEL org.opencontainers.image.description="Dynamic DNS updater for AWS Route 53"
LABEL org.opencontainers.image.version="1.0.0"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python", "app.py"]
