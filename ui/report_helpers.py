"""Shared report UI helpers — DRY widgets for management report patterns.

Extracted from repeated patterns in the Reports page of app.py.
"""

from __future__ import annotations

import datetime
from typing import Any, Callable

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Period-over-period growth comparison
# ---------------------------------------------------------------------------

def growth_comparison_kpi(
    *,
    session: Any,
    model: Any,
    amount_col: Any,
    date_col: Any,
    is_void_col: Any,
    d_from: datetime.date,
    d_to: datetime.date,
    currency: str,
    export_prefix: str,
    render_kpi_grid_fn: Callable,
    render_export_buttons_fn: Callable,
    t_fn: Callable,
    cq_fn: Callable,
    positive_is_good: bool = True,
) -> None:
    """Render a current-vs-prior period growth comparison with KPI cards.

    This pattern was duplicated verbatim for sales_growth and expense_growth.

    Parameters
    ----------
    session : SQLAlchemy session
    model : ORM model class (e.g. ``Sale``, ``ExpenseRecord``)
    amount_col : Column attribute for the monetary amount (e.g. ``Sale.amount``)
    date_col : Column attribute for the date (e.g. ``Sale.date``)
    is_void_col : Column attribute for the void flag (e.g. ``Sale.is_void``)
    d_from, d_to : Date range for the current period
    currency : Currency code string
    export_prefix : Filename prefix for export buttons
    render_kpi_grid_fn : ``render_kpi_grid`` callable from app.py
    render_export_buttons_fn : ``render_export_buttons`` callable from app.py
    t_fn : Translation function (``_t``)
    cq_fn : Company-scoped query function (``cq``)
    positive_is_good :
        If True (sales), growth is "success"; if False (expenses), growth is "danger".
    """
    from sqlalchemy import func

    st.caption(t_fn("rpt.kpi.growth_caption"))
    period_days = max((d_to - d_from).days, 1)
    prior_to = d_from - datetime.timedelta(days=1)
    prior_from = prior_to - datetime.timedelta(days=period_days - 1)

    cur_total = (
        cq_fn(session, model)
        .with_entities(func.sum(amount_col))
        .filter(date_col.between(d_from, d_to), is_void_col == False)  # noqa: E712
        .scalar()
        or 0.0
    )
    prior_total = (
        cq_fn(session, model)
        .with_entities(func.sum(amount_col))
        .filter(date_col.between(prior_from, prior_to), is_void_col == False)  # noqa: E712
        .scalar()
        or 0.0
    )
    change = cur_total - prior_total
    pct = (change / prior_total * 100) if prior_total else 0.0

    if positive_is_good:
        change_variant = "success" if change >= 0 else "danger"
        pct_variant = "success" if pct >= 0 else "danger"
        cur_variant = "success"
    else:
        change_variant = "danger" if change > 0 else "success"
        pct_variant = "danger" if pct > 0 else "success"
        cur_variant = "danger"

    render_kpi_grid_fn([
        {
            "label": t_fn("rpt.kpi.current_period", frm=d_from, to=d_to),
            "value": f"{currency} {cur_total:,.2f}",
            "variant": cur_variant,
        },
        {
            "label": t_fn("rpt.kpi.prior_period", frm=prior_from, to=prior_to),
            "value": f"{currency} {prior_total:,.2f}",
            "variant": "muted",
        },
        {
            "label": t_fn("rpt.kpi.change"),
            "value": f"{currency} {change:+,.2f}",
            "variant": change_variant,
        },
        {
            "label": t_fn("rpt.kpi.growth_pct"),
            "value": f"{pct:+.1f}%",
            "variant": pct_variant,
        },
    ])
    df = pd.DataFrame([
        {
            t_fn("col.period"): t_fn("rpt.kpi.current_period", frm=d_from, to=d_to),
            t_fn("col.total"): round(cur_total, 2),
        },
        {
            t_fn("col.period"): t_fn("rpt.kpi.prior_period", frm=prior_from, to=prior_to),
            t_fn("col.total"): round(prior_total, 2),
        },
        {
            t_fn("col.period"): t_fn("rpt.kpi.change"),
            t_fn("col.total"): round(change, 2),
        },
        {
            t_fn("col.period"): t_fn("rpt.kpi.growth_pct"),
            t_fn("col.total"): round(pct, 2),
        },
    ])
    render_export_buttons_fn(df, export_prefix, pdf=False)
