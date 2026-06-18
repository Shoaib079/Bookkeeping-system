import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { YearEndClosesListResponse } from "../lib/api/types";

export function YearEndClosePage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<YearEndClosesListResponse | null>(null);
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
        const data = await apiGet<YearEndClosesListResponse>(
          "/api/v1/year-end-closes",
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
              : "Failed to load year-end closes.";
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
    <section className="erp-year-end-close-page">
      <header className="erp-page-header">
        <h1>Year-End Close</h1>
        <p className="erp-page-header__meta">
          Read-only close history via `/api/v1/year-end-closes`
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
            <span>Closes: {page.row_count}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Year</th>
                  <th>Range</th>
                  <th>Closed</th>
                  <th>By</th>
                  <th>Periods</th>
                  <th>Allocations</th>
                  <th>Net income</th>
                  <th>RE at close</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.fiscal_year}</td>
                    <td>
                      {row.start_date} – {row.end_date}
                    </td>
                    <td>{row.closed_at}</td>
                    <td>{row.closed_by_name ?? "—"}</td>
                    <td>{row.period_count}</td>
                    <td>{row.allocation_count}</td>
                    <td>{row.net_income_snapshot}</td>
                    <td>{row.re_balance_at_close}</td>
                    <td>{row.is_void ? "Voided" : "Closed"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}
