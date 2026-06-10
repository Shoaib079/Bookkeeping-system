"""DEV-AUTH-01 — development banner gated on ERP_DEV_MODE env flag."""

from __future__ import annotations

import importlib
import inspect

import app as erp
from registry.i18n import t


def test_development_mode_defaults_off_without_env(monkeypatch):
    monkeypatch.delenv("ERP_DEV_MODE", raising=False)
    importlib.reload(erp)
    assert erp.DEV_MODE is False
    assert erp.DEVELOPMENT_MODE is False


def test_development_mode_on_when_env_set(monkeypatch):
    monkeypatch.setenv("ERP_DEV_MODE", "1")
    importlib.reload(erp)
    assert erp.DEV_MODE is True
    assert erp.DEVELOPMENT_MODE is True
    monkeypatch.delenv("ERP_DEV_MODE", raising=False)
    importlib.reload(erp)


def test_dev_banner_uses_i18n_not_hardcoded_english():
    src = inspect.getsource(erp.main)
    assert '_t("dev.banner")' in src
    assert "DEV_MODE and not is_setup01_active" in src


def test_dev_banner_tr_resolves():
    assert t("dev.banner", "tr") != "dev.banner"
    assert "GELİŞTİRME MODU AKTİF" in t("dev.banner", "tr")
