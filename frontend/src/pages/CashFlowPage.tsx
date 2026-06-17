import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { CashFlowResponse } from "../lib/api/types";

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

export function CashFlowPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [startDate, setStartDate] = useState(
    searchParams.get("start_date") ?? yearStartIso(),
  );
  const [endDate, setEndDate] = useState(
    searchParams.get("end_date") ?? todayIso(),
  );
  const [report, setReport] = useState<CashFlowResponse | null>(null);
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
        const data = await apiGet<CashFlowResponse>(
          `/api/v1/reports/cash-flow?start_date=${startDate}&end_date=${endDate}`,
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
              : "Failed to load cash flow.";
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
    <section className="erp-cash-flow-page">
      <header className="erp-page-header">
        <h1>Cash Flow</h1>
        <p className="erp-page-header__meta">
          Read-only statement via `/api/v1/reports/cash-flow`
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
        <>
          <div className="erp-ledger-summary">
            <span>Net operating: {formatMoney(report.net_op)}</span>
            <span>Net financing: {formatMoney(report.net_fin)}</span>
            <span>Net total: {formatMoney(report.net_total)}</span>
            <span>Cash accounts: {report.has_cash_accounts ? "Yes" : "No"}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Section</th>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Inflow</th>
                  <th>Outflow</th>
                </tr>
              </thead>
              <tbody>
                {report.operating_rows.map((row, index) => (
                  <tr key={`op-${row.date}-${index}`}>
                    <td>Operating</td>
                    <td>{row.date}</td>
                    <td>{row.type}</td>
                    <td>{row.description}</td>
                    <td>{row.inflow ? formatMoney(row.inflow) : ""}</td>
                    <td>{row.outflow ? formatMoney(row.outflow) : ""}</td>
                  </tr>
                ))}
                {report.financing_rows.map((row, index) => (
                  <tr key={`fin-${row.date}-${index}`}>
                    <td>Financing</td>
                    <td>{row.date}</td>
                    <td>{row.type}</td>
                    <td>{row.description}</td>
                    <td>{row.inflow ? formatMoney(row.inflow) : ""}</td>
                    <td>{row.outflow ? formatMoney(row.outflow) : ""}</td>
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
