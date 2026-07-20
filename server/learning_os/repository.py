"""PostgreSQL-backed persistence for the Learning OS.

Uses SQLAlchemy 2.0 Core with the psycopg 3 driver. Domain objects are stored as
JSONB so the schema stays flexible; the public repository methods return plain
dict/list structures that the service layer maps onto its Pydantic models.

This module is the only place that knows about the database. Swapping engines
means changing the URL/dialect here without touching the service or API layers.

Configuration (env):
    DATABASE_URL  e.g. postgresql+psycopg://user:pass@host:5432/learning_os
    (or the individual POSTGRES_* vars below)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    Index,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert
from sqlalchemy.engine import Engine

from ..base.logger import setup_logger

logger = setup_logger(__name__)


def resolve_database_url(database_url: Optional[str] = None) -> str:
    """Resolve a SQLAlchemy Postgres URL from env or explicit argument.

    Accepts a full ``DATABASE_URL`` or assembles one from ``POSTGRES_*`` vars.
    Normalises the ``postgresql://`` scheme to the psycopg 3 driver.
    """
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "learning_os")
        url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    # Normalise legacy/psycopg2 schemes onto psycopg 3.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


metadata = MetaData()

_ENTITY_TABLES: Dict[str, Table] = {
    "profiles": Table(
        "profiles",
        metadata,
        Column("id", String, primary_key=True),
        Column("user_id", String, nullable=False, index=True),
        Column("profile_id", String, nullable=True),
        Column("data", JSONB, nullable=False),
    ),
    "workspaces": Table(
        "workspaces",
        metadata,
        Column("id", String, primary_key=True),
        Column("user_id", String, nullable=False, index=True),
        Column("profile_id", String, nullable=True),
        Column("data", JSONB, nullable=False),
    ),
    "documents": Table(
        "documents",
        metadata,
        Column("id", String, primary_key=True),
        Column("user_id", String, nullable=False),
        Column("profile_id", String, nullable=False),
        Column("data", JSONB, nullable=False),
    ),
}

Index("idx_documents_profile", _ENTITY_TABLES["documents"].c.profile_id,
      _ENTITY_TABLES["documents"].c.user_id)

collections_table = Table(
    "collections",
    metadata,
    Column("kind", String, primary_key=True),
    Column("profile_id", String, primary_key=True),
    Column("data", JSONB, nullable=False),
)


class LearningRepository:
    """Durable per-entity store for profile-isolated learning data (PostgreSQL).

    Each entity type has its own table with an ``id`` primary key and a JSONB
    ``data`` column. Ownership/scoping columns (``user_id``/``profile_id``) are
    promoted out of the JSON so queries can filter without deserializing rows.
    """

    def __init__(self, database_url: Optional[str] = None, engine: Optional[Engine] = None) -> None:
        if engine is not None:
            self._engine = engine
        else:
            url = resolve_database_url(database_url)
            # pool_pre_ping recycles connections dropped by the server/network.
            self._engine = create_engine(url, pool_pre_ping=True, future=True)
        metadata.create_all(self._engine)
        logger.info("Learning repository ready (postgres, dialect=%s)", self._engine.dialect.name)

    # ------------------------------------------------------------------ entities

    def upsert_entity(
        self,
        table: str,
        entity_id: str,
        data: Dict[str, Any],
        *,
        user_id: str,
        profile_id: Optional[str] = None,
    ) -> None:
        tbl = _ENTITY_TABLES[table]
        values = {"id": entity_id, "user_id": user_id, "profile_id": profile_id, "data": data}
        stmt = pg_insert(tbl).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[tbl.c.id],
            set_={"user_id": user_id, "profile_id": profile_id, "data": data},
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)

    def get_entity(self, table: str, entity_id: str) -> Optional[Dict[str, Any]]:
        tbl = _ENTITY_TABLES[table]
        with self._engine.connect() as conn:
            row = conn.execute(select(tbl.c.data).where(tbl.c.id == entity_id)).fetchone()
        return dict(row[0]) if row else None

    def list_by_user(self, table: str, user_id: str) -> List[Dict[str, Any]]:
        tbl = _ENTITY_TABLES[table]
        with self._engine.connect() as conn:
            rows = conn.execute(select(tbl.c.data).where(tbl.c.user_id == user_id)).fetchall()
        return [dict(row[0]) for row in rows]

    def list_documents(self, profile_id: str, user_id: str) -> List[Dict[str, Any]]:
        tbl = _ENTITY_TABLES["documents"]
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(tbl.c.data).where(
                    tbl.c.profile_id == profile_id, tbl.c.user_id == user_id
                )
            ).fetchall()
        return [dict(row[0]) for row in rows]

    def get_documents_by_profile(self, profile_id: str) -> List[Dict[str, Any]]:
        """List documents for a profile regardless of owner (internal use only)."""
        tbl = _ENTITY_TABLES["documents"]
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(tbl.c.data).where(tbl.c.profile_id == profile_id)
            ).fetchall()
        return [dict(row[0]) for row in rows]

    def delete_collection(self, kind: str, profile_id: str) -> None:
        from sqlalchemy import delete as sa_delete

        with self._engine.begin() as conn:
            conn.execute(
                sa_delete(collections_table).where(
                    collections_table.c.kind == kind,
                    collections_table.c.profile_id == profile_id,
                )
            )

    def delete_entity(self, table: str, entity_id: str) -> None:
        from sqlalchemy import delete as sa_delete

        tbl = _ENTITY_TABLES[table]
        with self._engine.begin() as conn:
            conn.execute(sa_delete(tbl).where(tbl.c.id == entity_id))

    def delete_profile_cascade(self, profile_id: str) -> None:
        """Remove a profile and everything scoped to it, in one transaction."""
        from sqlalchemy import delete as sa_delete

        documents = _ENTITY_TABLES["documents"]
        workspaces = _ENTITY_TABLES["workspaces"]
        profiles = _ENTITY_TABLES["profiles"]
        with self._engine.begin() as conn:
            conn.execute(sa_delete(documents).where(documents.c.profile_id == profile_id))
            conn.execute(sa_delete(workspaces).where(workspaces.c.profile_id == profile_id))
            conn.execute(
                sa_delete(collections_table).where(collections_table.c.profile_id == profile_id)
            )
            conn.execute(sa_delete(profiles).where(profiles.c.id == profile_id))

    # --------------------------------------------------------------- collections

    def get_collection(self, kind: str, profile_id: str) -> List[Dict[str, Any]]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(collections_table.c.data).where(
                    collections_table.c.kind == kind,
                    collections_table.c.profile_id == profile_id,
                )
            ).fetchone()
        return list(row[0]) if row else []

    def set_collection(self, kind: str, profile_id: str, items: List[Dict[str, Any]]) -> None:
        stmt = pg_insert(collections_table).values(kind=kind, profile_id=profile_id, data=items)
        stmt = stmt.on_conflict_do_update(
            index_elements=[collections_table.c.kind, collections_table.c.profile_id],
            set_={"data": items},
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)

    def has_profiles(self, user_id: str) -> bool:
        tbl = _ENTITY_TABLES["profiles"]
        with self._engine.connect() as conn:
            row = conn.execute(
                select(tbl.c.id).where(tbl.c.user_id == user_id).limit(1)
            ).fetchone()
        return row is not None

    def ping(self) -> bool:
        """Return True if the database is reachable."""
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as error:  # pragma: no cover - network dependent
            logger.warning("Database ping failed: %s", error)
            return False

    def close(self) -> None:
        self._engine.dispose()
