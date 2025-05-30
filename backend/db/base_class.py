# backend/db/base_class.py
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData

# Define naming conventions for constraints. This helps in generating
# consistent and predictable names for indexes, unique constraints, etc.,
# which is particularly useful for Alembic migrations.
# See: https://alembic.sqlalchemy.org/en/latest/naming.html
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)

# Declarative base class
Base = declarative_base(metadata=metadata)
