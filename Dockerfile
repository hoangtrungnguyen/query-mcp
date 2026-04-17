# Multi-stage build for Cloud Run deployment
FROM python:3.11-slim as builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy only necessary system tools from builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application files
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Set Python path for user-installed packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cloud Run port (default 8080)
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check - removed for Cloud Run (uses liveness probes)
# Cloud Run manages health checks automatically

# Run server with HTTP transport on Cloud Run port
# Defaults to PORT=8080 env var, or can be overridden
CMD ["sh", "-c", "python -u src/server.py http ${PORT:-8080}"]
