FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends djvulibre-bin 7zip && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY archive ./archive
COPY static ./static
COPY docker-entrypoint.sh ./
ENV TNY_SOURCE=/archive TNY_DATA=/data PYTHONUNBUFFERED=1
EXPOSE 8765
ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
