FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/server.py .
COPY src/text_to_sql.py .

# Create config directory
RUN mkdir -p /root/.query-mcp

# Environment variables
ENV QUERY_MCP_API_KEY=${QUERY_MCP_API_KEY}
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the server
CMD ["python", "-u", "server.py"]
