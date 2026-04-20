# Conversation Context API

All query endpoints now support **multi-turn conversations** via a `session_id` parameter. When provided, the backend persists each Q&A turn and injects prior conversation history into the LLM prompt, enabling follow-up queries like _"show me more"_, _"filter those by status"_, etc.

---

## What Changed

| Endpoint | Change |
|---|---|
| `POST /api/ask` | New optional field `session_id` |
| `POST /api/query` | New optional field `session_id` |
| `POST /api/sql` | New optional field `session_id` |
| `GET /api/query/history` | New query param `conversationId` to filter by session |

No breaking changes. All endpoints remain backward-compatible — omitting `session_id` works exactly as before (stateless, single-turn).

---

## How It Works

```
1. FE generates a session_id (UUID) when user starts a new conversation
2. FE passes session_id on every request in that conversation
3. BE auto-creates session on first message (upsert)
4. BE appends each user+assistant turn to session's messages array
5. On subsequent requests, BE loads conversation history and injects it into LLM prompt
6. LLM can resolve references like "those", "the same", "more", "also", etc.
```

---

## Request Changes

### `POST /api/ask`

Full pipeline: generate SQL → execute → summarize results.

```jsonc
// Request body
{
  "user_message": "What are the top 5 most expensive drugs?",  // required
  "table_name": "medicine_bid",                                 // required
  "limit": 100,                // optional, default 100
  "llm_provider": "gemini",    // optional, default from config
  "lang": "vi",                // optional, auto-detect if omitted
  "session_id": "uuid-here"    // NEW — optional, enables conversation context
}
```

```jsonc
// Response (unchanged shape — new fields only appear when relevant)
{
  "success": true,
  "sql": "SELECT ... LIMIT 5",
  "results": [ { ... }, ... ],
  "row_count": 5,
  "answer": "The top 5 most expensive drugs are...",
  "needs_clarification": false,
  "clarification": null,
  "error": null
}
```

### `POST /api/query`

Generate SQL + execute (no summarization).

```jsonc
// Request body
{
  "user_message": "Show me more details about those",  // resolves from session context
  "table_name": "medicine_bid",
  "limit": 100,
  "llm_provider": "gemini",
  "session_id": "uuid-here"    // NEW
}
```

```jsonc
// Response
{
  "success": true,
  "sql": "SELECT ...",
  "results": [ ... ],
  "row_count": 10,
  "error": null,
  "needs_clarification": false,
  "clarification": null
}
```

### `POST /api/sql`

Generate SQL only (no execution).

```jsonc
// Request body
{
  "user_message": "Now filter by active status",
  "table_name": "medicine_bid",
  "lang": "en",
  "session_id": "uuid-here"    // NEW
}
```

```jsonc
// Response
{
  "success": true,
  "sql": "SELECT ... WHERE status = 'active'",
  "error": null,
  "needs_clarification": false,
  "clarification": null
}
```

### `GET /api/query/history`

Retrieve query history, optionally filtered by conversation.

| Query Param | Type | Required | Description |
|---|---|---|---|
| `conversationId` | `string` | No | Filter history to a specific session (NEW) |
| `limit` | `number` | No | Max records to return (default: 50) |

```jsonc
// Response
{
  "conversations": [
    {
      "id": 42,
      "session_id": "uuid-here",
      "user_message": "...",
      "table_name": "medicine_bid",
      "generated_sql": "SELECT ...",
      "success": true,
      "row_count": 5,
      "error": null,
      "llm_provider": "gemini",
      "llm_model": "gemini-2.5-flash",
      "execution_time_ms": 230,
      "created_at": "2026-04-18T17:00:00"
    }
  ],
  "count": 1
}
```

---

## Session Data Model

The `query_sessions` table stores conversation state:

| Column | Type | Description |
|---|---|---|
| `session_id` | `VARCHAR` (unique) | Client-generated UUID |
| `title` | `VARCHAR(255)` | Auto-set from first user message (truncated to 100 chars) |
| `table_name` | `VARCHAR(255)` | The table being queried in this session |
| `messages` | `JSONB` | Array of conversation turns (see below) |
| `context` | `JSONB` | Reserved for future use (schema snapshots, preferences) |
| `updated_at` | `TIMESTAMP` | Last activity time |

### Messages Array Structure

Each API call with a `session_id` appends two entries to the `messages` array:

```jsonc
[
  {
    "role": "user",
    "content": "What are the top 5 drugs?",
    "timestamp": "2026-04-18T10:00:00.000000"
  },
  {
    "role": "assistant",
    "sql": "SELECT * FROM medicine_bid ORDER BY price DESC LIMIT 5",
    "answer": "The top 5 most expensive drugs are...",  // null if not using /api/ask
    "row_count": 5,
    "success": true,
    "error": null,
    "timestamp": "2026-04-18T10:00:00.000000"
  }
]
```

---

## Frontend Integration Guide

### 1. Generate Session ID

Create a new UUID when the user starts a conversation. Reuse it for all follow-up messages in that conversation.

```typescript
const sessionId = crypto.randomUUID();
```

### 2. Pass session_id on Every Request

```typescript
const response = await fetch('/api/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_message: userInput,
    table_name: selectedTable,
    session_id: sessionId,  // same ID for all turns
  }),
});
```

### 3. New Conversation = New session_id

When the user clicks "New Chat" or switches context, generate a fresh UUID.

### 4. Load History for a Session

```typescript
const history = await fetch(`/api/query/history?conversationId=${sessionId}`);
```

### 5. Clarification Handling (unchanged)

When `needs_clarification` is `true`, display `clarification` to the user and let them rephrase. The session context is still preserved — their next message will include prior turns.

---

## Behavior Notes

- **Context window**: Backend keeps the last 20 messages in the LLM prompt to avoid token overflow.
- **Upsert**: First request with a new `session_id` creates the session. No separate "create session" call needed.
- **Title**: Auto-generated from the first user message (first 100 chars). Not editable via API currently.
- **Stateless fallback**: Omitting `session_id` = single-turn query, no history stored in `query_sessions` (still logged in `query_history`).
- **Error isolation**: Session persistence failures never block the main query response.
