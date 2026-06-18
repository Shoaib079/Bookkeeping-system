import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { BudgetVsActualResponse } from "../lib/api/types";

function currentYearMonth(): { year: number; month: number } {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function BudgetPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [searchParams, setSearchParams] = useSearchParams();
  const defaults = currentYearMonth();
  const [year, setYear] = useState(
    Number(searchParams.get("year") ?? defaults.year),
  );
  const [month, setMonth] = useState(
    Number(searchParams.get("month") ?? defaults.month),
  );
  const [report, setReport] = useState<BudgetVsActualResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session || !year || !month) {
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<BudgetVsActualResponse>(
          `/api/v1/reports/budget-vs-actual?year=${year}&month=${month}`,
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setReport(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load budget vs actual.";
          setError(detail);
          setReport(null);
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
  }, [session, year, month]);

  function handleFilterSubmit(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    next.set("year", String(year));
    next.set("month", String(month));
    setSearchParams(next);
  }

  return (
    <section className="erp-budget-page">
      <header className="erp-page-header">
        <h1>Budget vs Actual</h1>
        <p className="erp-page-header__meta">
          Read-only monthly comparison via `/api/v1/reports/budget-vs-actual`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session ? (
        <form className="erp-filter-form" onSubmit={handleFilterSubmit}>
          <label>
            Year
            <input
              type="number"
              min={2020}
              max={2030}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            />
          </label>
          <label>
            Month
            <input
              type="number"
              min={1}
              max={12}
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
            />
          </label>
          <button type="submit">Apply</button>
        </form>
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {report ? (
        <>
          <div className="erp-ledger-summary">
            <span>
              Period: {report.month_start} → {report.month_end}
            </span>
            <span>Budgeted: {formatMoney(report.total_budgeted)}</span>
            <span>Actual: {formatMoney(report.total_actual)}</span>
            <span>Variance: {formatMoney(report.total_variance)}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Account</th>
                  <th>Budgeted</th>
                  <th>Actual</th>
                  <th>Variance</th>
                  <th>Used %</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {report.rows.map((row) => (
                  <tr key={row.account_id}>
                    <td>{row.account_code}</td>
                    <td>{row.account_name}</td>
                    <td>{formatMoney(row.budgeted)}</td>
                    <td>{formatMoney(row.actual)}</td>
                    <td>{formatMoney(row.variance)}</td>
                    <td>{row.used_pct != null ? `${row.used_pct}%` : "—"}</td>
                    <td>{row.status}</td>
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
