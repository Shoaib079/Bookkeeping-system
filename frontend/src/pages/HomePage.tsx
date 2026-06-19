import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { errorMessageFromCatch } from "../lib/api/apiError";
import { getReadSession } from "../lib/api/session";
import type {
  CompaniesResponse,
  MeResponse,
  ProfitLossResponse,
} from "../lib/api/types";

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

export function HomePage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const range = useMemo(() => monthToDateRange(), []);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [companies, setCompanies] = useState<CompaniesResponse | null>(null);
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
        const [meData, companiesData, plData] = await Promise.all([
          apiGet<MeResponse>("/auth/me", { session, companyScoped: false }),
          apiGet<CompaniesResponse>("/auth/companies", {
            session,
            companyScoped: false,
          }),
          apiGet<ProfitLossResponse>(
            `/api/v1/reports/profit-loss?start_date=${range.start}&end_date=${range.end}`,
            { session, companyScoped: true },
          ),
        ]);
        if (!cancelled) {
          setMe(meData);
          setCompanies(companiesData);
          setProfitLoss(plData);
        }
      } catch (err) {
        if (!cancelled) {
          const detail = errorMessageFromCatch(
            err,
            "Failed to load dashboard data.",
          );
          setError(detail);
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

  const activeCompany = companies?.companies.find(
    (row) => row.company_id === session?.companyId,
  );

  return (
    <section className="erp-home-page">
      <header className="erp-page-header">
        <h1>Home</h1>
        <p className="erp-page-header__meta">Read-only dashboard (P1 API)</p>
      </header>

      {!session ? <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} /> : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {session && me ? (
        <div className="erp-home-grid">
          <article className="erp-card">
            <h2>User</h2>
            <p>{me.display_name ?? me.username}</p>
            <p className="erp-muted">@{me.username}</p>
          </article>
          <article className="erp-card">
            <h2>Company</h2>
            <p>{activeCompany?.company_name ?? `ID ${session.companyId}`}</p>
            {activeCompany ? (
              <p className="erp-muted">Role: {activeCompany.role}</p>
            ) : null}
          </article>
          {profitLoss ? (
            <>
              <article className="erp-card">
                <h2>Income (MTD)</h2>
                <p className="erp-kpi">{formatMoney(profitLoss.total_income)}</p>
              </article>
              <article className="erp-card">
                <h2>Expenses (MTD)</h2>
                <p className="erp-kpi">
                  {formatMoney(profitLoss.total_expenses)}
                </p>
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
            </>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
