import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { BankingReadinessResponse } from "../lib/api/types";

export function BankingReadinessPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [limit, setLimit] = useState(searchParams.get("limit") ?? "10");
  const [readiness, setReadiness] = useState<BankingReadinessResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    const parsedLimit = Number(limit);
    if (!Number.isFinite(parsedLimit) || parsedLimit < 1 || parsedLimit > 100) {
      setReadiness(null);
      return;
    }

    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<BankingReadinessResponse>(
          `/api/v1/banking/readiness?limit=${parsedLimit}`,
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setReadiness(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load banking readiness.";
          setError(detail);
          setReadiness(null);
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
  }, [session, limit]);

  function handleFilterSubmit(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (limit) {
      next.set("limit", limit);
    }
    setSearchParams(next);
  }

  return (
    <section className="erp-banking-readiness-page">
      <header className="erp-page-header">
        <h1>Banking Readiness</h1>
        <p className="erp-page-header__meta">
          Read-only statement imports via `/api/v1/banking/readiness`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      <form className="erp-ledger-filters" onSubmit={handleFilterSubmit}>
        <label>
          Limit (1–100)
          <input
            type="number"
            min={1}
            max={100}
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={!session}>
          Apply
        </button>
      </form>

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {readiness ? (
        <>
          <div className="erp-ledger-summary">
            <span>Imports: {readiness.items.length}</span>
            {readiness.meta ? (
              <span>Limit: {readiness.meta.limit}</span>
            ) : null}
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Period</th>
                  <th>Complete</th>
                  <th>Reconciled</th>
                  <th>Tie-out</th>
                  <th>Remaining</th>
                  <th>Review</th>
                  <th>Blocked</th>
                </tr>
              </thead>
              <tbody>
                {readiness.items.map((item) => (
                  <tr key={item.import_id}>
                    <td>{item.file_name}</td>
                    <td>{item.period}</td>
                    <td>{item.complete ? "Yes" : "No"}</td>
                    <td>{item.reconciled ? "Yes" : "No"}</td>
                    <td>{item.tie_out}</td>
                    <td>{item.remaining_rows}</td>
                    <td>{item.review_pending}</td>
                    <td>{item.failed_blocked}</td>
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
