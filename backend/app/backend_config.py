"""Backend storage configuration - select between JSON and database backends."""

import os
from enum import Enum


class BackendType(Enum):
    """Available storage backends."""
    JSON = "json"  # File-based (document_registry.json, conversations/*.json)
    DATABASE = "database"  # SQLAlchemy database (SQLite/PostgreSQL/MySQL)


BACKEND = BackendType(os.getenv("STORAGE_BACKEND", "database").lower())
"""
Storage backend selection via STORAGE_BACKEND environment variable.
Default: "database" (SQLite via SQLAlchemy)
Options: "database", "json"

Set to "json" to use legacy file-based storage for backward compatibility.
Database backend is recommended for production and multi-worker deployments.
"""


def is_database_backend() -> bool:
    """Check if using database backend."""
    return BACKEND == BackendType.DATABASE


def is_json_backend() -> bool:
    """Check if using JSON file-based backend."""
    return BACKEND == BackendType.JSON
