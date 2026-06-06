"""Accounting mode policy bundles — stub for Phase 14D-B2b / policy engine.

Not applied at runtime in 14D-B2a.
"""

ACCOUNTING_MODE_BUNDLES: dict[str, dict[str, str]] = {
    "flexible": {
        "policy.period_backdating": "allow",
        "policy.eod_close": "not_required",
        "policy.cash_reconciliation": "not_required",
        "policy.receipt_capture": "never",
    },
    "standard": {
        "policy.period_backdating": "warn",
        "policy.eod_close": "recommended",
        "policy.cash_reconciliation": "recommended",
        "policy.receipt_capture": "above_amount",
    },
    "strict": {
        "policy.period_backdating": "block",
        "policy.eod_close": "required",
        "policy.cash_reconciliation": "required",
        "policy.receipt_capture": "always",
    },
}
