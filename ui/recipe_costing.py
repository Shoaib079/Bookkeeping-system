"""RC-P1b — Recipe Costing presentation (no business logic).

Calls services.recipe_costing only. Restaurant-friendly labels — names, not IDs.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services import recipe_costing as rc_svc
from ui.section import section_header_html

_NEW_RECIPE_KEY = 0
_DEFAULT_LINE_UNITS = ("each", "g", "kg", "ml", "l", "dozen")


def _erp():
    import app as app_module

    return app_module


def _fmt_money(currency: str, value: float | None) -> str:
    if value is None:
        return "—"
    return f"{currency} {value:,.2f}"


def _fmt_qty_unit(quantity: float, unit: str) -> str:
    qty = int(quantity) if quantity == int(quantity) else round(quantity, 2)
    return f"{qty} {unit}"


def _line_label(line: Any) -> str:
    return getattr(line, "display_name", None) or getattr(line, "name", "?")


def _recipe_tree_markdown(recipe_name: str, lines: list[Any]) -> str:
    if not lines:
        return f"**{recipe_name}**\n\n*(no components yet)*"
    rows = [f"**{recipe_name}**", ""]
    for idx, line in enumerate(lines):
        branch = "└─" if idx == len(lines) - 1 else "├─"
        waste = f" (+{line.waste_percent:g}% waste)" if line.waste_percent else ""
        rows.append(
            f"{branch} {_line_label(line)}  \n"
            f"{'   ' if idx == len(lines) - 1 else '│  '}"
            f"  {_fmt_qty_unit(line.quantity, line.unit)}{waste}"
        )
    return "\n".join(rows)


def _draft_tree_markdown(
    recipe_name: str,
    draft_lines: list[dict[str, Any]],
    ingredient_names: dict[int, str],
    recipe_names: dict[int, str],
) -> str:
    if not draft_lines:
        return f"**{recipe_name or 'New recipe'}**\n\n*(no components yet)*"
    views: list[rc_svc.RecipeLineView] = []
    for idx, row in enumerate(draft_lines):
        if row["kind"] == "ingredient":
            name = ingredient_names.get(row["ingredient_id"], "?")
            views.append(
                rc_svc.RecipeLineView(
                    id=None,
                    sort_order=idx,
                    ingredient_id=row["ingredient_id"],
                    sub_recipe_id=None,
                    display_name=name,
                    quantity=row["quantity"],
                    unit=row["unit"],
                    waste_percent=row.get("waste_percent", 0.0),
                    notes=None,
                    line_kind="ingredient",
                )
            )
        else:
            name = recipe_names.get(row["sub_recipe_id"], "?")
            views.append(
                rc_svc.RecipeLineView(
                    id=None,
                    sort_order=idx,
                    ingredient_id=None,
                    sub_recipe_id=row["sub_recipe_id"],
                    display_name=name,
                    quantity=row["quantity"],
                    unit=row["unit"],
                    waste_percent=row.get("waste_percent", 0.0),
                    notes=None,
                    line_kind="sub_recipe",
                )
            )
    return _recipe_tree_markdown(recipe_name or "New recipe", views)


def _ingredient_options(
    ingredients: list[rc_svc.IngredientView],
) -> tuple[list[str], dict[str, int]]:
    labels: list[str] = []
    by_label: dict[str, int] = {}
    for ing in ingredients:
        label = f"{ing.name} ({ing.base_unit})"
        labels.append(label)
        by_label[label] = ing.id
    return labels, by_label


def _recipe_options(
    recipes: list[rc_svc.RecipeSummary],
    *,
    exclude_id: int | None = None,
) -> tuple[list[str], dict[str, int]]:
    labels: list[str] = []
    by_label: dict[str, int] = {}
    for rec in recipes:
        if exclude_id is not None and rec.id == exclude_id:
            continue
        label = f"{rec.name} (yields {rec.yield_quantity:g} {rec.yield_unit})"
        labels.append(label)
        by_label[label] = rec.id
    return labels, by_label


def render_recipe_ingredients(session) -> None:
    erp = _erp()
    if not erp._can("view_recipe_costing"):
        st.warning(erp._t("rc.no_permission"))
        return

    company_id = erp.current_company_required()
    user = erp._current_user() or {}
    user_id = user.get("id", 0)
    settings = erp.load_settings()
    currency = settings.get("currency", "TRY")
    can_manage = erp._can("manage_recipe_costing")

    st.markdown(
        section_header_html(erp._t("rc.ingredients.title")),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("rc.ingredients.subtitle"))

    c1, c2 = st.columns([2, 1])
    with c1:
        search = st.text_input(erp._t("rc.filter.search"), key="rc_ing_search")
    with c2:
        active_filter = st.selectbox(
            erp._t("rc.filter.status"),
            options=("all", "active", "inactive"),
            format_func=lambda x: erp._t(f"rc.filter.{x}"),
            key="rc_ing_status",
        )
    active_only = None
    if active_filter == "active":
        active_only = True
    elif active_filter == "inactive":
        active_only = False

    ingredients = rc_svc.list_ingredients(
        session,
        company_id,
        search=search or None,
        active_only=active_only,
    )

    if ingredients:
        df = pd.DataFrame(
            [
                {
                    erp._t("rc.col.name"): ing.name,
                    erp._t("rc.col.dimension"): ing.base_dimension,
                    erp._t("rc.col.unit"): ing.base_unit,
                    erp._t("rc.col.cost"): _fmt_money(currency, ing.cost_per_base_unit),
                    erp._t("rc.col.status"): erp._t("rc.status.active")
                    if ing.is_active
                    else erp._t("rc.status.inactive"),
                }
                for ing in ingredients
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(erp._t("rc.ingredients.empty"))

    if can_manage:
        with st.expander(erp._t("rc.ingredients.add"), expanded=not ingredients):
            with st.form("rc_add_ingredient"):
                name = st.text_input(erp._t("rc.field.name"), key="rc_add_ing_name")
                dim = st.selectbox(
                    erp._t("rc.field.dimension"),
                    options=rc_svc.list_dimensions(),
                    format_func=lambda d: erp._t(f"rc.dimension.{d}"),
                    key="rc_add_ing_dim",
                )
                base_unit = rc_svc.CANONICAL_BASE_UNIT[dim]
                st.caption(erp._t("rc.field.base_unit_caption", unit=base_unit))
                cost = erp.amount_input(erp._t("rc.field.cost_per_unit"), key="rc_add_ing_cost")
                notes = st.text_area(erp._t("rc.field.notes"), key="rc_add_ing_notes")
                if st.form_submit_button(erp._t("rc.action.add_ingredient"), type="primary"):
                    result = rc_svc.create_ingredient(
                        session,
                        company_id,
                        name,
                        dim,
                        base_unit,
                        cost or 0.0,
                        user_id,
                        notes=notes or None,
                        performed_by=user.get("username"),
                    )
                    if result.ok:
                        st.success(erp._t("rc.msg.ingredient_saved"))
                        st.rerun()
                    else:
                        st.error(result.error)

        ing_labels = [ing.name for ing in ingredients]
        if ing_labels:
            selected_name = st.selectbox(
                erp._t("rc.ingredients.edit_select"),
                options=ing_labels,
                key="rc_ing_edit_pick",
            )
            selected = next(i for i in ingredients if i.name == selected_name)
            with st.form("rc_edit_ingredient"):
                edit_name = st.text_input(
                    erp._t("rc.field.name"),
                    value=selected.name,
                    key="rc_edit_ing_name",
                )
                edit_notes = st.text_area(
                    erp._t("rc.field.notes"),
                    value=selected.notes or "",
                    key="rc_edit_ing_notes",
                )
                edit_cost = erp.amount_input(
                    erp._t("rc.field.cost_per_unit"),
                    key="rc_edit_ing_cost",
                    default=selected.cost_per_base_unit,
                )
                c_save, c_deact, c_act = st.columns(3)
                save = c_save.form_submit_button(erp._t("rc.action.save"), type="primary")
                deactivate = c_deact.form_submit_button(erp._t("rc.action.deactivate"))
                activate = c_act.form_submit_button(erp._t("rc.action.activate"))
                if save:
                    meta = rc_svc.update_ingredient(
                        session,
                        company_id,
                        selected.id,
                        edit_name,
                        user_id,
                        notes=edit_notes or None,
                        performed_by=user.get("username"),
                    )
                    if not meta.ok:
                        st.error(meta.error)
                    else:
                        cost_res = rc_svc.update_ingredient_cost(
                            session,
                            company_id,
                            selected.id,
                            edit_cost or 0.0,
                            user_id,
                            performed_by=user.get("username"),
                        )
                        if cost_res.ok:
                            st.success(erp._t("rc.msg.ingredient_saved"))
                            st.rerun()
                        else:
                            st.error(cost_res.error)
                elif deactivate:
                    res = rc_svc.deactivate_ingredient(
                        session,
                        company_id,
                        selected.id,
                        user_id,
                        performed_by=user.get("username"),
                    )
                    if res.ok:
                        st.success(erp._t("rc.msg.ingredient_deactivated"))
                        st.rerun()
                    else:
                        st.error(res.error)
                elif activate:
                    res = rc_svc.activate_ingredient(
                        session,
                        company_id,
                        selected.id,
                        user_id,
                        performed_by=user.get("username"),
                    )
                    if res.ok:
                        st.success(erp._t("rc.msg.ingredient_activated"))
                        st.rerun()
                    else:
                        st.error(res.error)


def _load_draft_from_recipe(detail: rc_svc.RecipeDetail | None) -> list[dict[str, Any]]:
    if detail is None:
        return []
    draft: list[dict[str, Any]] = []
    for line in detail.lines:
        if line.line_kind == "ingredient":
            draft.append(
                {
                    "kind": "ingredient",
                    "ingredient_id": line.ingredient_id,
                    "quantity": line.quantity,
                    "unit": line.unit,
                    "waste_percent": line.waste_percent,
                }
            )
        else:
            draft.append(
                {
                    "kind": "sub_recipe",
                    "sub_recipe_id": line.sub_recipe_id,
                    "quantity": line.quantity,
                    "unit": line.unit,
                    "waste_percent": line.waste_percent,
                }
            )
    return draft


def render_recipe_recipes(session) -> None:
    erp = _erp()
    if not erp._can("view_recipe_costing"):
        st.warning(erp._t("rc.no_permission"))
        return

    company_id = erp.current_company_required()
    user = erp._current_user() or {}
    user_id = user.get("id", 0)
    can_manage = erp._can("manage_recipe_costing")

    st.markdown(
        section_header_html(erp._t("rc.recipes.title")),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("rc.recipes.subtitle"))

    search = st.text_input(erp._t("rc.filter.search"), key="rc_rec_search")
    recipes = rc_svc.list_recipes(session, company_id, search=search or None)
    ingredients = rc_svc.list_ingredients(session, company_id, active_only=True)
    ing_names = {i.id: i.name for i in ingredients}
    rec_names = {r.id: r.name for r in recipes}

    pick_options = [_NEW_RECIPE_KEY] + [r.id for r in recipes]
    pick_labels = {0: erp._t("rc.recipes.new")}
    for r in recipes:
        pick_labels[r.id] = r.name

    selected_id = st.selectbox(
        erp._t("rc.recipes.select"),
        options=pick_options,
        format_func=lambda rid: pick_labels.get(rid, str(rid)),
        key="rc_recipe_pick",
    )

    if st.session_state.get("rc_loaded_recipe_id") != selected_id:
        detail = (
            rc_svc.get_recipe(session, company_id, selected_id)
            if selected_id != _NEW_RECIPE_KEY
            else None
        )
        st.session_state["rc_loaded_recipe_id"] = selected_id
        st.session_state["rc_draft_lines"] = _load_draft_from_recipe(detail)
        st.session_state["rc_recipe_name"] = detail.name if detail else ""
        st.session_state["rc_yield_qty"] = detail.yield_quantity if detail else 1.0
        st.session_state["rc_yield_unit"] = detail.yield_unit if detail else "each"
        st.session_state["rc_recipe_desc"] = detail.description if detail else ""

    recipe_name = st.text_input(
        erp._t("rc.field.recipe_name"),
        key="rc_recipe_name",
    )
    c1, c2 = st.columns(2)
    with c1:
        yield_qty = st.number_input(
            erp._t("rc.field.yield_qty"),
            min_value=0.01,
            step=0.5,
            key="rc_yield_qty",
        )
    with c2:
        yield_unit = st.selectbox(
            erp._t("rc.field.yield_unit"),
            options=("each", "g", "kg", "ml", "l", "dozen"),
            key="rc_yield_unit",
        )
    st.text_area(erp._t("rc.field.notes"), key="rc_recipe_desc")

    draft_lines: list[dict[str, Any]] = list(st.session_state.get("rc_draft_lines", []))
    st.markdown(_draft_tree_markdown(recipe_name, draft_lines, ing_names, rec_names))

    if can_manage:
        st.markdown(f"#### {erp._t('rc.recipes.components')}")
        for idx, row in enumerate(draft_lines):
            col_a, col_b, col_c = st.columns([5, 2, 1])
            if row["kind"] == "ingredient":
                label = ing_names.get(row["ingredient_id"], "?")
            else:
                label = rec_names.get(row["sub_recipe_id"], "?")
            col_a.markdown(f"**{label}** — {_fmt_qty_unit(row['quantity'], row['unit'])}")
            if col_c.button(erp._t("rc.action.remove"), key=f"rc_rm_{idx}"):
                draft_lines.pop(idx)
                st.session_state["rc_draft_lines"] = draft_lines
                st.rerun()

        with st.expander(erp._t("rc.recipes.add_line"), expanded=True):
            line_kind = st.radio(
                erp._t("rc.field.line_kind"),
                options=("ingredient", "sub_recipe"),
                format_func=lambda k: erp._t(f"rc.line_kind.{k}"),
                horizontal=True,
                key="rc_add_line_kind",
            )
            units = _DEFAULT_LINE_UNITS
            pick = None
            ing_opts: list[str] = []
            sub_opts: list[str] = []

            if line_kind == "ingredient":
                ing_opts, ing_map = _ingredient_options(ingredients)
                if not ing_opts:
                    st.caption(erp._t("rc.recipes.need_ingredients"))
                else:
                    pick = st.selectbox(
                        erp._t("rc.field.pick_ingredient"), ing_opts, key="rc_add_ing_pick"
                    )
                    ing = next(i for i in ingredients if i.id == ing_map[pick])
                    dim_units = rc_svc.units_for_dimension(ing.base_dimension)
                    units = dim_units or (ing.base_unit,)
            else:
                sub_opts, sub_map = _recipe_options(
                    recipes,
                    exclude_id=selected_id if selected_id != _NEW_RECIPE_KEY else None,
                )
                if not sub_opts:
                    st.caption(erp._t("rc.recipes.need_sub_recipes"))
                else:
                    pick = st.selectbox(
                        erp._t("rc.field.pick_sub_recipe"), sub_opts, key="rc_add_sub_pick"
                    )
                    sub_id = sub_map[pick]
                    sub_detail = rc_svc.get_recipe(session, company_id, sub_id)
                    if sub_detail:
                        dim_units = rc_svc.units_for_dimension(sub_detail.yield_dimension)
                        units = dim_units or (sub_detail.yield_unit,)
                    else:
                        units = ("each",)

            q_col, u_col, w_col = st.columns(3)
            with q_col:
                qty = st.number_input(erp._t("rc.field.quantity"), min_value=0.01, step=1.0, key="rc_add_qty")
            with u_col:
                unit = st.selectbox(erp._t("rc.field.unit"), options=units, key="rc_add_unit")
            with w_col:
                waste = st.number_input(
                    erp._t("rc.field.waste_pct"),
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key="rc_add_waste",
                )
            if st.button(erp._t("rc.action.add_line"), key="rc_add_line_btn"):
                if line_kind == "ingredient" and ing_opts:
                    draft_lines.append(
                        {
                            "kind": "ingredient",
                            "ingredient_id": ing_map[pick],
                            "quantity": qty,
                            "unit": unit,
                            "waste_percent": waste,
                        }
                    )
                    st.session_state["rc_draft_lines"] = draft_lines
                    st.rerun()
                elif line_kind == "sub_recipe" and sub_opts:
                    draft_lines.append(
                        {
                            "kind": "sub_recipe",
                            "sub_recipe_id": sub_map[pick],
                            "quantity": qty,
                            "unit": unit,
                            "waste_percent": waste,
                        }
                    )
                    st.session_state["rc_draft_lines"] = draft_lines
                    st.rerun()

        if st.button(erp._t("rc.action.save_recipe"), type="primary", key="rc_save_recipe"):
            line_inputs: list[rc_svc.RecipeLineInput] = []
            for sort_idx, row in enumerate(draft_lines):
                if row["kind"] == "ingredient":
                    line_inputs.append(
                        rc_svc.RecipeLineInput(
                            quantity=row["quantity"],
                            unit=row["unit"],
                            ingredient_id=row["ingredient_id"],
                            waste_percent=row.get("waste_percent", 0.0),
                            sort_order=sort_idx,
                        )
                    )
                else:
                    line_inputs.append(
                        rc_svc.RecipeLineInput(
                            quantity=row["quantity"],
                            unit=row["unit"],
                            sub_recipe_id=row["sub_recipe_id"],
                            waste_percent=row.get("waste_percent", 0.0),
                            sort_order=sort_idx,
                        )
                    )
            result = rc_svc.save_recipe(
                session,
                company_id,
                recipe_name,
                yield_qty,
                yield_unit,
                line_inputs,
                user_id,
                recipe_id=selected_id if selected_id != _NEW_RECIPE_KEY else None,
                description=st.session_state.get("rc_recipe_desc") or None,
                performed_by=user.get("username"),
            )
            if result.ok:
                st.success(erp._t("rc.msg.recipe_saved"))
                st.session_state["rc_loaded_recipe_id"] = None
                st.session_state["rc_recipe_pick"] = result.record_id
                st.rerun()
            else:
                st.error(result.error)


def render_recipe_cost_breakdown(session) -> None:
    erp = _erp()
    if not erp._can("view_recipe_costing"):
        st.warning(erp._t("rc.no_permission"))
        return

    company_id = erp.current_company_required()
    settings = erp.load_settings()
    currency = settings.get("currency", "TRY")

    st.markdown(
        section_header_html(erp._t("rc.cost.title")),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("rc.cost.subtitle"))

    recipes = rc_svc.list_recipes(session, company_id, active_only=True)
    if not recipes:
        st.info(erp._t("rc.cost.no_recipes"))
        return

    options = [r.id for r in recipes]
    labels = {r.id: r.name for r in recipes}
    recipe_id = st.selectbox(
        erp._t("rc.cost.select_recipe"),
        options=options,
        format_func=lambda rid: labels[rid],
        key="rc_cost_recipe",
    )

    breakdown = rc_svc.compute_recipe_cost(session, company_id, recipe_id)
    if breakdown is None:
        st.warning(erp._t("rc.cost.not_found"))
        return

    st.markdown(_recipe_tree_markdown(breakdown.recipe_name, breakdown.line_costs))

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric(erp._t("rc.cost.total"), _fmt_money(currency, breakdown.total_cost))
    m2.metric(
        erp._t("rc.cost.per_portion"),
        _fmt_money(currency, breakdown.cost_per_yield_unit),
    )
    m3.metric(
        erp._t("rc.cost.yield"),
        f"{breakdown.yield_quantity:g} {breakdown.yield_unit}",
    )

    if breakdown.warnings:
        for warn in breakdown.warnings:
            st.warning(warn)

    rows = []
    for line in breakdown.line_costs:
        rows.append(
            {
                erp._t("rc.col.component"): line.name,
                erp._t("rc.col.quantity"): _fmt_qty_unit(line.quantity, line.unit),
                erp._t("rc.field.waste_pct"): f"{line.waste_percent:g}%",
                erp._t("rc.col.line_cost"): _fmt_money(currency, line.line_cost),
            }
        )
        for warn in line.warnings:
            st.caption(f"⚠ {line.name}: {warn}")

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:g}%"


def render_recipe_menu_items(session) -> None:
    erp = _erp()
    if not erp._can("view_recipe_costing"):
        st.warning(erp._t("rc.no_permission"))
        return

    company_id = erp.current_company_required()
    user = erp._current_user() or {}
    user_id = user.get("id", 0)
    settings = erp.load_settings()
    currency = settings.get("currency", "TRY")
    can_manage = erp._can("manage_recipe_costing")

    st.markdown(
        section_header_html(erp._t("rc.menu.title")),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("rc.menu.subtitle"))

    target_fc = st.number_input(
        erp._t("rc.menu.target_food_cost"),
        min_value=1.0,
        max_value=99.0,
        value=rc_svc.DEFAULT_TARGET_FOOD_COST_PCT,
        step=1.0,
        key="rc_menu_target_fc",
    )

    profitability = rc_svc.list_menu_profitability(
        session,
        company_id,
        active_only=True,
        target_food_cost_pct=target_fc,
    )

    if profitability:
        df = pd.DataFrame(
            [
                {
                    erp._t("rc.col.name"): row.menu_item_name,
                    erp._t("rc.col.recipe"): row.recipe_name,
                    erp._t("rc.col.recipe_cost"): _fmt_money(currency, row.recipe_cost),
                    erp._t("rc.col.price_gross"): _fmt_money(
                        currency, row.selling_price_gross
                    ),
                    erp._t("rc.col.price_net"): _fmt_money(currency, row.selling_price_net),
                    erp._t("rc.col.gross_profit"): _fmt_money(currency, row.gross_profit),
                    erp._t("rc.col.food_cost_pct"): _fmt_pct(row.food_cost_pct),
                    erp._t("rc.col.markup_pct"): _fmt_pct(row.markup_pct),
                    erp._t("rc.col.suggested_price"): _fmt_money(
                        currency, row.suggested_price_gross
                    ),
                }
                for row in profitability
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        for row in profitability:
            for warn in row.warnings:
                st.caption(f"⚠ {row.menu_item_name}: {warn}")
    else:
        st.info(erp._t("rc.menu.empty"))

    if not can_manage:
        return

    recipes = rc_svc.list_recipes(session, company_id, active_only=True)
    if not recipes:
        st.warning(erp._t("rc.menu.need_recipes"))
        return

    rec_labels, rec_by_label = _recipe_options(recipes)

    with st.expander(erp._t("rc.menu.add"), expanded=not profitability):
        with st.form("rc_add_menu_item"):
            name = st.text_input(erp._t("rc.field.name"), key="rc_add_menu_name")
            recipe_label = st.selectbox(
                erp._t("rc.menu.link_recipe"),
                options=rec_labels,
                key="rc_add_menu_recipe",
            )
            notes = st.text_area(erp._t("rc.field.notes"), key="rc_add_menu_notes")
            price = erp.amount_input(erp._t("rc.menu.price_gross"), key="rc_add_menu_price")
            if st.form_submit_button(erp._t("rc.action.add_menu_item"), type="primary"):
                result = rc_svc.create_menu_item(
                    session,
                    company_id,
                    name,
                    rec_by_label[recipe_label],
                    user_id,
                    notes=notes or None,
                    performed_by=user.get("username"),
                )
                if not result.ok:
                    st.error(result.error)
                else:
                    if price and price > 0:
                        price_res = rc_svc.set_menu_price(
                            session,
                            company_id,
                            result.record_id,
                            price,
                            user_id,
                            performed_by=user.get("username"),
                        )
                        if not price_res.ok:
                            st.error(price_res.error)
                            return
                    st.success(erp._t("rc.msg.menu_item_saved"))
                    st.rerun()

    menu_items = rc_svc.list_menu_items(session, company_id, active_only=None)
    if menu_items:
        pick_labels = [m.name for m in menu_items]
        selected_name = st.selectbox(
            erp._t("rc.menu.edit_select"),
            options=pick_labels,
            key="rc_menu_edit_pick",
        )
        selected = next(m for m in menu_items if m.name == selected_name)
        current_recipe_label = next(
            (lbl for lbl, rid in rec_by_label.items() if rid == selected.recipe_id),
            rec_labels[0],
        )
        with st.form("rc_edit_menu_item"):
            edit_name = st.text_input(
                erp._t("rc.field.name"),
                value=selected.name,
                key="rc_edit_menu_name",
            )
            edit_recipe = st.selectbox(
                erp._t("rc.menu.link_recipe"),
                options=rec_labels,
                index=rec_labels.index(current_recipe_label)
                if current_recipe_label in rec_labels
                else 0,
                key="rc_edit_menu_recipe",
            )
            edit_notes = st.text_area(
                erp._t("rc.field.notes"),
                value=selected.notes or "",
                key="rc_edit_menu_notes",
            )
            edit_price = erp.amount_input(
                erp._t("rc.menu.price_gross"),
                key="rc_edit_menu_price",
                default=selected.current_price_gross,
            )
            c_save, c_price, c_deact = st.columns(3)
            save = c_save.form_submit_button(erp._t("rc.action.save"), type="primary")
            set_price = c_price.form_submit_button(erp._t("rc.action.set_price"))
            deactivate = c_deact.form_submit_button(erp._t("rc.action.deactivate"))
            if save:
                res = rc_svc.update_menu_item(
                    session,
                    company_id,
                    selected.id,
                    edit_name,
                    rec_by_label[edit_recipe],
                    user_id,
                    notes=edit_notes or None,
                    performed_by=user.get("username"),
                )
                if res.ok:
                    st.success(erp._t("rc.msg.menu_item_saved"))
                    st.rerun()
                else:
                    st.error(res.error)
            elif set_price:
                if edit_price is None or edit_price < 0:
                    st.error(erp._t("rc.menu.price_required"))
                else:
                    res = rc_svc.set_menu_price(
                        session,
                        company_id,
                        selected.id,
                        edit_price,
                        user_id,
                        performed_by=user.get("username"),
                    )
                    if res.ok:
                        st.success(erp._t("rc.msg.price_saved"))
                        st.rerun()
                    else:
                        st.error(res.error)
            elif deactivate:
                res = rc_svc.deactivate_menu_item(
                    session,
                    company_id,
                    selected.id,
                    user_id,
                    performed_by=user.get("username"),
                )
                if res.ok:
                    st.success(erp._t("rc.msg.menu_item_deactivated"))
                    st.rerun()
                else:
                    st.error(res.error)
