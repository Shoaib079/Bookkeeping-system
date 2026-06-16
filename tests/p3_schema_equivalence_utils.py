"""P3.4-C — baseline schema equivalence harness (test-only).

Compares schema fingerprints:
  A) ``Base.metadata.create_all`` only (ORM metadata baseline)
  B) ``create_all`` + ``legacy_migrate_schema()`` (pre-P3.9-C archived evolution path)

Future (P3.4-D): A becomes Alembic ``0001 upgrade``; B uses ``tests.legacy_migrate_schema``
for historical equivalence until fully Alembic-only. This module never connects to
``paths.DATABASE_URL`` or production ``erp_data.db``.
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from db import Base

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

# Indexes/constraints migrate_schema adds that autogenerate/create_all miss (pre-0001).
ACCOUNTING_INTEGRITY_UNIQUES: tuple[str, ...] = (
    "uq_eod_date_active",
    "uq_palloc_period",
    "uq_yec_year",
    "uq_esv_active",
    "uq_coa_code_company",
    "uq_products_sku_company",
)

COMPOSITE_MIGRATE_ONLY_INDEXES: tuple[str, ...] = (
    "ix_att_entity",
    "ix_draftatt_draft",
)

COMPANY_ID_INDEX_NAME_FRAGMENT = "_company_id"

PRE_0001_PHASE = "pre-0001-expected-drift"
POST_0001_PHASE = "post-0001-baseline-equivalence"
BASELINE_0001_PATH = (
    Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_baseline.py"
)


def _register_models() -> None:
    import models as _models  # noqa: F401


def _make_in_memory_engine() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
        if engine.dialect.name != "sqlite":
            return
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def _normalize_sql(sql: str | None) -> str | None:
    if not sql:
        return None
    return re.sub(r"\s+", " ", sql.strip())


def extract_sqlite_schema_summary(engine: Engine) -> dict[str, Any]:
    """Normalized SQLite schema fingerprint from ``sqlite_master`` + PRAGMA."""
    with engine.connect() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                    "ORDER BY name"
                )
            )
        ]

        columns: dict[str, list[dict[str, Any]]] = {}
        for table in tables:
            rows = conn.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
            columns[table] = [
                {
                    "name": row[1],
                    "type": (row[2] or "").upper(),
                    "notnull": bool(row[3]),
                    "pk": int(row[5] or 0),
                }
                for row in rows
            ]

        indexes: dict[str, dict[str, Any]] = {}
        for name, tbl, sql in conn.execute(
            text(
                "SELECT name, tbl_name, sql FROM sqlite_master "
                "WHERE type='index' AND name NOT LIKE 'sqlite_autoindex%' "
                "ORDER BY name"
            )
        ):
            sql_norm = _normalize_sql(sql)
            indexes[name] = {
                "table": tbl,
                "unique": bool(sql_norm and "UNIQUE" in sql_norm.upper()),
                "partial": bool(sql_norm and " WHERE " in sql_norm.upper()),
                "sql": sql_norm,
            }

        foreign_keys: dict[str, list[dict[str, Any]]] = {}
        for table in tables:
            fk_rows = conn.execute(
                text(f'PRAGMA foreign_key_list("{table}")')
            ).fetchall()
            if fk_rows:
                foreign_keys[table] = [
                    {
                        "from_column": row[3],
                        "to_table": row[2],
                        "to_column": row[4],
                        "on_update": row[5],
                        "on_delete": row[6],
                    }
                    for row in fk_rows
                ]

    return {
        "tables": tables,
        "columns": columns,
        "indexes": indexes,
        "foreign_keys": foreign_keys,
    }


def build_create_all_schema_summary() -> dict[str, Any]:
    """Schema A — ORM ``create_all`` only (future Alembic 0001 stand-in)."""
    _register_models()
    engine = _make_in_memory_engine()
    try:
        Base.metadata.create_all(bind=engine)
        return extract_sqlite_schema_summary(engine)
    finally:
        engine.dispose()


def build_migrate_evolved_schema_summary() -> dict[str, Any]:
    """Schema B — ``create_all`` + archived ``legacy_migrate_schema()`` (test-only)."""
    from legacy_migrate_schema import legacy_migrate_schema

    _register_models()
    engine = _make_in_memory_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        Base.metadata.create_all(bind=engine)
        with Session() as session:
            legacy_migrate_schema(session)
        return extract_sqlite_schema_summary(engine)
    finally:
        engine.dispose()


def compute_schema_drift(
    create_all_summary: dict[str, Any],
    migrated_summary: dict[str, Any],
) -> dict[str, Any]:
    """Diff normalized summaries; indexes-only-in-migrated is the pre-0001 gap."""
    tables_a = set(create_all_summary["tables"])
    tables_b = set(migrated_summary["tables"])
    idx_a = set(create_all_summary["indexes"])
    idx_b = set(migrated_summary["indexes"])

    only_migrated = sorted(idx_b - idx_a)
    only_create_all = sorted(idx_a - idx_b)

    company_id_only_migrated = [
        n for n in only_migrated if COMPANY_ID_INDEX_NAME_FRAGMENT in n
    ]

    accounting_only_migrated = [
        n for n in only_migrated if n in ACCOUNTING_INTEGRITY_UNIQUES
    ]

    composite_only_migrated = [
        n for n in only_migrated if n in COMPOSITE_MIGRATE_ONLY_INDEXES
    ]

    partial_only_migrated = [
        n
        for n in only_migrated
        if migrated_summary["indexes"][n].get("partial")
    ]

    column_diffs: dict[str, dict[str, Any]] = {}
    for table in sorted(tables_a | tables_b):
        cols_a = {c["name"] for c in create_all_summary["columns"].get(table, [])}
        cols_b = {c["name"] for c in migrated_summary["columns"].get(table, [])}
        if cols_a != cols_b:
            column_diffs[table] = {
                "only_in_create_all": sorted(cols_a - cols_b),
                "only_in_migrated": sorted(cols_b - cols_a),
            }

    return {
        "phase": PRE_0001_PHASE,
        "equivalent": not only_migrated and not only_create_all and not column_diffs,
        "tables_only_in_create_all": sorted(tables_a - tables_b),
        "tables_only_in_migrated": sorted(tables_b - tables_a),
        "indexes_only_in_create_all": only_create_all,
        "indexes_only_in_migrated": only_migrated,
        "indexes_in_both": sorted(idx_a & idx_b),
        "company_id_indexes_only_in_migrated": company_id_only_migrated,
        "accounting_uniques_only_in_migrated": accounting_only_migrated,
        "composite_indexes_only_in_migrated": composite_only_migrated,
        "partial_indexes_only_in_migrated": partial_only_migrated,
        "column_diffs": column_diffs,
        "index_count_create_all": len(idx_a),
        "index_count_migrated": len(idx_b),
    }


def format_pre_0001_drift_report(drift: dict[str, Any]) -> str:
    """Human-readable report; drift before 0001 is expected, not a failure."""
    lines = [
        "P3.4-C baseline equivalence report (pre-0001 expected drift)",
        f"phase: {drift.get('phase')}",
        f"equivalent: {drift.get('equivalent')}",
        f"indexes create_all: {drift.get('index_count_create_all')}",
        f"indexes migrated: {drift.get('index_count_migrated')}",
        f"indexes only in migrated ({len(drift.get('indexes_only_in_migrated', []))}): "
        + ", ".join(drift.get("indexes_only_in_migrated", [])[:12])
        + ("..." if len(drift.get("indexes_only_in_migrated", [])) > 12 else ""),
        f"accounting uniques only in migrated: {drift.get('accounting_uniques_only_in_migrated')}",
        f"company_id indexes only in migrated: {len(drift.get('company_id_indexes_only_in_migrated', []))}",
        f"composite only in migrated: {drift.get('composite_indexes_only_in_migrated')}",
        "status: expected pre-0001 drift — 0001 must reconcile in P3.4-D",
    ]
    return "\n".join(lines)


def assert_known_pre_0001_drift_detected(drift: dict[str, Any]) -> None:
    """Acceptance harness: known gaps must be present before 0001 exists."""
    assert drift["phase"] == PRE_0001_PHASE
    assert drift["indexes_only_in_migrated"], "expected migrate_schema-only indexes"
    assert drift["index_count_migrated"] > drift["index_count_create_all"]

    for name in ACCOUNTING_INTEGRITY_UNIQUES:
        assert name in drift["indexes_only_in_migrated"], (
            f"expected accounting unique {name!r} only in migrate_schema path"
        )

    for name in COMPOSITE_MIGRATE_ONLY_INDEXES:
        assert name in drift["indexes_only_in_migrated"], (
            f"expected composite index {name!r} only in migrate_schema path"
        )

    assert len(drift["company_id_indexes_only_in_migrated"]) >= 10, (
        "expected substantial company_id index drift from migrate_schema"
    )

    assert not drift["equivalent"], (
        "pre-0001 schemas must not be equivalent yet"
    )


def run_pre_0001_baseline_equivalence() -> dict[str, Any]:
    """Full harness run returning summaries + drift + report text."""
    create_all = build_create_all_schema_summary()
    migrated = build_migrate_evolved_schema_summary()
    drift = compute_schema_drift(create_all, migrated)
    return {
        "create_all_summary": create_all,
        "migrated_summary": migrated,
        "drift": drift,
        "report": format_pre_0001_drift_report(drift),
    }


def _load_0001_baseline_module():
    """Load revision 0001 without requiring ``import alembic`` (local tree shadows package)."""
    from sqlalchemy import text as sa_text

    source = BASELINE_0001_PATH.read_text(encoding="utf-8")
    cleaned = "\n".join(
        line for line in source.splitlines() if line.strip() != "from alembic import op"
    )
    mod = types.ModuleType("alembic_baseline_0001")
    mod.__dict__.update(
        {
            "__name__": "alembic_baseline_0001",
            "annotations": __import__("__future__").annotations,
            "text": sa_text,
            "op": None,
        }
    )
    exec(compile(cleaned, str(BASELINE_0001_PATH), "exec"), mod.__dict__)
    return mod


def build_alembic_0001_schema_summary() -> dict[str, Any]:
    """Schema A — Alembic revision ``0001`` upgrade on ephemeral SQLite.

    Uses this module's ``Base`` (ORM tables registered at import) plus the
    supplemental index DDL from ``0001_baseline.py``. Avoids calling
    ``upgrade()`` directly because ``importlib.reload(db)`` in other tests can
    leave ``db.Base`` detached from ORM tables while ``Base`` here remains valid.
    """
    _register_models()
    mod = _load_0001_baseline_module()
    engine = _make_in_memory_engine()
    try:
        with engine.begin() as connection:
            Base.metadata.create_all(connection)
            for ddl in mod._SUPPLEMENTAL_INDEX_SQL:
                connection.execute(text(ddl))
        return extract_sqlite_schema_summary(engine)
    finally:
        engine.dispose()


def compute_post_0001_drift(
    alembic_summary: dict[str, Any],
    migrated_summary: dict[str, Any],
) -> dict[str, Any]:
    """Diff Alembic 0001 vs migrate_schema-evolved summaries."""
    drift = compute_schema_drift(alembic_summary, migrated_summary)
    drift["phase"] = POST_0001_PHASE
    return drift


def format_post_0001_drift_report(drift: dict[str, Any]) -> str:
    lines = [
        "P3.4-D baseline equivalence report (post-0001)",
        f"phase: {drift.get('phase')}",
        f"equivalent: {drift.get('equivalent')}",
        f"indexes alembic_0001: {drift.get('index_count_create_all')}",
        f"indexes migrated: {drift.get('index_count_migrated')}",
        f"indexes only in migrated: {drift.get('indexes_only_in_migrated')}",
        f"indexes only in alembic_0001: {drift.get('indexes_only_in_create_all')}",
        f"column_diffs: {drift.get('column_diffs')}",
    ]
    return "\n".join(lines)


def assert_alembic_0001_matches_migrate_schema(drift: dict[str, Any]) -> None:
    """Acceptance gate: 0001 upgrade must match migrate_schema-evolved schema."""
    assert drift["phase"] == POST_0001_PHASE
    assert drift["tables_only_in_create_all"] == [], drift["tables_only_in_create_all"]
    assert drift["tables_only_in_migrated"] == [], drift["tables_only_in_migrated"]
    assert not drift["column_diffs"], drift["column_diffs"]
    assert not drift["indexes_only_in_migrated"], drift["indexes_only_in_migrated"]
    assert not drift["indexes_only_in_create_all"], drift["indexes_only_in_create_all"]
    assert drift["equivalent"]


def run_post_0001_baseline_equivalence() -> dict[str, Any]:
    """Full harness: Alembic 0001 vs migrate_schema-evolved."""
    alembic = build_alembic_0001_schema_summary()
    migrated = build_migrate_evolved_schema_summary()
    drift = compute_post_0001_drift(alembic, migrated)
    return {
        "alembic_summary": alembic,
        "migrated_summary": migrated,
        "drift": drift,
        "report": format_post_0001_drift_report(drift),
    }
