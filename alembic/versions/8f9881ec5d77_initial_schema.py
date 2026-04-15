"""initial_schema

Revision ID: 8f9881ec5d77
Revises:
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8f9881ec5d77'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RECORD_HASH_EXPR = """
    md5(
        COALESCE(registration_number, '') || '|' ||
        COALESCE(active_ingredient, '')   || '|' ||
        COALESCE(name, '')                || '|' ||
        COALESCE(concentration, '')       || '|' ||
        COALESCE(facility_code, '')       || '|' ||
        COALESCE((contract_start_date - '1970-01-01'::date)::TEXT, '') || '|' ||
        COALESCE((contract_end_date   - '1970-01-01'::date)::TEXT, '')
    )
"""


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    #  medicine_bid                                                        #
    # ------------------------------------------------------------------ #
    op.execute(f"""
        CREATE TABLE medicine_bid (
            id                   SERIAL PRIMARY KEY,
            name                 TEXT         NOT NULL,
            category             TEXT,
            price                NUMERIC(10,2),
            stock                INTEGER,
            manufacturer         TEXT,
            created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            active_ingredient    TEXT,
            registration_number  TEXT,
            route                TEXT,
            concentration        TEXT,
            unit                 TEXT,
            total_amount         NUMERIC(15,2),
            country              TEXT,
            province_code        VARCHAR(10),
            facility_code        VARCHAR(20),
            contract_start_date  DATE,
            contract_end_date    DATE,
            record_hash          TEXT GENERATED ALWAYS AS ({RECORD_HASH_EXPR}) STORED,
            bid_type             VARCHAR(50),
            province_name        VARCHAR(200),
            department_name      VARCHAR(300),
            facility_name        VARCHAR(300),
            drug_code            VARCHAR(50),
            drug_code_gy         VARCHAR(50),
            route_code           VARCHAR(20),
            route_code_gy        VARCHAR(20),
            dosage_form          VARCHAR(200),
            packaging            VARCHAR(300),
            contractor_name      VARCHAR(300),
            decision_number      VARCHAR(100),
            valid_from           TIMESTAMP,
            valid_to             TIMESTAMP,
            bid_package          VARCHAR(20),
            standard             VARCHAR(200),
            drug_type            VARCHAR(100),
            approval_sequence    VARCHAR(50),
            validity             VARCHAR(10),
            published_at         TIMESTAMP,
            bid_form             VARCHAR(20),
            source_created_at    TIMESTAMP
        )
    """)

    op.create_index('idx_medicine_bid_category',            'medicine_bid', ['category'])
    op.create_index('idx_medicine_bid_contract_end_date',   'medicine_bid', ['contract_end_date'])
    op.create_index('idx_medicine_bid_facility_code',       'medicine_bid', ['facility_code'])
    op.create_index('idx_medicine_bid_price',               'medicine_bid', ['price'])
    op.create_index('idx_medicine_bid_province_code',       'medicine_bid', ['province_code'])
    op.create_index('idx_medicine_bid_registration_number', 'medicine_bid', ['registration_number'])
    op.create_index('ix_medicine_bid_record_hash',          'medicine_bid', ['record_hash'], unique=True)

    op.execute("""
        COMMENT ON COLUMN medicine_bid.name                 IS 'Tên thuốc';
        COMMENT ON COLUMN medicine_bid.category             IS 'Nhóm thầu';
        COMMENT ON COLUMN medicine_bid.price                IS 'Giá';
        COMMENT ON COLUMN medicine_bid.stock                IS 'Số lượng';
        COMMENT ON COLUMN medicine_bid.manufacturer         IS 'Nhà SX (nhà sản xuất)';
        COMMENT ON COLUMN medicine_bid.active_ingredient    IS 'Tên hoạt chất';
        COMMENT ON COLUMN medicine_bid.registration_number  IS 'Số DK (số đăng ký)';
        COMMENT ON COLUMN medicine_bid.route                IS 'Đường dùng';
        COMMENT ON COLUMN medicine_bid.concentration        IS 'Hàm lượng';
        COMMENT ON COLUMN medicine_bid.unit                 IS 'ĐVT (đơn vị tính)';
        COMMENT ON COLUMN medicine_bid.total_amount         IS 'Thành tiền';
        COMMENT ON COLUMN medicine_bid.country              IS 'Nước SX (nước sản xuất)';
        COMMENT ON COLUMN medicine_bid.province_code        IS 'Mã tỉnh';
        COMMENT ON COLUMN medicine_bid.facility_code        IS 'Mã CSKCB (cơ sở khám chữa bệnh)';
        COMMENT ON COLUMN medicine_bid.contract_start_date  IS 'Từ ngày HD (hiệu lực hợp đồng)';
        COMMENT ON COLUMN medicine_bid.contract_end_date    IS 'Đến ngày HD (hết hiệu lực hợp đồng)';
        COMMENT ON COLUMN medicine_bid.bid_type             IS 'loai_thau';
        COMMENT ON COLUMN medicine_bid.province_name        IS 'ten_tinh';
        COMMENT ON COLUMN medicine_bid.department_name      IS 'ten_don_vi';
        COMMENT ON COLUMN medicine_bid.facility_name        IS 'ten_cskcb';
        COMMENT ON COLUMN medicine_bid.drug_code            IS 'ma';
        COMMENT ON COLUMN medicine_bid.drug_code_gy         IS 'ma_gy';
        COMMENT ON COLUMN medicine_bid.route_code           IS 'maduongdung';
        COMMENT ON COLUMN medicine_bid.route_code_gy        IS 'madd_gy';
        COMMENT ON COLUMN medicine_bid.dosage_form          IS 'dangbaoche';
        COMMENT ON COLUMN medicine_bid.packaging            IS 'donggoi';
        COMMENT ON COLUMN medicine_bid.contractor_name      IS 'tennhathau';
        COMMENT ON COLUMN medicine_bid.decision_number      IS 'quyetdinh';
        COMMENT ON COLUMN medicine_bid.valid_from           IS 'tungay';
        COMMENT ON COLUMN medicine_bid.valid_to             IS 'denngay';
        COMMENT ON COLUMN medicine_bid.bid_package          IS 'goithau';
        COMMENT ON COLUMN medicine_bid.standard             IS 'tieuchuan';
        COMMENT ON COLUMN medicine_bid.drug_type            IS 'loai';
        COMMENT ON COLUMN medicine_bid.approval_sequence    IS 'sttpheduyet';
        COMMENT ON COLUMN medicine_bid.validity             IS 'hieuluc';
        COMMENT ON COLUMN medicine_bid.published_at         IS 'congbo';
        COMMENT ON COLUMN medicine_bid.bid_form             IS 'ht_thau';
        COMMENT ON COLUMN medicine_bid.source_created_at    IS 'created_date';
    """)

    # ------------------------------------------------------------------ #
    #  items                                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        'items',
        sa.Column('id',         sa.Integer(),     nullable=False),
        sa.Column('name',       sa.VARCHAR(255),  nullable=False),
        sa.Column('category',   sa.VARCHAR(100),  nullable=True),
        sa.Column('price',      sa.NUMERIC(10,2), nullable=True),
        sa.Column('status',     sa.VARCHAR(50),   nullable=True),
        sa.Column('quantity',   sa.Integer(),     nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(),   nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_items_category', 'items', ['category'])
    op.create_index('idx_items_status',   'items', ['status'])

    # ------------------------------------------------------------------ #
    #  users                                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        'users',
        sa.Column('id',         sa.Integer(),     nullable=False),
        sa.Column('name',       sa.VARCHAR(255),  nullable=False),
        sa.Column('email',      sa.VARCHAR(255),  nullable=True),
        sa.Column('status',     sa.VARCHAR(50),   nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(),   nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='users_email_key'),
    )
    op.create_index('idx_users_status', 'users', ['status'])

    # ------------------------------------------------------------------ #
    #  orders                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        'orders',
        sa.Column('id',         sa.Integer(),     nullable=False),
        sa.Column('user_id',    sa.Integer(),     nullable=True),
        sa.Column('total',      sa.NUMERIC(10,2), nullable=True),
        sa.Column('status',     sa.VARCHAR(50),   nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(),   nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='orders_user_id_fkey'),
    )
    op.create_index('idx_orders_status',  'orders', ['status'])
    op.create_index('idx_orders_user_id', 'orders', ['user_id'])

    # ------------------------------------------------------------------ #
    #  query_sessions                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        'query_sessions',
        sa.Column('id',         sa.Integer(),   nullable=False),
        sa.Column('session_id', sa.VARCHAR(64), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_query_sessions_session_id', 'query_sessions', ['session_id'])

    # ------------------------------------------------------------------ #
    #  query_history                                                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        'query_history',
        sa.Column('id',                sa.Integer(),    nullable=False),
        sa.Column('session_id',        sa.VARCHAR(64),  nullable=True),
        sa.Column('user_message',      sa.TEXT(),       nullable=False),
        sa.Column('table_name',        sa.VARCHAR(255), nullable=True),
        sa.Column('generated_sql',     sa.TEXT(),       nullable=True),
        sa.Column('success',           sa.Boolean(),    nullable=False, server_default=sa.text('false')),
        sa.Column('row_count',         sa.Integer(),    nullable=True,  server_default=sa.text('0')),
        sa.Column('error',             sa.TEXT(),       nullable=True),
        sa.Column('llm_provider',      sa.VARCHAR(50),  nullable=True),
        sa.Column('llm_model',         sa.VARCHAR(100), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(),    nullable=True),
        sa.Column('created_at',        sa.TIMESTAMP(),  nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_query_history_created', 'query_history', ['created_at'])
    op.create_index('idx_query_history_session', 'query_history', ['session_id'])
    op.create_index('idx_query_history_success', 'query_history', ['success'])
    op.create_index('idx_query_history_table',   'query_history', ['table_name'])

    # ------------------------------------------------------------------ #
    #  import_log                                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        'import_log',
        sa.Column('id',            sa.Integer(),    nullable=False),
        sa.Column('filename',      sa.VARCHAR(500), nullable=False),
        sa.Column('source',        sa.VARCHAR(100), nullable=False, server_default='med-tech'),
        sa.Column('status',        sa.VARCHAR(20),  nullable=False, server_default='pending'),
        sa.Column('rows_inserted', sa.Integer(),    nullable=False, server_default=sa.text('0')),
        sa.Column('rows_updated',  sa.Integer(),    nullable=False, server_default=sa.text('0')),
        sa.Column('rows_failed',   sa.Integer(),    nullable=False, server_default=sa.text('0')),
        sa.Column('error_message', sa.TEXT(),       nullable=True),
        sa.Column('started_at',    sa.TIMESTAMP(),  nullable=True),
        sa.Column('finished_at',   sa.TIMESTAMP(),  nullable=True),
        sa.Column('created_at',    sa.TIMESTAMP(),  nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('note',          sa.TEXT(),       nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('pending','in_progress','success','failed')",
            name='import_log_status_check',
        ),
    )
    op.create_index('idx_import_log_status',     'import_log', ['status'])
    op.create_index('idx_import_log_created_at', 'import_log', ['created_at'])
    op.create_index('idx_import_log_source',     'import_log', ['source'])

    op.execute("""
        COMMENT ON TABLE  import_log               IS 'Tracks every file upload from the med-tech service';
        COMMENT ON COLUMN import_log.filename      IS 'Original uploaded filename';
        COMMENT ON COLUMN import_log.source        IS 'Originating service (default: med-tech)';
        COMMENT ON COLUMN import_log.status        IS 'pending | in_progress | success | failed';
        COMMENT ON COLUMN import_log.rows_inserted IS 'New rows inserted in this import';
        COMMENT ON COLUMN import_log.rows_updated  IS 'Existing rows updated (upsert) in this import';
        COMMENT ON COLUMN import_log.rows_failed   IS 'Rows that could not be processed';
        COMMENT ON COLUMN import_log.error_message IS 'Error detail when status = failed';
        COMMENT ON COLUMN import_log.started_at    IS 'When processing began';
        COMMENT ON COLUMN import_log.finished_at   IS 'When processing completed or failed';
        COMMENT ON COLUMN import_log.note          IS 'Free-text note from the uploader';
    """)

    # ------------------------------------------------------------------ #
    #  views                                                               #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE VIEW active_drugs AS
        SELECT id, name, category, price, stock
        FROM medicine_bid;

        CREATE VIEW drugs_by_category AS
        SELECT category, count(*) AS drug_count, avg(price) AS avg_price
        FROM medicine_bid
        GROUP BY category;

        CREATE VIEW expensive_items AS
        SELECT name, category, price
        FROM items
        WHERE price > 50
        ORDER BY price DESC;
    """)


def downgrade() -> None:
    op.execute('DROP VIEW IF EXISTS expensive_items')
    op.execute('DROP VIEW IF EXISTS drugs_by_category')
    op.execute('DROP VIEW IF EXISTS active_drugs')
    op.drop_table('import_log')
    op.drop_table('query_history')
    op.drop_table('query_sessions')
    op.drop_table('orders')
    op.drop_table('users')
    op.drop_table('items')
    op.drop_table('medicine_bid')
