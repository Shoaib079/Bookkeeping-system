import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { TrialBalanceResponse } from "../lib/api/types";

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function TrialBalancePage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [statement, setStatement] = useState<TrialBalanceResponse | null>(null);
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
        const data = await apiGet<TrialBalanceResponse>(
          "/api/v1/reports/trial-balance",
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
              : "Failed to load trial balance.";
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
  }, [session]);

  return (
    <section className="erp-trial-balance-page">
      <header className="erp-page-header">
        <h1>Trial Balance</h1>
        <p className="erp-page-header__meta">
          Read-only debit/credit check via `/api/v1/reports/trial-balance`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {statement ? (
        <>
          <div className="erp-ledger-summary">
            <span>Accounts: {statement.row_count}</span>
            <span>TB debits: {formatMoney(statement.total_debit)}</span>
            <span>TB credits: {formatMoney(statement.total_credit)}</span>
            <span>
              GL status: {statement.gl_balanced ? "Balanced" : "Unbalanced"}
            </span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Account</th>
                  <th>Type</th>
                  <th>Debit</th>
                  <th>Credit</th>
                </tr>
              </thead>
              <tbody>
                {statement.rows.map((row) => (
                  <tr key={row.account_code}>
                    <td>{row.account_code}</td>
                    <td>{row.account_name}</td>
                    <td>{row.account_type}</td>
                    <td>{row.debit > 0 ? formatMoney(row.debit) : ""}</td>
                    <td>{row.credit > 0 ? formatMoney(row.credit) : ""}</td>
                  </tr>
                ))}
                <tr>
                  <td colSpan={3}>
                    <strong>Total</strong>
                  </td>
                  <td>
                    <strong>{formatMoney(statement.total_debit)}</strong>
                  </td>
                  <td>
                    <strong>{formatMoney(statement.total_credit)}</strong>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="erp-ledger-summary">
            <span>GL debits: {formatMoney(statement.gl_total_debit)}</span>
            <span>GL credits: {formatMoney(statement.gl_total_credit)}</span>
            {!statement.gl_balanced ? (
              <span>Difference: {formatMoney(statement.gl_difference)}</span>
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  );
}
