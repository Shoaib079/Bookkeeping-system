"""POSTING-SERVICE-01 PS-P6-0b — yec_block_message call-site wiring proof."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")


def _fn_block(name: str) -> str:
    i = APP_SRC.index(f"def {name}(")
    j = APP_SRC.index("\ndef ", i + 10)
    return APP_SRC[i:j]


def test_post_partner_movement_uses_yec_block_message():
    block = _fn_block("post_partner_movement")
    assert "posting_service.post_partner_movement(" in block
    assert "company_id=current_company_required()" in block
    assert "cq(session, YearEndClose)" not in block
    assert "posting_service.yec_block_message(" not in block


def test_void_partner_movement_uses_yec_block_message():
    block = _fn_block("void_partner_movement")
    assert "posting_service.void_partner_movement(" in block
    assert "company_id=current_company_required()" in block
    assert "cq(session, YearEndClose)" not in block
    assert "posting_service.yec_block_message(" not in block


def test_post_worker_movement_uses_yec_block_message():
    block = _fn_block("post_worker_movement")
    assert "posting_service.post_worker_movement(" in block
    assert "company_id=current_company_required()" in block
    assert "cq(session, YearEndClose)" not in block
    assert "posting_service.yec_block_message(" not in block


def test_void_worker_movement_uses_yec_block_message():
    block = _fn_block("void_worker_movement")
    assert "posting_service.void_worker_movement(" in block
    assert "company_id=current_company_required()" in block
    assert "cq(session, YearEndClose)" not in block
    assert "posting_service.yec_block_message(" not in block


def test_void_profit_allocation_uses_yec_block_message():
    block = _fn_block("void_profit_allocation")
    assert "posting_service.yec_block_message(" in block
    assert "period.start_date" in block
    assert "period_end_date=period.end_date" in block
    assert 'mode="allocation_void"' in block
    assert "company_id=current_company_required()" in block
    assert "return _yec_msg" in block
    assert "cq(session, YearEndClose)" not in block
