import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { ReconHealthResponse } from "../lib/api/types";

function formatMoney(value: number, currency: string): string {
  return `${currency} ${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function SectionMetrics({
  title,
  currency,
  section,
}: {
  title: string;
  currency: string;
  section: ReconHealthResponse["accounts_receivable"];
}) {
  return (
    <article className="erp-recon-health-section">
      <h2>{title}</h2>
      <div className="erp-ledger-summary">
        <span>GL: {formatMoney(section.gl_balance, currency)}</span>
        <span>Subledger: {formatMoney(section.subledger_balance, currency)}</span>
        <span>Difference: {formatMoney(section.difference, currency)}</span>
        <span>Status: {section.status}</span>
      </div>
    </article>
  );
}

export function ReconHealthPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<ReconHealthResponse | null>(null);
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
        const data = await apiGet<ReconHealthResponse>(
          "/api/v1/reconciliation/health",
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
              : "Failed to load reconciliation health.";
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
    <section className="erp-recon-health-page">
      <header className="erp-page-header">
        <h1>Reconciliation Health</h1>
        <p className="erp-page-header__meta">
          Read-only GL integrity checks via `/api/v1/reconciliation/health`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {page ? (
        <>
          <SectionMetrics
            title="Accounts Receivable"
            currency={page.currency}
            section={page.accounts_receivable}
          />
          <SectionMetrics
            title="Accounts Payable"
            currency={page.currency}
            section={page.accounts_payable}
          />

          {page.credit_card ? (
            <article className="erp-recon-health-section">
              <h2>Credit Card Payable</h2>
              <div className="erp-ledger-summary">
                <span>GL: {formatMoney(page.credit_card.gl_balance, page.currency)}</span>
                <span>
                  Subledger: {formatMoney(page.credit_card.subledger_total, page.currency)}
                </span>
                <span>
                  Difference: {formatMoney(page.credit_card.difference, page.currency)}
                </span>
                <span>Status: {page.credit_card.status}</span>
              </div>
            </article>
          ) : null}

          <article className="erp-recon-health-section">
            <h2>Bank Accounts</h2>
            {page.bank_accounts.length > 0 ? (
              <div className="erp-table-wrap">
                <table className="erp-table">
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Currency</th>
                      <th>Stored</th>
                      <th>Derived</th>
                      <th>Difference</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {page.bank_accounts.map((row) => (
                      <tr key={row.account_id}>
                        <td>{row.name}</td>
                        <td>{row.currency ?? "—"}</td>
                        <td>{formatMoney(row.stored_balance, page.currency)}</td>
                        <td>{formatMoney(row.derived_balance, page.currency)}</td>
                        <td>{formatMoney(row.difference, page.currency)}</td>
                        <td>{row.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>No bank accounts.</p>
            )}
          </article>

          <article className="erp-recon-health-section">
            <h2>Chart of Accounts Cache</h2>
            <p>
              {page.coa_cache_clean
                ? "Cache matches journal-derived balances."
                : `${page.coa_drift_rows.length} account(s) with cache drift.`}
            </p>
            {!page.coa_cache_clean ? (
              <div className="erp-table-wrap">
                <table className="erp-table">
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Account</th>
                      <th>Cached</th>
                      <th>Expected</th>
                      <th>Delta</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {page.coa_drift_rows.map((row) => (
                      <tr key={row.account_code}>
                        <td>{row.account_code}</td>
                        <td>{row.account_name}</td>
                        <td>{formatMoney(row.cached_balance, page.currency)}</td>
                        <td>{formatMoney(row.expected_balance, page.currency)}</td>
                        <td>{formatMoney(row.delta, page.currency)}</td>
                        <td>{row.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </article>
        </>
      ) : null}
    </section>
  );
}
