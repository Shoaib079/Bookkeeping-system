"""POSTGRES-CUTOVER-PREP — runtime cutover gate parse tests."""

from __future__ import annotations

import pytest

from services import postgres_runtime_cutover as gate


def test_cutover_flag_defaults_off():
    assert gate.parse_postgres_runtime_cutover_flag(None) is False
    assert gate.parse_postgres_runtime_cutover_flag("") is False
    assert gate.parse_postgres_runtime_cutover_flag("0") is False


def test_cutover_flag_parses_true():
    assert gate.parse_postgres_runtime_cutover_flag("1") is True
    assert gate.parse_postgres_runtime_cutover_flag("yes") is True


def test_approval_phrase_required():
    assert gate.is_postgres_runtime_approval_given({"ERP_POSTGRES_RUNTIME_APPROVAL": "wrong"}) is False
    assert gate.is_postgres_runtime_approval_given(
        {"ERP_POSTGRES_RUNTIME_APPROVAL": gate.RUNTIME_CUTOVER_APPROVAL_PHRASE}
    ) is True


def test_blocked_when_flag_off():
    reason = gate.runtime_cutover_blocked_reason(
        cutover_flag=False,
        approval_given=True,
        target_is_sqlite=False,
    )
    assert reason is not None
    assert "off" in reason.lower()


def test_blocked_without_approval():
    reason = gate.runtime_cutover_blocked_reason(
        cutover_flag=True,
        approval_given=False,
        target_is_sqlite=False,
    )
    assert reason is not None
    assert "approval" in reason.lower()


def test_blocked_while_sqlite_target():
    reason = gate.runtime_cutover_blocked_reason(
        cutover_flag=True,
        approval_given=True,
        target_is_sqlite=True,
    )
    assert reason is not None
