"""Tests for Phase 15 i18n."""

from registry.i18n import normalize_locale, nav_display, page_title, t, td, translate


def test_normalize_locale():
    assert normalize_locale("tr") == "tr"
    assert normalize_locale("tr-TR") == "tr"
    assert normalize_locale("xx") == "en"
    assert normalize_locale(None) == "en"


def test_translate_english_default():
    assert t("common.save", "en") == "Save"
    assert t("common.save", "tr") == "Kaydet"


def test_translate_fallback_to_key():
    assert t("nonexistent.key", "en") == "nonexistent.key"


def test_translate_interpolation():
    assert "Acme" in t("wizard.complete", "en", vertical="Acme", mode="Standard")


def test_document_locale_independent():
    assert td("report.generated", "tr", date="01.06.2026").startswith("Oluşturulma")


def test_nav_display_keeps_emoji_and_translates():
    assert nav_display("🏠 Home", "en") == "🏠 Home"
    assert nav_display("🏠 Home", "tr") == "🏠 Ana Sayfa"


def test_page_title_without_emoji():
    assert page_title("💼 Sales", "en") == "Sales"
    assert page_title("💼 Sales", "tr") == "Satışlar"


def test_transactional_sales_tr():
    assert t("sales.record_btn", "tr") == "Satışı Kaydet"


def test_transactional_phase15c_tr():
    assert t("vendor.add_btn", "tr") == "Tedarikçi Ekle"
    assert t("purchase.add_btn", "tr") == "Satın Alma Ekle"
    assert t("customer.add_btn", "tr") == "Müşteri Ekle"


def test_purchase_gl_i18n_maps_inventory():
    from registry.locales.i18n_maps import PURCHASE_GL_I18N

    assert PURCHASE_GL_I18N["Inventory"] == "purchase.gl.inventory"
    assert t(PURCHASE_GL_I18N["Rent"], "tr") == "Kira"


def test_transactional_phase15d_tr():
    assert t("payable.add_btn", "tr") == "Borç Ekle"
    assert t("receivable.metric.open_invoices", "tr") == "Açık Faturalar"
    assert t("bank.add_txn_btn", "tr") == "İşlem Ekle"


def test_transactional_phase15e_tr():
    assert t("reports.exec.pnl", "tr") == "Gelir Tablosu"
    assert t("trial.balanced", "tr") == "DENGELİ"
    assert t("aging.days_1_30", "tr") == "1–30 Gün"


def test_aging_bucket_i18n_map():
    from registry.locales.i18n_maps import AGING_BUCKET_I18N

    assert t(AGING_BUCKET_I18N["90+ Days"], "tr") == "90+ Gün"


def test_transactional_phase15f_tr():
    assert t("bs.title", "tr") == "Bilanço"
    assert t("cf.title", "tr") == "Nakit Akış Tablosu"
    assert t("eod.close_day", "tr") == "Günü Kapat"
    assert t("recon.submit", "tr") == "Onaya Gönder"


def test_transactional_phase15g_tr():
    # Column headers
    assert t("col.section", "tr") == "Bölüm"
    assert t("col.inflow", "tr") == "Giriş"
    assert t("col.outflow", "tr") == "Çıkış"
    assert t("col.period", "tr") == "Dönem"
    assert t("col.total", "tr") == "Toplam"
    # P&L / BS / CF export labels
    assert t("pnl.net_profit_loss", "tr") == "Net Kâr / Zarar"
    assert t("bs.equity_gl", "tr") == "Özkaynak (GL)"
    assert t("bs.total_equity_ni", "tr") == "Toplam Özkaynak + NI"
    assert t("cf.net_operating", "tr") == "Net Faaliyet"
    assert t("cf.net_financing", "tr") == "Net Finansman"
    # Fiscal period KPIs
    assert t("fiscal.periods", "tr") == "Dönemler"
    assert t("fiscal.allocations", "tr") == "Dağıtımlar"
    assert t("fiscal.net_income", "tr") == "Net Gelir"
    assert t("fiscal.revenue", "tr") == "Gelir"
    # Management report dynamic labels
    assert "Güncel" in t("rpt.kpi.current_period", "tr", frm="01.01", to="31.01")
    assert "Önceki" in t("rpt.kpi.prior_period", "tr", frm="01.12", to="31.12")
    # Management report empty-state messages
    assert t("rpt.no_outstanding_ar", "tr") == "Açık alacak yok."
    assert t("rpt.no_outstanding_ap", "tr") == "Açık borç yok."
    assert t("rpt.capital_contributions", "tr") == "Sermaye Katılımları"
    assert t("rpt.all_days_closed", "tr") == "Bu aralıktaki tüm günler kapatılmış."


def test_recon_status_i18n_map():
    from registry.locales.i18n_maps import RECON_STATUS_I18N

    assert t(RECON_STATUS_I18N["pending_approval"], "tr") == "Onay Bekliyor"


def test_transactional_phase15i_tr():
    # Static labels
    assert t("attach.attach_file_btn", "tr") == "📎 Dosya Ekle"
    assert t("field.transaction_detail", "tr") == "İşlem Detayı"
    assert t("je.manual_entry", "tr") == "Manuel Yevmiye Kaydı"
    assert t("coa.balance_summary", "tr") == "Bakiye Özeti"
    assert t("sales.void_section", "tr") == "Satışı İptal Et"
    assert t("adv.expander.fiscal", "tr") == "📅 Mali Dönemler"
    assert t("backup.backup_now_btn", "tr") == "💾 Şimdi Yedekle"
    assert t("header.notifications_help", "tr") == "Bildirimler"
    assert t("cat.no_categories_ph", "tr") == "Henüz kategori yok"


def test_transactional_phase15i_interpolation():
    # Numeric format specs must interpolate without raising in both locales
    assert " (+2 daha)" == t("yec.err_more_suffix", "tr", count=2)
    assert "%75.00" in t("yec.check_shares_total", "tr", pct=75.0)
    assert t("txn.save_btn", "en", type="Sale") == "✅ Save Sale"
    assert t("txn.save_btn", "tr", type="Satış") == "✅ Satış Kaydet"
    msg = t("fiscal.not_allocated_net", "en", currency="TRY", amount=1234.5)
    assert "TRY 1,234.50" in msg
    assert t("bank.csv_import_btn", "tr", count=5) == "✅ 5 yeni işlemi içe aktar"


def test_transactional_phase15j_tr():
    # Reconciliation health, partner accounts, audit log
    assert t("rh.title", "tr") == "Mutabakat Sağlığı"
    assert t("rh.sec_ar", "tr") == "A · Alacak Hesapları"
    assert t("audit.title_banner", "tr") == "Denetim Günlüğü"
    assert t("partner.page_banner", "tr") == "Ortak Hesapları"
    assert t("partner.status_active", "tr") == "✅ Aktif"
    assert t("company_setup.base_currency_help", "tr") == "Tüm raporlar bu para birimini kullanır."


def test_payment_and_movement_maps():
    from registry.locales.i18n_maps import (
        PAYMENT_METHOD_I18N,
        PARTNER_MOVEMENT_TYPE_I18N,
    )

    assert t(PAYMENT_METHOD_I18N["Cash"], "tr") == "Nakit"
    assert t(PAYMENT_METHOD_I18N["Bank"], "tr") == "Banka"
    assert t(PAYMENT_METHOD_I18N["Credit"], "tr") == "Kredili"
    assert t(PAYMENT_METHOD_I18N["Card"], "tr") == "Kart"
    assert t(PARTNER_MOVEMENT_TYPE_I18N["CapitalContribution"], "tr") == "Sermaye Katılımı"
    assert t(PARTNER_MOVEMENT_TYPE_I18N["AdvanceOffset"], "tr") == "Avans Mahsubu"


def test_transactional_phase15k_txn_row_values():
    # Composite Type values + statuses shown in Transaction History rows/exports
    assert t("txnrow.cash_sale", "tr") == "Nakit Satış"
    assert t("txnrow.credit_sale", "tr") == "Kredili Satış"
    assert t("txnrow.bank_deposit", "tr") == "Banka Yatırma"
    assert t("txnrow.purchase", "tr") == "Alış"
    assert t("txnrow.corrected", "tr") == "Düzeltildi"
    assert t("status.void", "tr") == "İPTAL"
    assert t("status.recorded", "tr") == "Kaydedildi"
    assert t("status.active", "tr") == "Aktif"
    # English users keep English
    assert t("txnrow.cash_sale", "en") == "Cash Sale"
    assert t("status.void", "en") == "VOID"
    # Export headers
    assert t("col.reference", "tr") == "Referans"
    assert t("col.party", "tr") == "Taraf"
    assert t("col.created_by", "tr") == "Oluşturan"


def test_opening_balances_table_columns_tr():
    from registry.i18n import t

    assert t("col.stored_balance", "tr") == "Kayıtlı Bakiye"
    assert t("ob.col.ob_posted", "tr") == "AB Kaydedildi"
    assert t("ob.col.ob_date", "tr") == "AB Tarihi"
    assert t("ob.col.current_qty", "tr") == "Mevcut Miktar"
    assert t("ob.product_label", "tr") == "Ürün"
    assert t("ob.customer_label", "tr") == "Müşteri"
    assert t("ob.vendor_label", "tr") == "Tedarikçi"


def test_localize_df_recovers_stale_key_column_names(monkeypatch):
    import pandas as pd

    import app as app_mod

    monkeypatch.setattr(app_mod, "_ui_locale", lambda: "tr")
    df = pd.DataFrame([{"ob.col.ob_posted": "✅", "ob.col.ob_amount": "100"}])
    out = app_mod._localize_df(df)
    assert "AB Kaydedildi" in out.columns
    assert "AB Tutarı" in out.columns


def test_translate_falls_back_to_live_transactional_catalog():
    """Keys added only to transactional.py still resolve after MESSAGES was built."""
    from registry.locales import messages as msg_mod
    from registry.i18n import translate

    saved = msg_mod.MESSAGES["tr"].pop("ob.col.ob_amount", None)
    try:
        assert translate("ob.col.ob_amount", "tr") == "AB Tutarı"
    finally:
        if saved is not None:
            msg_mod.MESSAGES["tr"]["ob.col.ob_amount"] = saved


def test_audit_log_filter_labels_tr():
    from registry.locales.i18n_maps import AUDIT_ACTION_I18N, AUDIT_ENTITY_I18N

    assert t(AUDIT_ACTION_I18N["Void"], "tr") == "İptal"
    assert t(AUDIT_ACTION_I18N["PeriodClose"], "tr") == "Dönem kapat"
    assert t(AUDIT_ENTITY_I18N["CompanyUser"], "tr") == "Şirket üyesi"
    assert t(AUDIT_ENTITY_I18N["DailyCashReconciliation"], "tr") == "Günlük kasa mutabakatı"


def test_transactional_phase15l_admin_tr():
    from registry.locales.i18n_maps import COMPANY_ROLE_I18N

    assert t("members.role.owner", "tr") == "Sahip"
    assert t(COMPANY_ROLE_I18N["cashier"], "tr") == "Kasiyer"
    assert t("backup.confirm_restore", "tr") == "✅ Geri Yüklemeyi Onayla"
    assert t("backup.never", "tr") == "Hiç"
    assert t("adv.title", "tr") == "Gelişmiş Modüller"
    assert t("settings.section.categories", "tr") == "🏷 Kategorileri Yönet"
    assert t("col.username", "tr") == "Kullanıcı Adı"
    assert t("myaccount.2fa_title", "tr") == "İki Faktörlü Kimlik Doğrulama"


def test_phase15j_interpolation():
    msg = t("partner.shares_warning", "tr", pct=66.5)
    assert "%66.50" in msg
    msg = t("rh.coa_drift_warn", "en", count=3)
    assert "3 account(s)" in msg
    msg = t("audit.entries_count", "tr", count=12)
    assert "12 kayıt" in msg
    msg = t("partner.cap_caption", "en", currency="TRY", amount=5000.0)
    assert "Capital: TRY 5,000.00" == msg
