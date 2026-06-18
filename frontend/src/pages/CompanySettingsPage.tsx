import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { CompanySettingsResponse } from "../lib/api/types";

export function CompanySettingsPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<CompanySettingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<CompanySettingsResponse>(
          "/api/v1/company-settings",
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setPage(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load company settings.";
          setError(detail);
          setPage(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [session]);

  return (
    <section className="erp-company-settings-page">
      <header className="erp-page-header">
        <h1>Company Settings</h1>
        <p className="erp-page-header__meta">
          Read-only profile snapshot via `/api/v1/company-settings`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {page ? (
        <>
          <div className="erp-ledger-summary">
            <span>Slug: {page.slug}</span>
            <span>Wizard: {page.wizard_complete ? "Complete" : "Incomplete"}</span>
            <span>Currency: {page.base_currency}</span>
            <span>Tax: {page.tax_rate}%</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <tbody>
                <tr>
                  <th scope="row">Display name</th>
                  <td>{page.display_name}</td>
                </tr>
                <tr>
                  <th scope="row">Legal name</th>
                  <td>{page.legal_name ?? "—"}</td>
                </tr>
                <tr>
                  <th scope="row">Email</th>
                  <td>{page.email ?? "—"}</td>
                </tr>
                <tr>
                  <th scope="row">Phone</th>
                  <td>{page.phone ?? "—"}</td>
                </tr>
                <tr>
                  <th scope="row">Tax number</th>
                  <td>{page.tax_number ?? "—"}</td>
                </tr>
                <tr>
                  <th scope="row">Address</th>
                  <td>{page.address ?? "—"}</td>
                </tr>
                <tr>
                  <th scope="row">Logo URL</th>
                  <td>{page.logo_url ?? "—"}</td>
                </tr>
                <tr>
                  <th scope="row">Fiscal year</th>
                  <td>{page.fiscal_year_label}</td>
                </tr>
                <tr>
                  <th scope="row">Document language</th>
                  <td>{page.document_language}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}
