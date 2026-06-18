import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { EodClosesListResponse } from "../lib/api/types";

function monthToDateRange(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const pad = (value: number) => String(value).padStart(2, "0");
  const fmt = (date: Date) =>
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  return { start: fmt(start), end: fmt(now) };
}

export function EodClosePage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const range = useMemo(() => monthToDateRange(), []);
  const [page, setPage] = useState<EodClosesListResponse | null>(null);
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
        const data = await apiGet<EodClosesListResponse>(
          `/api/v1/end-of-day-closes?start_date=${range.start}&end_date=${range.end}`,
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
              : "Failed to load end-of-day closes.";
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
  }, [session, range.end, range.start]);

  return (
    <section className="erp-eod-close-page">
      <header className="erp-page-header">
        <h1>End-of-Day Close</h1>
        <p className="erp-page-header__meta">
          Read-only close history via `/api/v1/end-of-day-closes`
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
            <span>
              Range: {page.start_date ?? "—"} → {page.end_date ?? "—"}
            </span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Closed by</th>
                  <th>Closed at</th>
                  <th>Warnings</th>
                  <th>Sales</th>
                  <th>Expenses</th>
                  <th>Net cash</th>
                  <th>Recon</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.date}</td>
                    <td>{row.status}</td>
                    <td>{row.closed_by_name ?? "—"}</td>
                    <td>{row.closed_at}</td>
                    <td>{row.had_warnings ? "Yes" : "No"}</td>
                    <td>{row.total_sales}</td>
                    <td>{row.total_expenses}</td>
                    <td>{row.net_cash_movement}</td>
                    <td>{row.recon_status ?? "—"}</td>
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
