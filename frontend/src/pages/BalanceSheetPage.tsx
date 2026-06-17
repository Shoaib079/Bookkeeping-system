import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { BalanceSheetResponse } from "../lib/api/types";

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

export function BalanceSheetPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [asOf, setAsOf] = useState(searchParams.get("as_of") ?? todayIso());
  const [statement, setStatement] = useState<BalanceSheetResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session || !asOf) {
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<BalanceSheetResponse>(
          `/api/v1/reports/balance-sheet?as_of=${asOf}`,
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setStatement(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load balance sheet.";
          setError(detail);
          setStatement(null);
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
  }, [session, asOf]);

  function handleFilterSubmit(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (asOf) {
      next.set("as_of", asOf);
    }
    setSearchParams(next);
  }

  return (
    <section className="erp-balance-sheet-page">
      <header className="erp-page-header">
        <h1>Balance Sheet</h1>
        <p className="erp-page-header__meta">
          Read-only statement via `/api/v1/reports/balance-sheet`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      <form className="erp-ledger-filters" onSubmit={handleFilterSubmit}>
        <label>
          As of date
          <input
            type="date"
            value={asOf}
            onChange={(event) => setAsOf(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={!session}>
          Apply
        </button>
      </form>

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {statement ? (
        <div className="erp-home-grid">
          <article className="erp-card">
            <h2>Total assets</h2>
            <p className="erp-kpi">{formatMoney(statement.total_assets)}</p>
          </article>
          <article className="erp-card">
            <h2>Total liabilities</h2>
            <p className="erp-kpi">{formatMoney(statement.total_liabilities)}</p>
          </article>
          <article className="erp-card">
            <h2>Total equity</h2>
            <p className="erp-kpi">{formatMoney(statement.total_equity)}</p>
          </article>
          <article className="erp-card">
            <h2>Balanced</h2>
            <p className="erp-kpi">{statement.balanced ? "Yes" : "No"}</p>
            {!statement.balanced ? (
              <p className="erp-muted">Imbalance: {formatMoney(statement.imbalance)}</p>
            ) : null}
          </article>
        </div>
      ) : null}
    </section>
  );
}
