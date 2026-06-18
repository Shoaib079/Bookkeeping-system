import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { CompanyMembersResponse } from "../lib/api/types";

export function MembersPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<CompanyMembersResponse | null>(null);
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
        const data = await apiGet<CompanyMembersResponse>("/api/v1/members", {
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
              : "Failed to load members.";
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
    <section className="erp-members-page">
      <header className="erp-page-header">
        <h1>Members</h1>
        <p className="erp-page-header__meta">
          Read-only company roster via `/api/v1/members`
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
            <span>Total: {page.stats.total}</span>
            <span>Active: {page.stats.active}</span>
            <span>Inactive: {page.stats.inactive}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Display name</th>
                  <th>Role</th>
                  <th>Active</th>
                  <th>Last login</th>
                  <th>Added by</th>
                  <th>Member since</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.membership_id}>
                    <td>{row.username}</td>
                    <td>{row.display_name}</td>
                    <td>{row.role}</td>
                    <td>{row.is_active ? "Yes" : "No"}</td>
                    <td>{row.last_login ?? "—"}</td>
                    <td>{row.invited_by}</td>
                    <td>{row.member_since ?? "—"}</td>
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
