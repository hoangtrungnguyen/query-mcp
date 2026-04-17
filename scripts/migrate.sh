#!/bin/bash
set -e

echo "🗄️  Running database migrations..."

cd "$(dirname "$0")/.."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if database is accessible
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

# Run migrations
echo "🚀 Upgrading schema..."
alembic upgrade head

echo "✅ Migrations complete!"
echo ""
echo "Verify with:"
echo "  PGPASSWORD=postgres psql -h localhost -U postgres -d postgres -c \"\\dt\""
