FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps: build tools and compression libraries for biopython
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Build tools
        build-essential \
        libffi-dev \
        # Compression libraries for biopython
        libbz2-dev liblzma-dev libz-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY microsynth_auto_aligner.py .
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

# Create upload directory with proper permissions
RUN mkdir -p /tmp/uploads && chmod 777 /tmp/uploads

EXPOSE 8080

CMD ["python", "app.py"]
