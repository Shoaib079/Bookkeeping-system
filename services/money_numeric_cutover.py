"""MD-05-IMPL-5 — flag-gated money NUMERIC cutover (0001 → 0002).

Reuses P3.8 backup path + confirmation phrase. Never auto-applies to production
``erp_data.db`` unless an explicit production-approval env is set (still blocked
in IMPL-5; PG production cutover is a separate approval).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from sqlalchemy.orm import Session

from services.schema_migration_gate import (
    ACTION_UPGRADE_HEAD,
    MigrationGateDecision,
    evaluate_migration_gate,
)
from services.schema_version import STATUS_BEHIND_HEAD

_LOG = logging.getLogger(__name__)

MONEY_NUMERIC_CUTOVER_ENV_VAR = "ERP_MONEY_NUMERIC_CUTOVER"
MONEY_NUMERIC_PRODUCTION_APPROVAL_ENV_VAR = "ERP_MONEY_NUMERIC_PRODUCTION_APPROVAL"
MONEY_NUMERIC_PRODUCTION_APPROVAL_PHRASE = "APPROVE PRODUCTION POSTGRES CUTOVER"

MONEY_NUMERIC_FROM_REVISION = "0001"
MONEY_NUMERIC_TO_REVISION = "0002"

_TRUE_FLAG_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_FLAG_VALUES = frozenset({"0", "false", "no", "off"})


def parse_money_numeric_cutover_flag(value: str | None) -> bool:
    """Parse ``ERP_MONEY_NUMERIC_CUTOVER`` (default off)."""
    if value is None:
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    if normalized in _TRUE_FLAG_VALUES:
        return True
    if normalized in _FALSE_FLAG_VALUES:
        return False
    return False


def is_money_numeric_cutover_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environ is None else environ
    return parse_money_numeric_cutover_flag(source.get(MONEY_NUMERIC_CUTOVER_ENV_VAR))


def is_money_numeric_production_approval_given(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Explicit operator phrase for production DB cutover (PG path; not used in IMPL-5)."""
    source = os.environ if environ is None else environ
    value = source.get(MONEY_NUMERIC_PRODUCTION_APPROVAL_ENV_VAR)
    if value is None:
        return False
    return value.strip() == MONEY_NUMERIC_PRODUCTION_APPROVAL_PHRASE


def is_money_numeric_cutover_eligible(
    *,
    schema_status: str,
    db_revision: str | None,
    head_revision: str | None,
) -> bool:
    """True only for populated DB at 0001 with local head 0002."""
    if schema_status.strip().lower() != STATUS_BEHIND_HEAD:
        return False
    return (
        db_revision == MONEY_NUMERIC_FROM_REVISION
        and head_revision == MONEY_NUMERIC_TO_REVISION
    )


def evaluate_money_numeric_cutover_gate(
    *,
    db_path_or_url: str,
    backup_path: str | None,
    confirmation_value: str | None,
    allow_production: bool = False,
) -> MigrationGateDecision:
    """P3.8 gate for populated 0001→0002 upgrade."""
    return evaluate_migration_gate(
        db_path_or_url=db_path_or_url,
        action=ACTION_UPGRADE_HEAD,
        is_populated=True,
        backup_path=backup_path,
        confirmation_value=confirmation_value,
        require_backup=True,
        require_confirmation=True,
        is_strict_new_empty=False,
    )


def is_money_numeric_cutover_authorized(
    *,
    cutover_enabled: bool,
    eligible: bool,
    gate_decision: MigrationGateDecision,
    allow_production: bool,
    database_url: str,
) -> bool:
    """True when cutover flag is on, revision pair matches, gate passes, URL allowed."""
    if not cutover_enabled or not eligible or not gate_decision.allowed:
        return False
    from services.alembic_runner import is_allowed_database_url

    return is_allowed_database_url(database_url, allow_production=allow_production)


def resolve_money_numeric_allow_production(
    database_url: str,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Production paths stay blocked unless explicit production approval is set."""
    from services.schema_migration_gate import is_production_database_path

    if not is_production_database_path(database_url):
        return False
    return is_money_numeric_production_approval_given(environ)


def run_money_numeric_post_cutover(session: Session) -> None:
    """Re-derive cached GL and bank balances after 0002 upgrade."""
    import app as erp_app
    from services.banking_balance import sync_bank_account_balances

    erp_app.sync_account_balances(session)
    sync_bank_account_balances(session)
    _LOG.info(
        "[money-numeric] post-cutover cache re-sync complete (GL + bank balances)."
    )
