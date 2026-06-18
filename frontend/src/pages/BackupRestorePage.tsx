import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { BackupStatusResponse } from "../lib/api/types";

export function BackupRestorePage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<BackupStatusResponse | null>(null);
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
        const data = await apiGet<BackupStatusResponse>("/api/v1/backup-status", {
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
              : "Failed to load backup status.";
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
    <section className="erp-backup-restore-page">
      <header className="erp-page-header">
        <h1>Backup &amp; Restore</h1>
        <p className="erp-page-header__meta">
          Read-only backup inventory via `/api/v1/backup-status`
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
            <span>Stored: {page.row_count}</span>
            <span>Last backup: {page.last_backup ?? "Never"}</span>
            <span>DB size: {page.db_size_kb} KB</span>
            <span>
              Cloud folder: {page.cloud_folder ?? "—"}
              {page.cloud_folder
                ? page.cloud_folder_exists
                  ? " (ok)"
                  : " (missing)"
                : ""}
            </span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Size (KB)</th>
                  <th>Modified</th>
                  <th>Attachments zip</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.name}>
                    <td>{row.name}</td>
                    <td>{row.size_kb}</td>
                    <td>{row.modified}</td>
                    <td>{row.has_uploads_zip ? "Yes" : "No"}</td>
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
