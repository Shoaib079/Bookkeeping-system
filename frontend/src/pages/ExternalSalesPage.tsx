import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { ExternalSalesVerificationsListResponse } from "../lib/api/types";

function monthToDateRange(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const pad = (value: number) => String(value).padStart(2, "0");
  const fmt = (date: Date) =>
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  return { start: fmt(start), end: fmt(now) };
}

export function ExternalSalesPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const range = useMemo(() => monthToDateRange(), []);
  const [page, setPage] = useState<ExternalSalesVerificationsListResponse | null>(
    null,
  );
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
        const data = await apiGet<ExternalSalesVerificationsListResponse>(
          `/api/v1/external-sales-verifications?start_date=${range.start}&end_date=${range.end}`,
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
              : "Failed to load external sales verifications.";
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
  }, [session, range.end, range.start]);

  return (
    <section className="erp-external-sales-page">
      <header className="erp-page-header">
        <h1>External Sales Verification</h1>
        <p className="erp-page-header__meta">
          Read-only verification history via `/api/v1/external-sales-verifications`
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
            <span>Records: {page.row_count}</span>
            <span>
              Range: {page.start_date ?? "—"} → {page.end_date ?? "—"}
            </span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Branch</th>
                  <th>External</th>
                  <th>Z-report</th>
                  <th>ERP</th>
                  <th>Variance</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.business_date}</td>
                    <td>{row.source_name}</td>
                    <td>{row.source_type ?? "—"}</td>
                    <td>{row.branch_location ?? "—"}</td>
                    <td>{row.external_total ?? "—"}</td>
                    <td>{row.z_report_total ?? "—"}</td>
                    <td>{row.erp_total ?? "—"}</td>
                    <td>{row.variance_total ?? "—"}</td>
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
