#!/bin/bash
set -e

echo "🎯 Query MCP - Complete Setup & Run"
echo ""

cd "$(dirname "$0")/.."

# Step 1: Setup
if [ ! -d "venv" ]; then
    echo "📦 Step 1: Setting up virtual environment..."
    bash scripts/setup.sh
    echo ""
fi

# Activate venv
source venv/bin/activate

# Step 2: Migrate
echo "🗄️  Step 2: Running database migrations..."
bash scripts/migrate.sh
echo ""

# Step 3: Run
PORT=${1:-8001}
echo "🚀 Step 3: Starting server..."
bash scripts/run.sh $PORT
