#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Query MCP — API Test Script
#
# Usage:
#   ./scripts/test-api.sh              # default: http://localhost:8001
#   ./scripts/test-api.sh 8080         # custom port
#   BASE_URL=https://my.server ./scripts/test-api.sh  # custom URL
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

PORT=${1:-8001}
BASE=${BASE_URL:-"http://localhost:$PORT"}
SESSION="test-$(date +%s)"
PASS=0
FAIL=0
TOTAL=0

# ── Helpers ──────────────────────────────────────────────────────

green()  { printf "\033[32m%s\033[0m\n" "$1"; }
red()    { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }
bold()   { printf "\033[1m%s\033[0m\n" "$1"; }

check() {
    local name="$1" response="$2" expected="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$response" | grep -q "$expected"; then
        green "  ✓ $name"
        PASS=$((PASS + 1))
    else
        red "  ✗ $name"
        echo "    Expected: $expected"
        echo "    Response: $(echo "$response" | head -3)"
        FAIL=$((FAIL + 1))
    fi
}

post() {
    curl -s -X POST "$BASE$1" -H 'Content-Type: application/json' -d "$2"
}

get() {
    curl -s "$BASE$1"
}

# ── 1. Health Check ──────────────────────────────────────────────

bold "── Health Check ──"

R=$(get "/health")
check "GET /health" "$R" '"status":"ok"'

R=$(get "/api/health")
check "GET /api/health" "$R" '"status":"ok"'

# ── 2. Tables ────────────────────────────────────────────────────

bold "── Tables ──"

R=$(get "/api/tables")
check "GET /api/tables — list" "$R" '"name"'

# Get first table id for later use
TABLE_ID=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "")
TABLE_NAME=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['name'])" 2>/dev/null || echo "medicine_bid")

if [ -n "$TABLE_ID" ]; then
    R=$(get "/api/tables/$TABLE_ID")
    check "GET /api/tables/{id} — detail" "$R" "$TABLE_NAME"

    R=$(get "/api/tables/$TABLE_ID/schema")
    check "GET /api/tables/{id}/schema — columns" "$R" '"columns"'

    R=$(get "/api/tables/$TABLE_ID/data?limit=5")
    check "GET /api/tables/{id}/data — paginated" "$R" '"rows"'

    R=$(get "/api/tables/$TABLE_ID/stats")
    check "GET /api/tables/{id}/stats — statistics" "$R" '"totalRows"'
else
    yellow "  ⚠ Skipping table detail tests (no tables found)"
fi

# ── 3. SQL Generation (no execution) ────────────────────────────

bold "── POST /api/sql — Generate SQL only ──"

R=$(post "/api/sql" "{\"user_message\":\"Show all records\",\"table_name\":\"$TABLE_NAME\"}")
check "Generate SQL" "$R" '"sql"'

R=$(post "/api/sql" "{\"user_message\":\"Show top 3 by price\",\"table_name\":\"$TABLE_NAME\",\"session_id\":\"$SESSION\"}")
check "Generate SQL with session_id" "$R" '"sql"'

R=$(post "/api/sql" "{\"user_message\":\"bad\"}")
check "Generate SQL — missing table_name → 400" "$R" '"error"'

# ── 4. Execute raw SQL ──────────────────────────────────────────

bold "── POST /api/execute — Execute raw SQL ──"

R=$(post "/api/execute" "{\"sql_query\":\"SELECT 1 AS test_col\"}")
check "Execute SELECT 1" "$R" '"success":true'

R=$(post "/api/execute" "{\"sql_query\":\"SELECT COUNT(*) FROM $TABLE_NAME\"}")
check "Execute COUNT(*)" "$R" '"success":true'

R=$(post "/api/execute" "{}")
check "Execute — missing sql_query → 400" "$R" '"error"'

# ── 5. Generate + Execute ───────────────────────────────────────

bold "── POST /api/query — Generate + Execute ──"

R=$(post "/api/query" "{\"user_message\":\"Count all records\",\"table_name\":\"$TABLE_NAME\",\"session_id\":\"$SESSION\"}")
check "Generate + execute" "$R" '"sql"'

R=$(post "/api/query" "{\"user_message\":\"Show me those grouped by category\",\"table_name\":\"$TABLE_NAME\",\"session_id\":\"$SESSION\"}")
check "Generate + execute with context (follow-up)" "$R" '"sql"'

# ── 6. Ask (full pipeline) ──────────────────────────────────────

bold "── POST /api/ask — Full pipeline ──"

R=$(post "/api/ask" "{\"user_message\":\"How many drugs are there?\",\"table_name\":\"$TABLE_NAME\",\"session_id\":\"$SESSION\"}")
check "Ask — returns answer" "$R" '"answer"'

R=$(post "/api/ask" "{\"user_message\":\"What about by category?\",\"table_name\":\"$TABLE_NAME\",\"session_id\":\"$SESSION\"}")
check "Ask — follow-up with context" "$R" '"answer"'

R=$(post "/api/ask" "{\"user_message\":\"Show the cheapest ones\",\"table_name\":\"$TABLE_NAME\",\"session_id\":\"$SESSION\",\"lang\":\"vi\"}")
check "Ask — with lang=vi" "$R" '"answer"'

R=$(post "/api/ask" "{\"user_message\":\"test\"}")
check "Ask — missing table_name → 400" "$R" '"error"'

# ── 7. Query History ────────────────────────────────────────────

bold "── GET /api/query/history ──"

R=$(get "/api/query/history?limit=5")
check "History — all sessions" "$R" '"conversations"'

R=$(get "/api/query/history?conversationId=$SESSION&limit=10")
check "History — filtered by session_id" "$R" '"conversations"'

# ── 8. Conversation in query_sessions ───────────────────────────

bold "── Conversation stored in query_sessions ──"

R=$(post "/api/execute" "{\"sql_query\":\"SELECT session_id, title, table_name, jsonb_array_length(messages) as msg_count FROM query_sessions WHERE session_id = '$SESSION'\"}")
check "Session exists in query_sessions" "$R" "$SESSION"

MSG_COUNT=$(echo "$R" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['results'][0]['msg_count'] if r.get('results') else 0)" 2>/dev/null || echo "0")
if [ "$MSG_COUNT" -gt 0 ]; then
    green "  ✓ Session has $MSG_COUNT messages stored"
    PASS=$((PASS + 1))
else
    red "  ✗ Session has no messages"
    FAIL=$((FAIL + 1))
fi
TOTAL=$((TOTAL + 1))

# ── Summary ─────────────────────────────────────────────────────

echo ""
bold "══════════════════════════════════════"
if [ $FAIL -eq 0 ]; then
    green "  ALL $TOTAL TESTS PASSED ✓"
else
    yellow "  $PASS/$TOTAL passed, $FAIL failed"
fi
bold "══════════════════════════════════════"

exit $FAIL
