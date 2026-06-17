import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { CoaListResponse } from "../lib/api/types";

export function ChartOfAccountsPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<CoaListResponse | null>(null);
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
        const data = await apiGet<CoaListResponse>("/api/v1/chart-of-accounts", {
          session,
          companyScoped: true,
        });
        if (!cancelled) {
          setPage(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load chart of accounts.";
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
  }, [session]);

  return (
    <section className="erp-coa-page">
      <header className="erp-page-header">
        <h1>Chart of Accounts</h1>
        <p className="erp-page-header__meta">
          Read-only COA list via `/api/v1/chart-of-accounts`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {page ? (
        <>
          <div className="erp-ledger-summary">
            <span>Accounts: {page.row_count}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Currency</th>
                  <th>Active</th>
                  <th>Ledger</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.account_code}</td>
                    <td>{row.account_name}</td>
                    <td>{row.account_type}</td>
                    <td>{row.currency ?? "—"}</td>
                    <td>{row.is_active ? "Yes" : "No"}</td>
                    <td>
                      <Link
                        to={`/books/general-ledger?account_id=${row.id}`}
                      >
                        View ledger
                      </Link>
                    </td>
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
