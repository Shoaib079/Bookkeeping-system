import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { ProfitLossResponse } from "../lib/api/types";

function yearStartIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-01-01`;
}

function todayIso(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function ProfitLossPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [startDate, setStartDate] = useState(
    searchParams.get("start_date") ?? yearStartIso(),
  );
  const [endDate, setEndDate] = useState(
    searchParams.get("end_date") ?? todayIso(),
  );
  const [report, setReport] = useState<ProfitLossResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session || !startDate || !endDate) {
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<ProfitLossResponse>(
          `/api/v1/reports/profit-loss?start_date=${startDate}&end_date=${endDate}`,
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
              : "Failed to load profit & loss.";
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
  }, [session, startDate, endDate]);

  function handleFilterSubmit(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (startDate) {
      next.set("start_date", startDate);
    }
    if (endDate) {
      next.set("end_date", endDate);
    }
    setSearchParams(next);
  }

  return (
    <section className="erp-profit-loss-page">
      <header className="erp-page-header">
        <h1>Profit & Loss</h1>
        <p className="erp-page-header__meta">
          Read-only statement via `/api/v1/reports/profit-loss`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      <form className="erp-ledger-filters" onSubmit={handleFilterSubmit}>
        <label>
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            required
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={!session}>
          Apply
        </button>
      </form>

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {report ? (
        <div className="erp-home-grid">
          <article className="erp-card">
            <h2>Total income</h2>
            <p className="erp-kpi">{formatMoney(report.total_income)}</p>
          </article>
          <article className="erp-card">
            <h2>Total expenses</h2>
            <p className="erp-kpi">{formatMoney(report.total_expenses)}</p>
          </article>
          <article className="erp-card">
            <h2>Net</h2>
            <p
              className={`erp-kpi ${report.is_profit ? "erp-kpi--positive" : "erp-kpi--negative"}`}
            >
              {formatMoney(report.net)}
            </p>
            {report.margin_pct !== null ? (
              <p className="erp-muted">Margin: {report.margin_pct.toFixed(1)}%</p>
            ) : null}
          </article>
          <article className="erp-card">
            <h2>Period</h2>
            <p>
              {report.start_date} → {report.end_date}
            </p>
          </article>
        </div>
      ) : null}
    </section>
  );
}
