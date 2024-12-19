FROM python:3.10-slim

WORKDIR /app

# Install dependencies and create necessary directories
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    mkdir -p /tmp && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy model directory
COPY model /app/model

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PYTHONPATH=/app

# Expose application port
EXPOSE 8080

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl --fail http://localhost:$PORT/health || exit 1

# Command to run the application
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
