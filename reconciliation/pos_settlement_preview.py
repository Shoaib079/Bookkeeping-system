"""BANKING-UX-02 P1 — POS settlement preview helpers (read-only, no posting)."""

from __future__ import annotations

from dataclasses import dataclass, field

_TOLERANCE = 0.01


@dataclass
class PosSettlementPreviewWarning:
    key: str
    kwargs: dict = field(default_factory=dict)


@dataclass
class PosSettlementPreview:
    available_clearing: float
    settlement_amount: float
    bank_charges: float
    expected_bank_deposit: float
    remaining_clearing: float
    warnings: list[PosSettlementPreviewWarning] = field(default_factory=list)


def resolve_preview_bank_charges(
    settlement_amount: float,
    deposit_amount: float,
    *,
    fee_amount: float | None = None,
) -> float:
    """Bank charges for preview — explicit settlement fee or clearing minus deposit."""
    if fee_amount is not None:
        return round(float(fee_amount), 2)
    settlement = round(settlement_amount, 2)
    deposit = round(deposit_amount, 2)
    if settlement > deposit + _TOLERANCE:
        return round(settlement - deposit, 2)
    return 0.0


def compute_pos_settlement_preview(
    available_clearing_balance: float,
    settlement_amount: float,
    deposit_amount: float,
    *,
    fee_amount: float | None = None,
) -> PosSettlementPreview:
    """Preview POS settlement before posting.

    settlement_amount = selected clearing sales total (gross clearing cleared).
    expected_bank_deposit = settlement_amount - bank_charges (matches bank deposit).
    remaining_clearing = available_clearing_balance - settlement_amount.
    """
    available = round(available_clearing_balance, 2)
    settlement = round(settlement_amount, 2)
    deposit = round(deposit_amount, 2)
    charges = resolve_preview_bank_charges(
        settlement, deposit, fee_amount=fee_amount
    )
    expected_deposit = round(settlement - charges, 2)
    remaining = round(available - settlement, 2)

    warnings: list[PosSettlementPreviewWarning] = []
    if available <= _TOLERANCE:
        warnings.append(PosSettlementPreviewWarning("banking.pos_preview.warn_no_clearing"))
    if settlement > available + _TOLERANCE:
        warnings.append(
            PosSettlementPreviewWarning(
                "banking.pos_preview.warn_settlement_exceeds_clearing",
                {
                    "settlement": settlement,
                    "available": available,
                },
            )
        )
    if charges > settlement + _TOLERANCE:
        warnings.append(
            PosSettlementPreviewWarning(
                "banking.pos_preview.warn_fee_exceeds_settlement",
                {"fee": charges, "settlement": settlement},
            )
        )
    if expected_deposit < -_TOLERANCE:
        warnings.append(
            PosSettlementPreviewWarning(
                "banking.pos_preview.warn_negative_deposit",
                {"amount": expected_deposit},
            )
        )

    return PosSettlementPreview(
        available_clearing=available,
        settlement_amount=settlement,
        bank_charges=charges,
        expected_bank_deposit=expected_deposit,
        remaining_clearing=remaining,
        warnings=warnings,
    )
