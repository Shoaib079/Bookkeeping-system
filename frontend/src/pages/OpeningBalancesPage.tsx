import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { OpeningBalancesStatusResponse } from "../lib/api/types";

function formatMoney(value: number, currency: string): string {
  return `${currency} ${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function OpeningBalancesPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<OpeningBalancesStatusResponse | null>(null);
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
        const data = await apiGet<OpeningBalancesStatusResponse>(
          "/api/v1/opening-balances",
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
              : "Failed to load opening balances status.";
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
    <section className="erp-opening-balances-page">
      <header className="erp-page-header">
        <h1>Opening Balances</h1>
        <p className="erp-page-header__meta">
          Read-only OB status via `/api/v1/opening-balances`
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
            <span>OBE: {formatMoney(page.obe_balance, page.currency)}</span>
            <span>Status: {page.obe_status}</span>
          </div>

          <article className="erp-ob-section">
            <h2>Bank &amp; Cash</h2>
            <div className="erp-table-wrap">
              <table className="erp-table">
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Kind</th>
                    <th>Stored</th>
                    <th>OB Posted</th>
                    <th>OB Date</th>
                    <th>OB Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {page.bank_rows.map((row) => (
                    <tr key={row.id}>
                      <td>{row.name}</td>
                      <td>{row.kind}</td>
                      <td>{formatMoney(row.stored_balance, page.currency)}</td>
                      <td>{row.ob_posted ? "Yes" : "No"}</td>
                      <td>{row.ob_date ?? "—"}</td>
                      <td>
                        {row.ob_amount != null
                          ? formatMoney(row.ob_amount, page.currency)
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="erp-ob-section">
            <h2>Customers</h2>
            <div className="erp-table-wrap">
              <table className="erp-table">
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>OB Posted</th>
                    <th>OB Date</th>
                    <th>OB Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {page.customer_rows.map((row) => (
                    <tr key={row.id}>
                      <td>{row.name}</td>
                      <td>{row.ob_posted ? "Yes" : "No"}</td>
                      <td>{row.ob_date ?? "—"}</td>
                      <td>
                        {row.ob_amount != null
                          ? formatMoney(row.ob_amount, page.currency)
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="erp-ob-section">
            <h2>Vendors</h2>
            <div className="erp-table-wrap">
              <table className="erp-table">
                <thead>
                  <tr>
                    <th>Vendor</th>
                    <th>OB Posted</th>
                    <th>OB Date</th>
                    <th>OB Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {page.vendor_rows.map((row) => (
                    <tr key={row.id}>
                      <td>{row.name}</td>
                      <td>{row.ob_posted ? "Yes" : "No"}</td>
                      <td>{row.ob_date ?? "—"}</td>
                      <td>
                        {row.ob_amount != null
                          ? formatMoney(row.ob_amount, page.currency)
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="erp-ob-section">
            <h2>Owner Capital</h2>
            <p>
              {page.capital.ob_posted
                ? `Posted ${page.capital.ob_date} — ${formatMoney(page.capital.ob_amount ?? 0, page.currency)}`
                : "Not posted"}
            </p>
          </article>

          {page.loan_rows.length > 0 ? (
            <article className="erp-ob-section">
              <h2>Loans</h2>
              <div className="erp-table-wrap">
                <table className="erp-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {page.loan_rows.map((row) => (
                      <tr key={row.journal_entry_id}>
                        <td>{row.entry_date}</td>
                        <td>{row.description}</td>
                        <td>{formatMoney(row.amount, page.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
