import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { LedgerPageResponse } from "../lib/api/types";

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function LedgerPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [accountId, setAccountId] = useState(
    searchParams.get("account_id") ?? "",
  );
  const [startDate, setStartDate] = useState(
    searchParams.get("start_date") ?? "",
  );
  const [endDate, setEndDate] = useState(searchParams.get("end_date") ?? "");
  const [ledger, setLedger] = useState<LedgerPageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    const parsedAccountId = Number(accountId);
    if (!Number.isFinite(parsedAccountId) || parsedAccountId < 1) {
      setLedger(null);
      return;
    }

    const params = new URLSearchParams({ account_id: String(parsedAccountId) });
    if (startDate) {
      params.set("start_date", startDate);
    }
    if (endDate) {
      params.set("end_date", endDate);
    }

    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<LedgerPageResponse>(
          `/api/v1/ledger?${params.toString()}`,
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setLedger(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load ledger.";
          setError(detail);
          setLedger(null);
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
  }, [session, accountId, startDate, endDate]);

  function handleFilterSubmit(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (accountId) {
      next.set("account_id", accountId);
    }
    if (startDate) {
      next.set("start_date", startDate);
    }
    if (endDate) {
      next.set("end_date", endDate);
    }
    setSearchParams(next);
  }

  return (
    <section className="erp-ledger-page">
      <header className="erp-page-header">
        <h1>General Ledger</h1>
        <p className="erp-page-header__meta">
          Read-only journal lines via `/api/v1/ledger`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      <form className="erp-ledger-filters" onSubmit={handleFilterSubmit}>
        <label>
          Account id
          <input
            type="number"
            min={1}
            value={accountId}
            onChange={(event) => setAccountId(event.target.value)}
            required
          />
        </label>
        <label>
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </label>
        <button type="submit" disabled={!session}>
          Apply filters
        </button>
      </form>

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {ledger ? (
        <>
          <div className="erp-ledger-summary">
            <span>Rows: {ledger.row_count}</span>
            <span>Opening: {formatMoney(ledger.opening_balance)}</span>
            <span>Closing: {formatMoney(ledger.closing_balance)}</span>
            <span>Type: {ledger.account_type}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Reference</th>
                  <th>Description</th>
                  <th>Debit</th>
                  <th>Credit</th>
                  <th>Balance</th>
                </tr>
              </thead>
              <tbody>
                {ledger.rows.map((row, index) => (
                  <tr key={`${row.date}-${row.reference}-${index}`}>
                    <td>{row.date}</td>
                    <td>{row.reference}</td>
                    <td>{row.description}</td>
                    <td>{row.debit ? formatMoney(row.debit) : ""}</td>
                    <td>{row.credit ? formatMoney(row.credit) : ""}</td>
                    <td>{formatMoney(row.running_balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {session && !accountId ? (
        <p className="erp-muted">Enter an account id to load ledger lines.</p>
      ) : null}
    </section>
  );
}
