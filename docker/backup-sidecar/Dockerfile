FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scripts/backup /app/scripts/backup
COPY src/durability /app/src/durability
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command: run backup scheduler
CMD ["python", "-m", "scripts.backup.backup_scheduler"]
