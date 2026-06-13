FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev \
    libproj-dev \
    proj-data \
    gdal-bin \
    libgdal-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
