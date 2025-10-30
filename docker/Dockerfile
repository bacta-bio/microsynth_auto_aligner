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

# Copy the new project structure
COPY src/ ./src/
COPY benchling/ ./benchling/
COPY templates/ ./templates/
COPY static/ ./static/
COPY docker/gunicorn.conf.py ./gunicorn.conf.py

# Create upload directory with proper permissions
RUN mkdir -p /tmp/uploads && chmod 777 /tmp/uploads

EXPOSE 8080

# Run the Flask app with Gunicorn using config file (env-overridable)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "src.app:app"]


