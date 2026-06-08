"""SETUP-01 company creation wizard — navigation and session helpers."""

from __future__ import annotations

from typing import Any

# Step 0 is "details" (not counted in progress 1–8).
SETUP01_STEP_ORDER: tuple[str, ...] = (
    "details",
    "business",
    "pos",
    "statements",
    "company_cc",
    "inventory",
    "currency",
    "controls",
    "summary",
)

SETUP01_PROGRESS_STEP: dict[str, int] = {
    "business": 1,
    "pos": 2,
    "statements": 3,
    "company_cc": 4,
    "inventory": 5,
    "currency": 6,
    "controls": 7,
    "summary": 8,
}

SETUP01_SESSION_ACTIVE = "setup01_active"
SETUP01_SESSION_STEP = "setup01_step"
SETUP01_SESSION_ANSWERS = "setup01_answers"
SETUP01_SESSION_RETURN = "setup01_return_to"
SETUP01_SESSION_CANCEL_CONFIRM = "setup01_cancel_confirm"
SETUP01_SESSION_JUMP = "setup01_jump_step"
SETUP01_SESSION_CREATING = "setup01_creating"
SETUP01_SESSION_CREATE_ERROR = "setup01_create_error"

POS_NO_CARDS = "no_cards"
POS_IMMEDIATE = "immediate"
POS_LATER = "later"

BUSINESS_RESTAURANT = "restaurant"
BUSINESS_RETAIL = "retail"
BUSINESS_SERVICES = "services"
BUSINESS_OTHER = "other"

CONTROL_RELAXED = "relaxed"
CONTROL_BALANCED = "balanced"
CONTROL_STRICT = "strict"

SETUP01_CONTROL_TO_ACCOUNTING_MODE: dict[str, str] = {
    CONTROL_RELAXED: "flexible",
    CONTROL_BALANCED: "standard",
    CONTROL_STRICT: "strict",
}


def default_setup01_answers() -> dict[str, Any]:
    return {
        "company_name": "",
        "company_legal": "",
        "company_email": "",
        "company_phone": "",
        "business": BUSINESS_RESTAURANT,
        "pos": POS_LATER,
        "statements": "yes",
        "company_cc": "no",
        "inventory": "yes",
        "currency": "no",
        "controls": CONTROL_BALANCED,
        "skipped_steps": [],
    }


def begin_setup01_wizard(*, return_to: str = "picker") -> None:
    """Enter SETUP-01 flow (session only — B1 does not persist settings)."""
    import streamlit as st

    st.session_state[SETUP01_SESSION_ACTIVE] = True
    st.session_state[SETUP01_SESSION_STEP] = "details"
    st.session_state[SETUP01_SESSION_RETURN] = return_to
    answers = default_setup01_answers()
    st.session_state[SETUP01_SESSION_ANSWERS] = answers
    st.session_state["setup01_company_name"] = answers["company_name"]
    st.session_state["setup01_company_legal"] = answers["company_legal"]
    st.session_state["setup01_company_email"] = answers["company_email"]
    st.session_state["setup01_company_phone"] = answers["company_phone"]
    st.session_state.pop(SETUP01_SESSION_CANCEL_CONFIRM, None)
    st.session_state.pop(SETUP01_SESSION_JUMP, None)
    st.session_state.pop(SETUP01_SESSION_CREATING, None)
    st.session_state.pop(SETUP01_SESSION_CREATE_ERROR, None)


def _setup01_keys_to_clear() -> tuple[str, ...]:
    return (
        SETUP01_SESSION_ACTIVE,
        SETUP01_SESSION_STEP,
        SETUP01_SESSION_ANSWERS,
        SETUP01_SESSION_RETURN,
        SETUP01_SESSION_CANCEL_CONFIRM,
        SETUP01_SESSION_JUMP,
        "setup01_company_name",
        "setup01_company_legal",
        "setup01_company_email",
        "setup01_company_phone",
        SETUP01_SESSION_CREATING,
        SETUP01_SESSION_CREATE_ERROR,
    )


def company_create_kwargs_from_answers(answers: dict[str, Any]) -> dict[str, str]:
    """Map Step 0 fields to create_company() keyword arguments."""
    return {
        "name": (answers.get("company_name") or "").strip(),
        "full_name": (answers.get("company_legal") or "").strip(),
        "email": (answers.get("company_email") or "").strip(),
        "phone": (answers.get("company_phone") or "").strip(),
    }


def is_setup01_creating() -> bool:
    import streamlit as st

    return bool(st.session_state.get(SETUP01_SESSION_CREATING))


def discard_setup01_wizard() -> None:
    import streamlit as st

    for key in _setup01_keys_to_clear():
        st.session_state.pop(key, None)


def is_setup01_active() -> bool:
    import streamlit as st

    return bool(st.session_state.get(SETUP01_SESSION_ACTIVE))


def get_setup01_step() -> str:
    import streamlit as st

    step = st.session_state.get(SETUP01_SESSION_STEP, "details")
    return step if step in SETUP01_STEP_ORDER else "details"


def get_setup01_answers() -> dict[str, Any]:
    import streamlit as st

    raw = st.session_state.get(SETUP01_SESSION_ANSWERS)
    if not isinstance(raw, dict):
        return default_setup01_answers()
    base = default_setup01_answers()
    base.update(raw)
    return base


def set_setup01_answers(**kwargs: Any) -> None:
    import streamlit as st

    answers = get_setup01_answers()
    answers.update(kwargs)
    st.session_state[SETUP01_SESSION_ANSWERS] = answers


def pos_skips_statement_step(answers: dict[str, Any]) -> bool:
    return answers.get("pos") == POS_NO_CARDS


def _step_index(step: str) -> int:
    try:
        return SETUP01_STEP_ORDER.index(step)
    except ValueError:
        return 0


def next_setup01_step(current: str, answers: dict[str, Any]) -> str:
    idx = _step_index(current)
    if idx >= len(SETUP01_STEP_ORDER) - 1:
        return "summary"
    nxt = SETUP01_STEP_ORDER[idx + 1]
    if nxt == "statements" and pos_skips_statement_step(answers):
        return next_setup01_step(
            "statements",
            {
                **answers,
                "skipped_steps": list(
                    dict.fromkeys([*(answers.get("skipped_steps") or []), "statements"])
                ),
                "statements": "skipped",
            },
        )
    return nxt


def apply_skip_side_effects(answers: dict[str, Any]) -> dict[str, Any]:
    """Merge skip-branch defaults after advancing past POS (session layer calls this)."""
    if pos_skips_statement_step(answers):
        skipped = list(answers.get("skipped_steps") or [])
        if "statements" not in skipped:
            skipped.append("statements")
        return {**answers, "skipped_steps": skipped, "statements": "skipped"}
    return answers


def prev_setup01_step(current: str, answers: dict[str, Any]) -> str:
    idx = _step_index(current)
    if idx <= 0:
        return "details"
    prev = SETUP01_STEP_ORDER[idx - 1]
    if current == "company_cc" and pos_skips_statement_step(answers):
        return "pos"
    if current == "statements" and pos_skips_statement_step(answers):
        return "pos"
    return prev


def validate_setup01_step(step: str, answers: dict[str, Any]) -> str | None:
    """Return error message or None if step can advance."""
    if step in ("details", "summary"):
        name = (answers.get("company_name") or "").strip()
        if not name:
            return "company_name_required"
    return None


def _summary_business_value(answers: dict[str, Any]) -> str:
    key = {
        BUSINESS_RESTAURANT: "setup01.summary.human.business.restaurant",
        BUSINESS_RETAIL: "setup01.summary.human.business.retail",
        BUSINESS_SERVICES: "setup01.summary.human.business.services",
        BUSINESS_OTHER: "setup01.summary.human.business.other",
    }.get(answers.get("business", BUSINESS_OTHER), "setup01.summary.human.business.other")
    return key


def _summary_pos_value(answers: dict[str, Any]) -> str:
    return {
        POS_IMMEDIATE: "setup01.summary.human.pos.immediate",
        POS_LATER: "setup01.summary.human.pos.later",
        POS_NO_CARDS: "setup01.summary.human.pos.no_cards",
    }.get(answers.get("pos", POS_LATER), "setup01.summary.human.pos.later")


def _summary_statements_value(answers: dict[str, Any]) -> str:
    if pos_skips_statement_step(answers):
        return "setup01.summary.human.statements.skipped"
    return {
        "yes": "setup01.summary.human.statements.yes",
        "no": "setup01.summary.human.statements.no",
        "skipped": "setup01.summary.human.statements.skipped",
    }.get(answers.get("statements", "no"), "setup01.summary.human.statements.no")


def _summary_yesno_value(prefix: str, answers: dict[str, Any], field: str) -> str:
    yn = answers.get(field, "no")
    return f"setup01.summary.human.{prefix}.{'yes' if yn == 'yes' else 'no'}"


def _summary_controls_value(answers: dict[str, Any]) -> str:
    return {
        CONTROL_RELAXED: "setup01.summary.human.controls.relaxed",
        CONTROL_BALANCED: "setup01.summary.human.controls.balanced",
        CONTROL_STRICT: "setup01.summary.human.controls.strict",
    }.get(answers.get("controls", CONTROL_BALANCED), "setup01.summary.human.controls.balanced")


def summary_display_rows(answers: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return (row_key, label_i18n_key, value_i18n_key) for summary UI."""
    rows: list[tuple[str, str, str]] = [
        ("business", "setup01.summary.row.business", _summary_business_value(answers)),
        ("pos", "setup01.summary.row.pos", _summary_pos_value(answers)),
    ]
    if not pos_skips_statement_step(answers):
        rows.append(
            ("statements", "setup01.summary.row.statements", _summary_statements_value(answers))
        )
    rows.extend(
        [
            ("company_cc", "setup01.summary.row.company_cc", _summary_yesno_value("company_cc", answers, "company_cc")),
            ("inventory", "setup01.summary.row.inventory", _summary_yesno_value("inventory", answers, "inventory")),
            ("currency", "setup01.summary.row.currency", _summary_yesno_value("currency", answers, "currency")),
            ("controls", "setup01.summary.row.controls", _summary_controls_value(answers)),
        ]
    )
    return rows


SETUP01_I18N_KEYS: tuple[str, ...] = (
    "setup01.title",
    "setup01.subtitle",
    "setup01.start_btn",
    "setup01.cancel",
    "setup01.cancel_confirm",
    "setup01.discard",
    "setup01.choose_option",
    "setup01.progress.intro",
    "setup01.progress.step",
    "setup01.details.title",
    "setup01.details.lead",
    "setup01.details.about",
    "setup01.business.title",
    "setup01.business.lead",
    "setup01.business.about",
    "setup01.business.hint",
    "setup01.business.restaurant",
    "setup01.business.restaurant.desc",
    "setup01.business.retail",
    "setup01.business.retail.desc",
    "setup01.business.services",
    "setup01.business.services.desc",
    "setup01.business.other",
    "setup01.business.other.desc",
    "setup01.pos.title",
    "setup01.pos.lead",
    "setup01.pos.about",
    "setup01.pos.hint",
    "setup01.pos.immediate",
    "setup01.pos.immediate.desc",
    "setup01.pos.later",
    "setup01.pos.later.desc",
    "setup01.pos.no_cards",
    "setup01.pos.no_cards.desc",
    "setup01.statements.title",
    "setup01.statements.lead",
    "setup01.statements.about",
    "setup01.statements.hint",
    "setup01.statements.yes.desc",
    "setup01.statements.no.desc",
    "setup01.company_cc.title",
    "setup01.company_cc.lead",
    "setup01.company_cc.about",
    "setup01.company_cc.hint",
    "setup01.company_cc.yes.desc",
    "setup01.company_cc.no.desc",
    "setup01.inventory.title",
    "setup01.inventory.lead",
    "setup01.inventory.about",
    "setup01.inventory.hint",
    "setup01.inventory.yes.desc",
    "setup01.inventory.no.desc",
    "setup01.currency.title",
    "setup01.currency.lead",
    "setup01.currency.about",
    "setup01.currency.hint",
    "setup01.currency.yes.desc",
    "setup01.currency.no.desc",
    "setup01.controls.title",
    "setup01.controls.lead",
    "setup01.controls.about",
    "setup01.controls.hint",
    "setup01.controls.relaxed",
    "setup01.controls.relaxed.desc",
    "setup01.controls.balanced",
    "setup01.controls.balanced.desc",
    "setup01.controls.strict",
    "setup01.controls.strict.desc",
    "setup01.common.yes",
    "setup01.common.no",
    "setup01.summary.title",
    "setup01.summary.lead",
    "setup01.summary.edit",
    "setup01.summary.row.company",
    "setup01.summary.row.business",
    "setup01.summary.row.pos",
    "setup01.summary.row.statements",
    "setup01.summary.row.company_cc",
    "setup01.summary.row.inventory",
    "setup01.summary.row.currency",
    "setup01.summary.row.controls",
    "setup01.summary.human.business.restaurant",
    "setup01.summary.human.business.retail",
    "setup01.summary.human.business.services",
    "setup01.summary.human.business.other",
    "setup01.summary.human.pos.immediate",
    "setup01.summary.human.pos.later",
    "setup01.summary.human.pos.no_cards",
    "setup01.summary.human.statements.yes",
    "setup01.summary.human.statements.no",
    "setup01.summary.human.statements.skipped",
    "setup01.summary.human.company_cc.yes",
    "setup01.summary.human.company_cc.no",
    "setup01.summary.human.inventory.yes",
    "setup01.summary.human.inventory.no",
    "setup01.summary.human.currency.yes",
    "setup01.summary.human.currency.no",
    "setup01.summary.human.controls.relaxed",
    "setup01.summary.human.controls.balanced",
    "setup01.summary.human.controls.strict",
    "setup01.create.working",
    "setup01.create.in_progress",
    "setup01.settings_failed",
)


def setup01_vertical_from_answers(answers: dict[str, Any]) -> str:
    """Map Step 1 business type to setup.vertical_template registry value."""
    vertical = answers.get("business", BUSINESS_OTHER)
    if vertical == BUSINESS_OTHER:
        return "general"
    return vertical


def setup01_registry_settings_from_answers(answers: dict[str, Any]) -> dict[str, bool | str]:
    """Map wizard answers to registry-backed company settings (B3)."""
    pos = answers.get("pos", POS_LATER)
    if pos == POS_NO_CARDS:
        card_settlement = False
        reconciliation = False
    elif pos == POS_LATER:
        card_settlement = True
        reconciliation = answers.get("statements", "no") == "yes"
    else:
        card_settlement = False
        reconciliation = answers.get("statements", "no") == "yes"

    return {
        "setup.vertical_template": setup01_vertical_from_answers(answers),
        "banking.card_settlement_enabled": card_settlement,
        "banking.reconciliation_enabled": reconciliation,
        "banking.company_card_enabled": answers.get("company_cc") == "yes",
        "setup.wizard_completed": True,
    }


def setup01_module_flags_from_answers(answers: dict[str, Any]) -> dict[str, bool]:
    """Map Steps 5–6 to module.*.enabled flags (user choice only)."""
    return {
        "inventory": answers.get("inventory") == "yes",
        "foreign_currency": answers.get("currency") == "yes",
    }


def setup01_accounting_mode_from_answers(answers: dict[str, Any]) -> str:
    """Map Step 7 control level to policy.accounting_mode bundle key."""
    return SETUP01_CONTROL_TO_ACCOUNTING_MODE.get(
        answers.get("controls", CONTROL_BALANCED),
        "standard",
    )


def apply_setup01_wizard_settings(session, company_id: int, answers: dict[str, Any]) -> None:
    """Persist SETUP-01 answers to company settings (registry + modules). Commits."""
    from registry.service import save_company_settings_batch, set_company_setting
    from registry.setup_wizard import apply_accounting_mode_bundle

    save_company_settings_batch(
        session,
        company_id,
        setup01_registry_settings_from_answers(answers),
    )
    apply_accounting_mode_bundle(
        session,
        company_id,
        setup01_accounting_mode_from_answers(answers),
    )
    for module_id, enabled in setup01_module_flags_from_answers(answers).items():
        set_company_setting(
            session,
            company_id,
            f"module.{module_id}.enabled",
            enabled,
        )
    session.commit()
