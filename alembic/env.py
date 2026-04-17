import json
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import pool
from sqlalchemy.engine import URL

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _get_db_url() -> URL:
    config_file = Path.home() / ".query-mcp" / "config.json"
    if config_file.exists():
        with open(config_file) as f:
            db = json.load(f).get("database", {})
    else:
        db = {}
    return URL.create(
        drivername="postgresql+psycopg2",
        username=db.get("user", "postgres"),
        password=db.get("password", "postgres"),
        host=db.get("host", "localhost"),
        port=int(db.get("port", 5432)),
        database=db.get("name", "postgres"),
    )


def run_migrations_offline() -> None:
    url = _get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_get_db_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
