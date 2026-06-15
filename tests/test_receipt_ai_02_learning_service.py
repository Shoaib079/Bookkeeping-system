"""RECEIPT-AI-02-IMPL-1 — tests for the pure receipt learning service."""

from __future__ import annotations

import datetime
import inspect
import json

import pytest

from services import receipt_learning as learn


def _event(**kw) -> learn.ApprovalLearningEvent:
    base = dict(
        company_id=1,
        vendor_signature="BIM",
        expense_record_id=100,
        tx_category_id=5,
        tx_subcategory_id=12,
        payment_method="Cash",
        category_name="Groceries",
        amount=50.0,
        approved_at=datetime.datetime(2026, 6, 15, 10, 0, 0),
    )
    base.update(kw)
    return learn.ApprovalLearningEvent(**base)


class TestShouldLearn:
    def test_requires_expense_record_id(self):
        ok, reason = learn.should_learn_from_approval(_event(expense_record_id=None))
        assert not ok
        assert "expense_record_id" in reason

    def test_blank_vendor_does_not_learn(self):
        ok, _ = learn.should_learn_from_approval(_event(vendor_signature=""))
        assert not ok
        ok2, _ = learn.should_learn_from_approval(_event(vendor_signature="   "))
        assert not ok2

    def test_payroll_category_blocked(self):
        ok, reason = learn.should_learn_from_approval(
            _event(category_name="Payroll Expense")
        )
        assert not ok
        assert "never-learn" in reason


class TestRecordApproval:
    def test_increments_mapping(self):
        store = learn.InMemoryLearningStore()
        result = learn.record_approval(store, _event())
        assert result.learned
        assert result.records_written >= 3
        rows = store.list_for_signature(1, "vendor_category", "BIM")
        assert len(rows) == 1
        assert rows[0].approval_count == 1
        assert rows[0].target_value == "5"

    def test_missing_expense_record_does_not_learn(self):
        store = learn.InMemoryLearningStore()
        result = learn.record_approval(store, _event(expense_record_id=None))
        assert not result.learned
        assert store.all_records() == ()

    def test_blank_vendor_does_not_learn(self):
        store = learn.InMemoryLearningStore()
        result = learn.record_approval(store, _event(vendor_signature=""))
        assert not result.learned
        assert store.all_records() == ()

    def test_company_isolation(self):
        store = learn.InMemoryLearningStore()
        learn.record_approval(store, _event(company_id=1))
        learn.record_approval(store, _event(company_id=2, tx_category_id=9))
        assert learn.suggest_for_vendor(store, 1, "BIM") is not None
        assert learn.suggest_for_vendor(store, 2, "BIM") is not None
        cat_a = learn.suggest_for_vendor(store, 1, "BIM").category
        cat_b = learn.suggest_for_vendor(store, 2, "BIM").category
        assert cat_a.target_value == "5"
        assert cat_b.target_value == "9"
        assert learn.suggest_for_vendor(store, 1, "BIM").company_id == 1


class TestConfidence:
    def test_consistency_lowers_confidence_for_conflicts(self):
        store = learn.InMemoryLearningStore()
        for _ in range(3):
            learn.record_approval(store, _event(tx_category_id=5))
        learn.record_approval(store, _event(tx_category_id=9))

        dominant = learn.suggest_for_vendor(store, 1, "BIM")
        assert dominant is not None
        assert dominant.category.target_value == "5"
        dominant_conf = dominant.category.confidence

        records = store.list_for_signature(1, "vendor_category", "BIM")
        minority = next(r for r in records if r.target_value == "9")
        minority_conf = learn.calculate_confidence(
            approval_count=minority.approval_count,
            total_approvals_for_signature=sum(r.approval_count for r in records),
            approvals_for_target=minority.approval_count,
        )
        assert dominant_conf > minority_conf

    def test_confidence_tiers(self):
        assert learn.classify_confidence_tier(50.0, 1) == learn.TIER_MANUAL
        assert learn.classify_confidence_tier(85.0, 2) == learn.TIER_PREFILL
        assert learn.classify_confidence_tier(96.0, 3) == learn.TIER_AUTO_POST_ELIGIBLE
        assert learn.classify_confidence_tier(99.5, 5) == learn.TIER_TRUSTED

    def test_payment_suggestion_is_advisory(self):
        store = learn.InMemoryLearningStore()
        learn.record_approval(store, _event(payment_method="Card"))
        suggestion = learn.suggest_for_vendor(store, 1, "BIM")
        assert suggestion.payment_method is not None
        assert suggestion.payment_method.advisory_only is True
        assert suggestion.payment_method.target_value == "Card"


class TestPurity:
    def test_no_streamlit_or_db_imports(self):
        roots = set()
        import ast

        mod_tree = ast.parse(inspect.getsource(learn))
        for node in ast.walk(mod_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        for forbidden in ("streamlit", "sqlalchemy", "models", "app", "db"):
            assert forbidden not in roots

    def test_dtos_json_serializable(self):
        store = learn.InMemoryLearningStore()
        learn.record_approval(store, _event())
        suggestion = learn.suggest_for_vendor(store, 1, "BIM")
        result = learn.RecordApprovalResult(learned=True, records_written=1)
        json.dumps(_event().to_dict())
        json.dumps(result.to_dict())
        json.dumps(suggestion.to_dict())
        json.dumps(store.all_records()[0].to_dict())
