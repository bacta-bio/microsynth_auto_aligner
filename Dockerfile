FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps for building Python packages that require compilation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        tk \
        libbz2-dev \
        liblzma-dev \
        libz-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY microsynth_auto_aligner.py .

ENTRYPOINT ["python", "microsynth_auto_aligner.py"]
