import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { TransactionHistoryResponse } from "../lib/api/types";

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

export function TransactionLedgerPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [startDate, setStartDate] = useState(
    searchParams.get("start_date") ?? yearStartIso(),
  );
  const [endDate, setEndDate] = useState(
    searchParams.get("end_date") ?? todayIso(),
  );
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [typeFilter, setTypeFilter] = useState(
    searchParams.get("type_filter") ?? "all",
  );
  const [page, setPage] = useState<TransactionHistoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session || !startDate || !endDate) {
      return;
    }
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
      type_filter: typeFilter,
    });
    if (search.trim()) {
      params.set("search", search.trim());
    }

    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<TransactionHistoryResponse>(
          `/api/v1/transactions?${params.toString()}`,
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
              : "Failed to load transaction ledger.";
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
  }, [session, startDate, endDate, search, typeFilter]);

  function handleFilterSubmit(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (startDate) {
      next.set("start_date", startDate);
    }
    if (endDate) {
      next.set("end_date", endDate);
    }
    if (search.trim()) {
      next.set("search", search.trim());
    }
    if (typeFilter) {
      next.set("type_filter", typeFilter);
    }
    setSearchParams(next);
  }

  return (
    <section className="erp-transaction-ledger-page">
      <header className="erp-page-header">
        <h1>Transaction Ledger</h1>
        <p className="erp-page-header__meta">
          Read-only history via `/api/v1/transactions`
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
        <label>
          Search
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label>
          Type
          <select
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value)}
          >
            <option value="all">All</option>
            <option value="Sale">Sale</option>
            <option value="Expense">Expense</option>
            <option value="Purchase">Purchase</option>
            <option value="Banking">Banking</option>
            <option value="Payable">Payable</option>
          </select>
        </label>
        <button type="submit" disabled={!session}>
          Apply filters
        </button>
      </form>

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {page ? (
        <>
          <div className="erp-ledger-summary">
            <span>Rows: {page.row_count}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Reference</th>
                  <th>Party</th>
                  <th>Amount</th>
                  <th>Method</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={`${row.source_type}-${row.source_id}`}>
                    <td>{row.date}</td>
                    <td>{row.type}</td>
                    <td>{row.reference}</td>
                    <td>{row.party}</td>
                    <td>{formatMoney(row.amount)}</td>
                    <td>{row.method}</td>
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
