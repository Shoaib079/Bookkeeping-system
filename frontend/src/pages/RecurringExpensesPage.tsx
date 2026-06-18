import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { RecurringExpensesPageResponse } from "../lib/api/types";

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function RecurringExpensesPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<RecurringExpensesPageResponse | null>(null);
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
        const data = await apiGet<RecurringExpensesPageResponse>(
          "/api/v1/recurring-expenses",
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
              : "Failed to load recurring expenses.";
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
    <section className="erp-recurring-expenses-page">
      <header className="erp-page-header">
        <h1>Recurring Expenses</h1>
        <p className="erp-page-header__meta">
          Read-only templates and drafts via `/api/v1/recurring-expenses`
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
            <span>Templates: {page.template_count}</span>
            <span>Pending: {page.pending_count}</span>
            <span>History: {page.history_count}</span>
          </div>

          <h2>Pending drafts</h2>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Template</th>
                  <th>Due</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Method</th>
                </tr>
              </thead>
              <tbody>
                {page.pending_drafts.map((row) => (
                  <tr key={row.id}>
                    <td>{row.template_name}</td>
                    <td>{row.due_date}</td>
                    <td>{row.category}</td>
                    <td>{formatMoney(row.amount)}</td>
                    <td>{row.payment_method}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2>Templates</h2>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Frequency</th>
                  <th>Next due</th>
                  <th>Active</th>
                  <th>Pending</th>
                </tr>
              </thead>
              <tbody>
                {page.templates.map((row) => (
                  <tr key={row.id}>
                    <td>{row.name}</td>
                    <td>{row.category}</td>
                    <td>{formatMoney(row.amount)}</td>
                    <td>{row.frequency}</td>
                    <td>{row.next_due_date}</td>
                    <td>{row.is_active ? "Yes" : "No"}</td>
                    <td>{row.pending_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2>Draft history</h2>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Template</th>
                  <th>Due</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Actioned</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {page.draft_history.map((row) => (
                  <tr key={row.id}>
                    <td>{row.template_name}</td>
                    <td>{row.due_date}</td>
                    <td>{row.category}</td>
                    <td>{formatMoney(row.amount)}</td>
                    <td>{row.status}</td>
                    <td>{row.actioned_at ?? "—"}</td>
                    <td>{row.note ?? "—"}</td>
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
