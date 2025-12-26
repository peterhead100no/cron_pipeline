# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application files
COPY . .

# Create directories for audio files and transcripts
RUN mkdir -p AUDIO_RECORDING AUDIO_TO_TEXT

# Expose port for FastAPI server
EXPOSE 8502

# Default command - run FastAPI cron API server
CMD ["uvicorn", "cron_api:app", "--host", "0.0.0.0", "--port", "8502"]
