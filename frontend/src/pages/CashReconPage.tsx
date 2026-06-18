import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { CashReconciliationsListResponse } from "../lib/api/types";

function monthToDateRange(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const pad = (value: number) => String(value).padStart(2, "0");
  const fmt = (date: Date) =>
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  return { start: fmt(start), end: fmt(now) };
}

export function CashReconPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const range = useMemo(() => monthToDateRange(), []);
  const [page, setPage] = useState<CashReconciliationsListResponse | null>(null);
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
        const data = await apiGet<CashReconciliationsListResponse>(
          `/api/v1/cash-reconciliations?start_date=${range.start}&end_date=${range.end}`,
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
              : "Failed to load cash reconciliations.";
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
    <section className="erp-cash-recon-page">
      <header className="erp-page-header">
        <h1>Cash Reconciliation</h1>
        <p className="erp-page-header__meta">
          Read-only reconciliation history via `/api/v1/cash-reconciliations`
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
            <span>Records: {page.row_count}</span>
            <span>
              Range: {page.start_date ?? "—"} → {page.end_date ?? "—"}
            </span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Account</th>
                  <th>Expected</th>
                  <th>Actual</th>
                  <th>Difference</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Submitted by</th>
                  <th>Approved by</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.date}</td>
                    <td>{row.cash_account_name ?? "—"}</td>
                    <td>{row.expected_cash}</td>
                    <td>{row.actual_cash}</td>
                    <td>{row.difference}</td>
                    <td>{row.variance_type}</td>
                    <td>{row.status}</td>
                    <td>{row.submitted_by_name ?? "—"}</td>
                    <td>{row.approved_by_name ?? "—"}</td>
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
