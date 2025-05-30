from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine
import pgvector.sqlalchemy # Import for Vector type autogenerate support

from backend.db import Base  # Import Base from db package's __init__.py
from backend.config import settings      # Import your settings
from backend.db.session import async_engine # Import your async_engine

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# Import Vector for render_item type check, if not already globally available
# from pgvector.sqlalchemy import Vector # Already imported at the top

def render_item(type_, obj, autogen_context):
    """Render an item for autogenerate to handle pgvector.Vector."""
    if type_ == 'type' and hasattr(obj, '__module__') and obj.__module__ == 'pgvector.sqlalchemy' and obj.__class__.__name__ == 'Vector':
        # Ensure Vector is imported in the generated migration script
        autogen_context.imports.add("from pgvector.sqlalchemy import Vector")
        if obj.dimensions:
            return f"Vector({obj.dimensions})"
        else:
            return "Vector()" # Assumes Vector() is valid if no dimensions specified
    return False # Let Alembic handle other types by default

target_metadata = Base.metadata  # Point to your models' metadata
print(f"DEBUG: env.py - target_metadata.tables before autogen: {list(target_metadata.tables.keys())}") # Diagnostic print

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = config.get_main_option("sqlalchemy.url")
    # Use the DATABASE_URL from your project settings
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in the environment settings.")
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_item=render_item
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_item=render_item
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    #     url=settings.DATABASE_URL  # Ensure it uses the correct URL if not using async_engine directly
    # )

    # Use the existing async_engine from the application
    if async_engine is None:
        raise Exception("async_engine is not initialized. Check db.session.py and DATABASE_URL.")

    async with async_engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await async_engine.dispose()


import asyncio

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
