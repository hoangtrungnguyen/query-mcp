"""expand_query_sessions_for_conversation

Add columns to query_sessions so it stores the full conversation:
  - title: auto-generated from first user message
  - table_name: the table being queried in this session
  - messages: JSONB array of {role, content, sql, answer, row_count, error, timestamp}
  - context: JSONB for stored context (schema snapshot, preferences, etc.)
  - updated_at: last activity timestamp

Revision ID: 70b3e4cf007b
Revises: 8f9881ec5d77
Create Date: 2026-04-18 16:53:29.796051
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = '70b3e4cf007b'
down_revision: Union[str, Sequence[str], None] = '8f9881ec5d77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint on session_id for upsert support
    op.drop_index('idx_query_sessions_session_id', table_name='query_sessions')
    op.create_unique_constraint('uq_query_sessions_session_id', 'query_sessions', ['session_id'])

    op.add_column('query_sessions', sa.Column('title', sa.VARCHAR(255), nullable=True))
    op.add_column('query_sessions', sa.Column('table_name', sa.VARCHAR(255), nullable=True))
    op.add_column('query_sessions', sa.Column('messages', JSONB(), nullable=True, server_default='[]'))
    op.add_column('query_sessions', sa.Column('context', JSONB(), nullable=True, server_default='{}'))
    op.add_column('query_sessions', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True,
                                              server_default=sa.text('CURRENT_TIMESTAMP')))


def downgrade() -> None:
    op.drop_column('query_sessions', 'updated_at')
    op.drop_column('query_sessions', 'context')
    op.drop_column('query_sessions', 'messages')
    op.drop_column('query_sessions', 'table_name')
    op.drop_column('query_sessions', 'title')

    op.drop_constraint('uq_query_sessions_session_id', 'query_sessions', type_='unique')
    op.create_index('idx_query_sessions_session_id', 'query_sessions', ['session_id'])
