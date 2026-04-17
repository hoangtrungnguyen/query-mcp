#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PORT=${1:-8001}

echo "╔════════════════════════════════════════════════════════╗"
echo "║          Query MCP - Local Development Setup           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Setup Virtual Environment
echo "📦 Step 1: Setting up Python environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
echo "   ✓ Virtual environment ready"
echo ""

# Step 2: Install Dependencies
echo "📥 Step 2: Installing dependencies..."
pip install -q -r "$PROJECT_DIR/requirements.txt" 2>/dev/null || pip install -r "$PROJECT_DIR/requirements.txt"
echo "   ✓ Dependencies installed"
echo ""

# Step 3: Check Database Connection
echo "📡 Step 3: Checking database..."
if ! PGPASSWORD=postgres psql -h localhost -U postgres -d postgres -c "SELECT 1" &>/dev/null; then
    echo "   ❌ ERROR: Cannot connect to PostgreSQL"
    echo ""
    echo "   Make sure PostgreSQL is running with:"
    echo "     - Host: localhost"
    echo "     - Port: 5432"
    echo "     - User: postgres"
    echo "     - Password: postgres"
    echo ""
    echo "   Start PostgreSQL with: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15"
    exit 1
fi
echo "   ✓ Database connection OK"
echo ""

# Step 4: Run Migrations
echo "🗄️  Step 4: Running database migrations..."
cd "$PROJECT_DIR"
alembic upgrade head 2>&1 | grep -E "Running|Upgrading|Alembic" || echo "   ✓ Migrations applied"
echo ""

# Step 5: Check API Key
echo "🔑 Step 5: Checking API configuration..."
if [ -z "$QUERY_MCP_API_KEY" ]; then
    echo "   ⚠️  Warning: QUERY_MCP_API_KEY not set"
    echo "   Set it with: export QUERY_MCP_API_KEY='your-api-key'"
    echo ""
else
    echo "   ✓ API key configured"
fi
echo ""

# Step 6: Start Server
echo "╔════════════════════════════════════════════════════════╗"
echo "║            🚀 Starting Server on Port $PORT             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Available endpoints:"
echo "  POST http://localhost:$PORT/api/ask      - Natural language → answer"
echo "  POST http://localhost:$PORT/api/query    - Natural language → SQL + results"
echo "  POST http://localhost:$PORT/api/sql      - Natural language → SQL only"
echo "  POST http://localhost:$PORT/api/execute  - Execute raw SQL"
echo "  GET  http://localhost:$PORT/api/tables   - List tables"
echo "  GET  http://localhost:$PORT/health       - Health check"
echo ""
echo "Example:"
echo "  curl -X POST http://localhost:$PORT/api/ask \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"user_message\": \"Show top 5 medicines\", \"table_name\": \"medicine_bid\"}'"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$PROJECT_DIR"
python src/server.py http $PORT
