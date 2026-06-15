"""RECEIPT-AI-02-IMPL-3 — persistent LearningStore over ReceiptLearningMap.

Implements the :class:`services.receipt_learning.LearningStore` protocol using the
``receipt_learning_map`` table. Service-level ``record_approval`` / ``suggest_for_vendor``
work unchanged; **not** wired to ``approve_expense_draft`` in this slice.

No Streamlit, no auto-post, no posting changes.
"""

from __future__ import annotations

import datetime

from models import ReceiptLearningMap
from services import receipt_learning as learn
from sqlalchemy.orm import Session

_TARGET_KIND_BY_SIGNATURE: dict[learn.SignatureType, str] = {
    "vendor_category": "category_id",
    "vendor_subcategory": "subcategory_id",
    "vendor_payment": "payment_method",
    "item_product": "product_id",
    "source_format": "document_type",
}

_ID_TARGET_SIGNATURES: frozenset[learn.SignatureType] = frozenset(
    {"vendor_category", "vendor_subcategory", "item_product"}
)

_UNUSED_TARGET_ID = -1
_UNUSED_TARGET_VALUE = ""


def _encode_target(
    signature_type: learn.SignatureType,
    target_value: str,
) -> tuple[str, int, str]:
    kind = _TARGET_KIND_BY_SIGNATURE[signature_type]
    if signature_type in _ID_TARGET_SIGNATURES:
        return kind, int(target_value), _UNUSED_TARGET_VALUE
    return kind, _UNUSED_TARGET_ID, target_value


def _decode_target_value(row: ReceiptLearningMap) -> str:
    if row.target_id is not None and row.target_id != _UNUSED_TARGET_ID:
        return str(row.target_id)
    return row.target_value or ""


def _row_to_learning_record(row: ReceiptLearningMap) -> learn.LearningRecord:
    return learn.LearningRecord(
        company_id=row.company_id,
        signature_type=row.signature_type,  # type: ignore[arg-type]
        signature_key=row.signature_key,
        target_value=_decode_target_value(row),
        approval_count=row.approval_count,
        correction_count=row.correction_count,
        last_approved_at=row.last_approved_at,
    )


def _refresh_confidence_for_signature(
    session: Session,
    company_id: int,
    signature_type: learn.SignatureType,
    signature_key: str,
) -> None:
    rows = (
        session.query(ReceiptLearningMap)
        .filter(
            ReceiptLearningMap.company_id == company_id,
            ReceiptLearningMap.signature_type == signature_type,
            ReceiptLearningMap.signature_key == signature_key,
            ReceiptLearningMap.is_active.is_(True),
        )
        .all()
    )
    total = sum(r.approval_count for r in rows)
    for row in rows:
        row.confidence_cached = learn.calculate_confidence(
            approval_count=row.approval_count,
            total_approvals_for_signature=total,
            approvals_for_target=row.approval_count,
            correction_count=row.correction_count,
        )
        row.updated_at = datetime.datetime.now()


class PersistentLearningStore:
    """SQLAlchemy-backed :class:`~services.receipt_learning.LearningStore`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_signature(
        self,
        company_id: int,
        signature_type: learn.SignatureType,
        signature_key: str,
    ) -> tuple[learn.LearningRecord, ...]:
        rows = (
            self._session.query(ReceiptLearningMap)
            .filter(
                ReceiptLearningMap.company_id == company_id,
                ReceiptLearningMap.signature_type == signature_type,
                ReceiptLearningMap.signature_key == signature_key,
                ReceiptLearningMap.is_active.is_(True),
            )
            .order_by(ReceiptLearningMap.approval_count.desc())
            .all()
        )
        return tuple(_row_to_learning_record(r) for r in rows)

    def record_approval_hit(
        self,
        company_id: int,
        signature_type: learn.SignatureType,
        signature_key: str,
        target_value: str,
        *,
        approved_at: datetime.datetime,
    ) -> learn.LearningRecord:
        target_kind, target_id, target_val = _encode_target(signature_type, target_value)
        row = (
            self._session.query(ReceiptLearningMap)
            .filter(
                ReceiptLearningMap.company_id == company_id,
                ReceiptLearningMap.signature_type == signature_type,
                ReceiptLearningMap.signature_key == signature_key,
                ReceiptLearningMap.target_kind == target_kind,
                ReceiptLearningMap.target_id == target_id,
                ReceiptLearningMap.target_value == target_val,
            )
            .first()
        )
        now = datetime.datetime.now()
        if row is None:
            row = ReceiptLearningMap(
                company_id=company_id,
                signature_type=signature_type,
                signature_key=signature_key,
                target_kind=target_kind,
                target_id=target_id,
                target_value=target_val,
                approval_count=1,
                correction_count=0,
                last_approved_at=approved_at,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.approval_count += 1
            row.last_approved_at = approved_at
            row.updated_at = now
            row.is_active = True
        self._session.flush()
        _refresh_confidence_for_signature(
            self._session, company_id, signature_type, signature_key
        )
        self._session.commit()
        self._session.refresh(row)
        return _row_to_learning_record(row)

    def get_map_row(
        self,
        company_id: int,
        signature_type: learn.SignatureType,
        signature_key: str,
        target_value: str,
    ) -> ReceiptLearningMap | None:
        """Test/admin helper — fetch the persisted map row."""
        target_kind, target_id, target_val = _encode_target(signature_type, target_value)
        return (
            self._session.query(ReceiptLearningMap)
            .filter(
                ReceiptLearningMap.company_id == company_id,
                ReceiptLearningMap.signature_type == signature_type,
                ReceiptLearningMap.signature_key == signature_key,
                ReceiptLearningMap.target_kind == target_kind,
                ReceiptLearningMap.target_id == target_id,
                ReceiptLearningMap.target_value == target_val,
            )
            .first()
        )


def persistent_learning_store(session: Session) -> PersistentLearningStore:
    """Factory for the DB-backed learning store."""
    return PersistentLearningStore(session)
