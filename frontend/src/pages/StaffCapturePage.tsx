import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { StaffExpenseDraftsPageResponse } from "../lib/api/types";

function formatMoney(value: number, currency: string): string {
  return `${currency} ${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function StaffCapturePage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<StaffExpenseDraftsPageResponse | null>(null);
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
        const data = await apiGet<StaffExpenseDraftsPageResponse>(
          "/api/v1/staff-expense-drafts",
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
              : "Failed to load staff expense drafts.";
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
    <section className="erp-staff-capture-page">
      <header className="erp-page-header">
        <h1>Staff Expenses</h1>
        <p className="erp-page-header__meta">
          Read-only submissions and inbox via `/api/v1/staff-expense-drafts`
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
            <span>My drafts: {page.my_draft_count}</span>
            <span>Inbox: {page.inbox_count}</span>
          </div>

          {page.can_submit ? (
            <>
              <h2>My submissions</h2>
              <div className="erp-table-wrap">
                <table className="erp-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Amount</th>
                      <th>Method</th>
                      <th>Status</th>
                      <th>Description</th>
                      <th>Submitted</th>
                    </tr>
                  </thead>
                  <tbody>
                    {page.my_drafts.map((row) => (
                      <tr key={row.id}>
                        <td>{row.date}</td>
                        <td>{formatMoney(row.amount, row.currency)}</td>
                        <td>{row.payment_method}</td>
                        <td>{row.status}</td>
                        <td>{row.description || "—"}</td>
                        <td>{row.submitted_at ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}

          {page.can_approve ? (
            <>
              <h2>Approval inbox</h2>
              <div className="erp-table-wrap">
                <table className="erp-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Amount</th>
                      <th>Method</th>
                      <th>Status</th>
                      <th>Description</th>
                      <th>Submitted</th>
                    </tr>
                  </thead>
                  <tbody>
                    {page.inbox_drafts.map((row) => (
                      <tr key={row.id}>
                        <td>{row.date}</td>
                        <td>{formatMoney(row.amount, row.currency)}</td>
                        <td>{row.payment_method}</td>
                        <td>{row.status}</td>
                        <td>{row.description || "—"}</td>
                        <td>{row.submitted_at ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
