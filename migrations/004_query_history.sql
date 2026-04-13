-- Migration: 004_query_history
-- Description: Store user queries, generated SQL, and execution results

CREATE TABLE IF NOT EXISTS query_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64),
    user_message TEXT NOT NULL,
    table_name VARCHAR(255),
    generated_sql TEXT,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    row_count INTEGER DEFAULT 0,
    error TEXT,
    llm_provider VARCHAR(50),
    llm_model VARCHAR(100),
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_history_session ON query_history(session_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created ON query_history(created_at);
CREATE INDEX IF NOT EXISTS idx_query_history_table ON query_history(table_name);
CREATE INDEX IF NOT EXISTS idx_query_history_success ON query_history(success);
CREATE INDEX IF NOT EXISTS idx_query_sessions_session_id ON query_sessions(session_id);
