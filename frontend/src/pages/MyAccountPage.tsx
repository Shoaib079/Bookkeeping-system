import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { MyAccountResponse } from "../lib/api/types";

export function MyAccountPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<MyAccountResponse | null>(null);
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
        const data = await apiGet<MyAccountResponse>("/api/v1/my-account", {
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
              : "Failed to load account profile.";
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
    <section className="erp-my-account-page">
      <header className="erp-page-header">
        <h1>My Account</h1>
        <p className="erp-page-header__meta">
          Read-only profile snapshot via `/api/v1/my-account`
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
            <span>@{page.username}</span>
            <span>Role: {page.company_role ?? "—"}</span>
            <span>Company: {page.active_company_name ?? "—"}</span>
            <span>Member since: {page.member_since ?? "—"}</span>
            <span>Last login: {page.last_login ?? "—"}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Display name</td>
                  <td>{page.display_name ?? "—"}</td>
                </tr>
                <tr>
                  <td>Email</td>
                  <td>{page.email ?? "—"}</td>
                </tr>
                <tr>
                  <td>Phone</td>
                  <td>{page.phone ?? "—"}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <h2>Company access</h2>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Role</th>
                  <th>Default</th>
                </tr>
              </thead>
              <tbody>
                {page.companies.map((row) => (
                  <tr key={row.company_id}>
                    <td>{row.company_name}</td>
                    <td>{row.role}</td>
                    <td>{row.is_default ? "Yes" : "No"}</td>
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
