#!/bin/bash
set -e

echo "🚀 Starting Query MCP Server..."

cd "$(dirname "$0")/.."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Activate venv
source venv/bin/activate

# Get port from argument or use default
PORT=${1:-8001}

echo "🌐 Server starting on http://localhost:$PORT"
echo ""
echo "Available endpoints:"
echo "  POST http://localhost:$PORT/api/ask      - Natural language → answer"
echo "  POST http://localhost:$PORT/api/query    - Natural language → SQL + results"
echo "  POST http://localhost:$PORT/api/sql      - Natural language → SQL only"
echo "  POST http://localhost:$PORT/api/execute  - Execute raw SQL"
echo "  GET  http://localhost:$PORT/api/tables   - List tables"
echo "  GET  http://localhost:$PORT/health       - Health check"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Set API key if provided
if [ -z "$QUERY_MCP_API_KEY" ]; then
    echo "⚠️  Warning: QUERY_MCP_API_KEY not set"
    echo "   Set it with: export QUERY_MCP_API_KEY='your-key'"
fi

python src/server.py http $PORT
