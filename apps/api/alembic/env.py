from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://tutorial:tutorial@localhost:5433/tutorial")
    # Alembic runs sync; swap async driver to sync if needed.
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg")
    return url


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section)
    if section is None:
        raise RuntimeError("Alembic configuration section is missing.")

    connectable = engine_from_config(section, url=get_url(), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_server_default=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
