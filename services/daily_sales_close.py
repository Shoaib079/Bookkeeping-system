"""DSC-P1 — External Sales Verification service layer.

FastAPI-ready: explicit inputs, serializable outputs, no Streamlit or app.py imports.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
from typing import Any

from models import AuditLog, ExternalSalesVerification, Sale
from services.money import money_to_float
from sqlalchemy import func
from sqlalchemy.orm import Session

DEFAULT_TOLERANCE = 0.01
MAX_BRANCH_LEN = 200
MAX_SOURCE_NAME_LEN = 200

ALLOWED_SOURCE_TYPES = frozenset({
    "POS",
    "ERP",
    "MANUAL",
    "Z_REPORT",
    "EXCEL_UPLOAD",
    "OTHER",
})


# ── Serializable DTOs ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ErpSalesTotals:
    business_date: datetime.date
    total: float
    cash: float
    card: float
    credit: float
    sale_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_date": self.business_date.isoformat(),
            "total": self.total,
            "cash": self.cash,
            "card": self.card,
            "credit": self.credit,
            "sale_count": self.sale_count,
        }


@dataclass(frozen=True)
class ExternalSalesTotals:
    external_total: float | None = None
    z_report_total: float | None = None
    cash: float | None = None
    card: float | None = None
    online: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalSalesSource:
    source_name: str
    source_type: str | None = None
    branch_location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "branch_location": self.branch_location,
        }


@dataclass(frozen=True)
class SalesVarianceResult:
    variance_total: float | None
    variance_cash: float | None
    variance_card: float | None
    variance_online: float | None
    z_report_variance: float | None
    variance_type: str
    within_tolerance: bool
    breakdown_warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variance_total": self.variance_total,
            "variance_cash": self.variance_cash,
            "variance_card": self.variance_card,
            "variance_online": self.variance_online,
            "z_report_variance": self.z_report_variance,
            "variance_type": self.variance_type,
            "within_tolerance": self.within_tolerance,
            "breakdown_warnings": list(self.breakdown_warnings),
        }


@dataclass(frozen=True)
class VerificationRecord:
    """Serializable verification row for API and UI layers."""

    id: int
    company_id: int
    business_date: datetime.date
    source_name: str
    source_type: str | None
    branch_location: str | None
    status: str
    external_total: float | None
    z_report_total: float | None
    external_cash: float | None
    external_card: float | None
    external_online: float | None
    erp_total: float | None
    erp_cash: float | None
    erp_card: float | None
    erp_credit: float | None
    variance_total: float | None
    variance_cash: float | None
    variance_card: float | None
    variance_online: float | None
    z_report_variance: float | None
    variance_type: str | None
    within_tolerance: bool | None
    variance_acknowledged: bool
    variance_ack_note: str | None
    notes: str | None
    verified_by_id: int | None
    verified_at: datetime.datetime | None
    created_by_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
    is_void: bool
    voided_by_id: int | None
    voided_at: datetime.datetime | None
    void_reason: str | None
    sale_count_snapshot: int | None
    attachment_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "business_date": self.business_date.isoformat(),
            "source_name": self.source_name,
            "source_type": self.source_type,
            "branch_location": self.branch_location,
            "status": self.status,
            "external_total": self.external_total,
            "z_report_total": self.z_report_total,
            "external_cash": self.external_cash,
            "external_card": self.external_card,
            "external_online": self.external_online,
            "erp_total": self.erp_total,
            "erp_cash": self.erp_cash,
            "erp_card": self.erp_card,
            "erp_credit": self.erp_credit,
            "variance_total": self.variance_total,
            "variance_cash": self.variance_cash,
            "variance_card": self.variance_card,
            "variance_online": self.variance_online,
            "z_report_variance": self.z_report_variance,
            "variance_type": self.variance_type,
            "within_tolerance": self.within_tolerance,
            "variance_acknowledged": self.variance_acknowledged,
            "variance_ack_note": self.variance_ack_note,
            "notes": self.notes,
            "verified_by_id": self.verified_by_id,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_void": self.is_void,
            "voided_by_id": self.voided_by_id,
            "voided_at": self.voided_at.isoformat() if self.voided_at else None,
            "void_reason": self.void_reason,
            "sale_count_snapshot": self.sale_count_snapshot,
            "attachment_count": self.attachment_count,
        }


@dataclass(frozen=True)
class MutationResult:
    """Result of save_draft or verify_external_sales."""

    record_id: int | None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.record_id is not None and not self.error

    def to_dict(self) -> dict[str, Any]:
        return {"record_id": self.record_id, "error": self.error, "ok": self.ok}


# ── Pure validation / math ────────────────────────────────────────────────────


def normalize_branch(branch: str | None) -> str | None:
    """Trim branch; empty or whitespace-only becomes None (default site)."""
    if branch is None:
        return None
    trimmed = branch.strip()
    if not trimmed:
        return None
    return trimmed[:MAX_BRANCH_LEN]


def validate_external_source(source: ExternalSalesSource) -> str | None:
    """Return an error message or None when valid."""
    name = (source.source_name or "").strip()
    if not name:
        return "Source name is required."
    if len(name) > MAX_SOURCE_NAME_LEN:
        return f"Source name must be at most {MAX_SOURCE_NAME_LEN} characters."
    if source.source_type is not None and source.source_type not in ALLOWED_SOURCE_TYPES:
        return f"Invalid source type: {source.source_type}."
    if source.branch_location is not None:
        branch = normalize_branch(source.branch_location)
        if branch and len(branch) > MAX_BRANCH_LEN:
            return f"Branch location must be at most {MAX_BRANCH_LEN} characters."
    return None


def validate_external_totals(
    external: ExternalSalesTotals,
    *,
    for_verify: bool = False,
) -> str | None:
    """Return an error message or None when valid."""
    fields = (
        ("external_total", external.external_total),
        ("z_report_total", external.z_report_total),
        ("cash", external.cash),
        ("card", external.card),
        ("online", external.online),
    )
    for label, value in fields:
        if value is not None and value < 0:
            return f"{label} cannot be negative."

    if for_verify:
        if external.external_total is None and external.z_report_total is None:
            return "At least one of external total or Z-report total is required to verify."
    return None


def _exceeds_tolerance(value: float, tolerance: float) -> bool:
    return abs(value) > tolerance


def _classify_variance_type(failures: list[str]) -> str:
    if not failures:
        return "balanced"
    if len(failures) > 1:
        return "multi_variance"
    mapping = {
        "total": "total_variance",
        "cash": "cash_variance",
        "card": "card_variance",
        "online": "online_variance",
        "z": "z_report_variance",
    }
    return mapping[failures[0]]


def compute_variance(
    external: ExternalSalesTotals,
    erp: ErpSalesTotals,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> SalesVarianceResult:
    """Pure variance math — no database access."""
    breakdown_warnings: list[str] = []
    variance_total: float | None = None
    variance_cash: float | None = None
    variance_card: float | None = None
    variance_online: float | None = None
    z_report_variance: float | None = None
    failures: list[str] = []

    if external.external_total is not None:
        variance_total = money_to_float(external.external_total - erp.total)
        if _exceeds_tolerance(variance_total, tolerance):
            failures.append("total")

        has_breakdown = any(
            v is not None for v in (external.cash, external.card, external.online)
        )
        if has_breakdown:
            breakdown_sum = money_to_float(
                (external.cash or 0.0)
                + (external.card or 0.0)
                + (external.online or 0.0),
            )
            if _exceeds_tolerance(breakdown_sum - external.external_total, tolerance):
                breakdown_warnings.append(
                    "External breakdown sum differs from external total by more than tolerance."
                )

    if external.cash is not None:
        variance_cash = money_to_float(external.cash - erp.cash)
        if _exceeds_tolerance(variance_cash, tolerance):
            failures.append("cash")

    if external.card is not None:
        variance_card = money_to_float(external.card - erp.card)
        if _exceeds_tolerance(variance_card, tolerance):
            failures.append("card")

    if external.online is not None:
        variance_online = money_to_float(external.online - erp.credit)
        if _exceeds_tolerance(variance_online, tolerance):
            failures.append("online")

    if external.z_report_total is not None:
        z_report_variance = money_to_float(external.z_report_total - erp.total)
        if _exceeds_tolerance(z_report_variance, tolerance):
            failures.append("z")

    within_tolerance = not failures
    variance_type = _classify_variance_type(failures)

    return SalesVarianceResult(
        variance_total=variance_total,
        variance_cash=variance_cash,
        variance_card=variance_card,
        variance_online=variance_online,
        z_report_variance=z_report_variance,
        variance_type=variance_type,
        within_tolerance=within_tolerance,
        breakdown_warnings=tuple(breakdown_warnings),
    )


# ── Internal DB helpers ───────────────────────────────────────────────────────


def _verification_query(session: Session, company_id: int):
    return session.query(ExternalSalesVerification).filter(
        ExternalSalesVerification.company_id == company_id,
    )


def _apply_branch_filter(query, branch: str | None):
    normalized = normalize_branch(branch)
    if normalized is None:
        return query.filter(ExternalSalesVerification.branch_location.is_(None))
    return query.filter(ExternalSalesVerification.branch_location == normalized)


def _to_record(row: ExternalSalesVerification) -> VerificationRecord:
    return VerificationRecord(
        id=row.id,
        company_id=row.company_id,
        business_date=row.business_date,
        source_name=row.source_name,
        source_type=row.source_type,
        branch_location=row.branch_location,
        status=row.status,
        external_total=row.external_total,
        z_report_total=row.z_report_total,
        external_cash=row.external_cash,
        external_card=row.external_card,
        external_online=row.external_online,
        erp_total=row.erp_total,
        erp_cash=row.erp_cash,
        erp_card=row.erp_card,
        erp_credit=row.erp_credit,
        variance_total=row.variance_total,
        variance_cash=row.variance_cash,
        variance_card=row.variance_card,
        variance_online=row.variance_online,
        z_report_variance=row.z_report_variance,
        variance_type=row.variance_type,
        within_tolerance=row.within_tolerance,
        variance_acknowledged=bool(row.variance_acknowledged),
        variance_ack_note=row.variance_ack_note,
        notes=row.notes,
        verified_by_id=row.verified_by_id,
        verified_at=row.verified_at,
        created_by_id=row.created_by_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        is_void=bool(row.is_void),
        voided_by_id=row.voided_by_id,
        voided_at=row.voided_at,
        void_reason=row.void_reason,
        sale_count_snapshot=row.sale_count_snapshot,
        attachment_count=row.attachment_count or 0,
    )


def _external_from_row(row: ExternalSalesVerification) -> ExternalSalesTotals:
    return ExternalSalesTotals(
        external_total=money_to_float(row.external_total) if row.external_total is not None else None,
        z_report_total=money_to_float(row.z_report_total) if row.z_report_total is not None else None,
        cash=money_to_float(row.external_cash) if row.external_cash is not None else None,
        card=money_to_float(row.external_card) if row.external_card is not None else None,
        online=money_to_float(row.external_online) if row.external_online is not None else None,
    )


def _write_audit(
    session: Session,
    *,
    company_id: int,
    action: str,
    entity_id: int,
    description: str,
    performed_by: str | None = None,
) -> None:
    session.add(
        AuditLog(
            timestamp=datetime.datetime.now(),
            action=action,
            entity_type="ExternalSalesVerification",
            entity_id=entity_id,
            description=description,
            performed_by=performed_by,
            company_id=company_id,
        )
    )


def _clear_verified_snapshot(row: ExternalSalesVerification) -> None:
    row.erp_total = None
    row.erp_cash = None
    row.erp_card = None
    row.erp_credit = None
    row.variance_total = None
    row.variance_cash = None
    row.variance_card = None
    row.variance_online = None
    row.z_report_variance = None
    row.variance_type = None
    row.within_tolerance = None
    row.variance_acknowledged = False
    row.variance_ack_note = None
    row.verified_by_id = None
    row.verified_at = None
    row.sale_count_snapshot = None


def _apply_source(row: ExternalSalesVerification, source: ExternalSalesSource) -> None:
    row.source_name = source.source_name.strip()
    row.source_type = source.source_type
    row.branch_location = normalize_branch(source.branch_location)


def _apply_external(row: ExternalSalesVerification, external: ExternalSalesTotals) -> None:
    row.external_total = external.external_total
    row.z_report_total = external.z_report_total
    row.external_cash = external.cash
    row.external_card = external.card
    row.external_online = external.online


# ── Public service API ────────────────────────────────────────────────────────


def compute_erp_sales_totals(
    session: Session,
    company_id: int,
    business_date: datetime.date,
) -> ErpSalesTotals:
    """Read-only ERP sales sums for one company and business date."""

    def _sale_sum(sale_type: str | None = None) -> float:
        q = session.query(func.sum(Sale.amount)).filter(
            Sale.company_id == company_id,
            Sale.date == business_date,
            Sale.is_void == False,  # noqa: E712
        )
        if sale_type:
            q = q.filter(Sale.sale_type == sale_type)
        return money_to_float(q.scalar() or 0.0)

    cash = _sale_sum("Cash")
    card = _sale_sum("Card")
    credit = _sale_sum("Credit")
    total = money_to_float(cash + card + credit)
    sale_count = (
        session.query(func.count(Sale.id))
        .filter(
            Sale.company_id == company_id,
            Sale.date == business_date,
            Sale.is_void == False,  # noqa: E712
        )
        .scalar()
        or 0
    )
    return ErpSalesTotals(
        business_date=business_date,
        total=total,
        cash=cash,
        card=card,
        credit=credit,
        sale_count=int(sale_count),
    )


def get_active_verification(
    session: Session,
    company_id: int,
    business_date: datetime.date,
    branch: str | None = None,
) -> VerificationRecord | None:
    """Return the active (non-void) verification for company/date/branch, if any."""
    q = _verification_query(session, company_id).filter(
        ExternalSalesVerification.business_date == business_date,
        ExternalSalesVerification.is_void == False,  # noqa: E712
    )
    q = _apply_branch_filter(q, branch)
    row = q.first()
    return _to_record(row) if row else None


def list_verifications(
    session: Session,
    company_id: int,
    date_from: datetime.date,
    date_to: datetime.date,
    branch: str | None = None,
) -> list[VerificationRecord]:
    """List verification records in a date range (includes voided rows)."""
    q = _verification_query(session, company_id).filter(
        ExternalSalesVerification.business_date >= date_from,
        ExternalSalesVerification.business_date <= date_to,
    )
    q = _apply_branch_filter(q, branch)
    rows = q.order_by(
        ExternalSalesVerification.business_date.desc(),
        ExternalSalesVerification.id.desc(),
    ).all()
    return [_to_record(row) for row in rows]


def save_draft(
    session: Session,
    company_id: int,
    business_date: datetime.date,
    source: ExternalSalesSource,
    external: ExternalSalesTotals,
    user_id: int,
    notes: str | None = None,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    """Create or update an active draft; ERP and variance columns remain NULL."""
    source_err = validate_external_source(source)
    if source_err:
        return MutationResult(record_id=None, error=source_err)
    totals_err = validate_external_totals(external, for_verify=False)
    if totals_err:
        return MutationResult(record_id=None, error=totals_err)

    normalized_branch = normalize_branch(source.branch_location)
    active = (
        _verification_query(session, company_id)
        .filter(
            ExternalSalesVerification.business_date == business_date,
            ExternalSalesVerification.is_void == False,  # noqa: E712
        )
    )
    active = _apply_branch_filter(active, normalized_branch)
    row = active.first()

    now = datetime.datetime.now()
    if row is not None:
        if row.status == "verified":
            return MutationResult(
                record_id=None,
                error=(
                    "An active verified record already exists for this date and branch. "
                    "Void it before saving a new draft."
                ),
            )
        _apply_source(row, source)
        _apply_external(row, external)
        row.notes = notes.strip() if notes else None
        row.updated_at = now
        created = False
    else:
        row = ExternalSalesVerification(
            company_id=company_id,
            business_date=business_date,
            status="draft",
            notes=notes.strip() if notes else None,
            created_by_id=user_id,
            created_at=now,
            updated_at=now,
            is_void=False,
            variance_acknowledged=False,
            attachment_count=0,
        )
        _apply_source(row, source)
        _apply_external(row, external)
        _clear_verified_snapshot(row)
        session.add(row)
        created = True

    session.flush()
    session.commit()

    action = "Create" if created else "Update"
    _write_audit(
        session,
        company_id=company_id,
        action=action,
        entity_id=row.id,
        description=f"External sales verification draft {action.lower()}d for {business_date}",
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id, error="")


def verify_external_sales(
    session: Session,
    company_id: int,
    verification_id: int,
    user_id: int,
    *,
    ack_note: str | None = None,
    performed_by: str | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> MutationResult:
    """Snapshot ERP totals and mark a draft as verified."""
    row = session.get(ExternalSalesVerification, verification_id)
    if not row or row.company_id != company_id:
        return MutationResult(record_id=None, error="Verification record not found.")
    if row.is_void:
        return MutationResult(record_id=None, error="Cannot verify a voided record.")
    if row.status == "verified":
        return MutationResult(record_id=None, error="This record is already verified.")

    external = _external_from_row(row)
    totals_err = validate_external_totals(external, for_verify=True)
    if totals_err:
        return MutationResult(record_id=None, error=totals_err)

    erp = compute_erp_sales_totals(session, company_id, row.business_date)
    variance = compute_variance(external, erp, tolerance=tolerance)

    if not variance.within_tolerance:
        note = (ack_note or "").strip()
        if not note:
            return MutationResult(
                record_id=None,
                error="Material variance requires an acknowledgement note.",
            )

    row.erp_total = erp.total
    row.erp_cash = erp.cash
    row.erp_card = erp.card
    row.erp_credit = erp.credit
    row.variance_total = variance.variance_total
    row.variance_cash = variance.variance_cash
    row.variance_card = variance.variance_card
    row.variance_online = variance.variance_online
    row.z_report_variance = variance.z_report_variance
    row.variance_type = variance.variance_type
    row.within_tolerance = variance.within_tolerance
    row.sale_count_snapshot = erp.sale_count
    row.status = "verified"
    row.verified_by_id = user_id
    row.verified_at = datetime.datetime.now()
    row.updated_at = row.verified_at

    if variance.within_tolerance:
        row.variance_acknowledged = False
        row.variance_ack_note = (ack_note or "").strip() or None
    else:
        row.variance_acknowledged = True
        row.variance_ack_note = (ack_note or "").strip()

    session.commit()

    _write_audit(
        session,
        company_id=company_id,
        action="Verify",
        entity_id=row.id,
        description=(
            f"External sales verification verified for {row.business_date} "
            f"({variance.variance_type})"
        ),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id, error="")


def void_verification(
    session: Session,
    company_id: int,
    verification_id: int,
    user_id: int,
    reason: str,
    *,
    performed_by: str | None = None,
) -> str:
    """Void a verification record. Returns an error message or empty string."""
    row = session.get(ExternalSalesVerification, verification_id)
    if not row or row.company_id != company_id:
        return "Verification record not found."
    if row.is_void:
        return "This verification has already been voided."

    clean_reason = (reason or "").strip()
    if not clean_reason:
        return "Void reason is required."

    row.is_void = True
    row.status = "voided"
    row.voided_by_id = user_id
    row.voided_at = datetime.datetime.now()
    row.void_reason = clean_reason
    row.updated_at = row.voided_at
    session.commit()

    _write_audit(
        session,
        company_id=company_id,
        action="Void",
        entity_id=row.id,
        description=f"External sales verification voided for {row.business_date}: {clean_reason}",
        performed_by=performed_by,
    )
    session.commit()
    return ""


def is_verification_stale(
    session: Session,
    company_id: int,
    record: VerificationRecord,
) -> bool:
    """True when verified sale count no longer matches the stored snapshot."""
    if record.company_id != company_id:
        return False
    if record.status != "verified" or record.is_void:
        return False
    if record.sale_count_snapshot is None:
        return False
    current = compute_erp_sales_totals(session, company_id, record.business_date)
    return current.sale_count != record.sale_count_snapshot
