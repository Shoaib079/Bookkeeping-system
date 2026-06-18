import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { JournalEntriesListResponse } from "../lib/api/types";

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function JournalEntriesPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<JournalEntriesListResponse | null>(null);
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
        const data = await apiGet<JournalEntriesListResponse>(
          "/api/v1/journal-entries",
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
              : "Failed to load journal entries.";
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
    <section className="erp-journal-entries-page">
      <header className="erp-page-header">
        <h1>Journal Entries</h1>
        <p className="erp-page-header__meta">
          Read-only posted entries via `/api/v1/journal-entries`
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
            <span>Entries: {page.row_count}</span>
          </div>
          {page.rows.map((entry) => (
            <article key={entry.id} className="erp-journal-entry-card">
              <header>
                <h2>
                  {entry.entry_date} — {entry.description}
                </h2>
                {entry.reference_type ? (
                  <p className="erp-page-header__meta">
                    Reference: {entry.reference_type}
                    {entry.reference_id != null ? ` #${entry.reference_id}` : ""}
                  </p>
                ) : null}
              </header>
              <div className="erp-table-wrap">
                <table className="erp-table">
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Debit</th>
                      <th>Credit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entry.lines.map((line) => (
                      <tr key={line.id}>
                        <td>
                          {line.account_code
                            ? `${line.account_code} — ${line.account_name}`
                            : line.account_name}
                        </td>
                        <td>{line.debit > 0 ? formatMoney(line.debit) : ""}</td>
                        <td>{line.credit > 0 ? formatMoney(line.credit) : ""}</td>
                      </tr>
                    ))}
                    <tr>
                      <td>
                        <strong>Total</strong>
                      </td>
                      <td>
                        <strong>{formatMoney(entry.total_debit)}</strong>
                      </td>
                      <td>
                        <strong>{formatMoney(entry.total_credit)}</strong>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </article>
          ))}
        </>
      ) : null}
    </section>
  );
}
