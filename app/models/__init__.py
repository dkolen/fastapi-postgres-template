"""SQLAlchemy models.

Every module in this package is imported automatically so `Base.metadata`
sees all tables (Alembic autogenerate relies on this).
"""

import importlib
import pkgutil

from app.models.base import Base, TimestampMixin

for _module_info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
    importlib.import_module(f"{__name__}.{_module_info.name}")

__all__ = ["Base", "TimestampMixin"]
