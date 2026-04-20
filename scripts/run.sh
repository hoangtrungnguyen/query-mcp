#!/bin/bash
set -e

echo "🎯 Query MCP - Setup, Migrate & Run"
echo ""

cd "$(dirname "$0")/.."

# ── Load .env ────────────────────────────────────────────────────
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# ── Step 1: Virtual environment & dependencies ───────────────────
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# ── Step 2: Database migrations ──────────────────────────────────
echo ""
echo "🗄️  Running database migrations..."

echo "📡 Checking database connection..."
if ! PGPASSWORD=postgres psql -h localhost -U postgres -d postgres -c "SELECT 1" &>/dev/null; then
    echo "❌ Cannot connect to PostgreSQL at localhost:5432"
    echo "   Make sure PostgreSQL is running with:"
    echo "   - Host: localhost"
    echo "   - Port: 5432"
    echo "   - User: postgres"
    echo "   - Password: postgres"
    exit 1
fi
echo "✓ Database connection OK"

echo "🚀 Upgrading schema..."
alembic upgrade head

echo "✅ Migrations complete!"

# ── Step 3: Start server ─────────────────────────────────────────
PORT=${1:-8001}

echo ""
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

if [ -z "$QUERY_MCP_API_KEY" ]; then
    echo "⚠️  Warning: QUERY_MCP_API_KEY not set"
    echo "   Set it in .env or: export QUERY_MCP_API_KEY='your-key'"
fi

python src/server.py http $PORT
