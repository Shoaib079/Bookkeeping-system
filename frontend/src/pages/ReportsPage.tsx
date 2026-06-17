import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { ProfitLossResponse } from "../lib/api/types";

function monthToDateRange(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const pad = (value: number) => String(value).padStart(2, "0");
  const fmt = (date: Date) =>
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  return { start: fmt(start), end: fmt(now) };
}

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const REPORT_LINKS = [
  { label: "Profit & Loss", to: "/reports/profit-loss" },
  { label: "Balance Sheet", to: "/reports/balance-sheet" },
  { label: "Cash Flow", to: "/reports/cash-flow" },
  { label: "Transaction Ledger", to: "/transactions/ledger" },
  { label: "Receivables", to: "/receivables" },
  { label: "Payables", to: "/payables" },
];

export function ReportsPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const range = useMemo(() => monthToDateRange(), []);
  const [profitLoss, setProfitLoss] = useState<ProfitLossResponse | null>(null);
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
        const data = await apiGet<ProfitLossResponse>(
          `/api/v1/reports/profit-loss?start_date=${range.start}&end_date=${range.end}`,
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setProfitLoss(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load reports summary.";
          setError(detail);
          setProfitLoss(null);
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
    <section className="erp-reports-page">
      <header className="erp-page-header">
        <h1>Reports</h1>
        <p className="erp-page-header__meta">
          Read-only hub — summary via `/api/v1/reports/profit-loss`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {profitLoss ? (
        <div className="erp-home-grid">
          <article className="erp-card">
            <h2>Income (MTD)</h2>
            <p className="erp-kpi">{formatMoney(profitLoss.total_income)}</p>
          </article>
          <article className="erp-card">
            <h2>Expenses (MTD)</h2>
            <p className="erp-kpi">{formatMoney(profitLoss.total_expenses)}</p>
          </article>
          <article className="erp-card">
            <h2>Net (MTD)</h2>
            <p
              className={`erp-kpi ${profitLoss.is_profit ? "erp-kpi--positive" : "erp-kpi--negative"}`}
            >
              {formatMoney(profitLoss.net)}
            </p>
            <p className="erp-muted">
              {range.start} → {range.end}
            </p>
          </article>
        </div>
      ) : null}

      <nav className="erp-reports-hub-links">
        <h2>Statements & lists</h2>
        <ul>
          {REPORT_LINKS.map((link) => (
            <li key={link.to}>
              <Link to={link.to}>{link.label}</Link>
            </li>
          ))}
        </ul>
      </nav>
    </section>
  );
}
