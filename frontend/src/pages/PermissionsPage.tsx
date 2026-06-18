import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type {
  EffectivePermissionsResponse,
  PermissionMembersResponse,
} from "../lib/api/types";

export function PermissionsPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [members, setMembers] = useState<PermissionMembersResponse | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [effective, setEffective] = useState<EffectivePermissionsResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    let cancelled = false;
    async function loadMembers() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<PermissionMembersResponse>(
          "/api/v1/permissions/members",
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setMembers(data);
          setSelectedUserId((current) => current ?? data.rows[0]?.user_id ?? null);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load permission members.";
          setError(detail);
          setMembers(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void loadMembers();
    return () => {
      cancelled = true;
    };
  }, [session]);

  useEffect(() => {
    if (!session || selectedUserId == null) {
      return;
    }
    let cancelled = false;
    async function loadEffective() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<EffectivePermissionsResponse>(
          `/api/v1/permissions/effective?user_id=${selectedUserId}`,
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setEffective(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load effective permissions.";
          setError(detail);
          setEffective(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void loadEffective();
    return () => {
      cancelled = true;
    };
  }, [session, selectedUserId]);

  return (
    <section className="erp-permissions-page">
      <header className="erp-page-header">
        <h1>Permissions</h1>
        <p className="erp-page-header__meta">
          Read-only provenance via `/api/v1/permissions/*`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session && members ? (
        <label className="erp-filter-form">
          Member
          <select
            value={selectedUserId ?? ""}
            onChange={(e) => setSelectedUserId(Number(e.target.value))}
          >
            {members.rows.map((row) => (
              <option key={row.user_id} value={row.user_id}>
                {row.display_name} ({row.username}) — {row.role}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {effective ? (
        <>
          <div className="erp-ledger-summary">
            <span>Role: {effective.role ?? "—"}</span>
            <span>Template: {effective.template_count}</span>
            <span>Grants: {effective.grant_count}</span>
            <span>Denies: {effective.deny_count}</span>
            <span>Effective: {effective.effective_count}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Permission</th>
                  <th>Template</th>
                  <th>Grant</th>
                  <th>Deny</th>
                  <th>Effective</th>
                </tr>
              </thead>
              <tbody>
                {effective.rows.map((row) => (
                  <tr key={row.permission_key}>
                    <td>{row.permission_key}</td>
                    <td>{row.in_template ? "Yes" : "No"}</td>
                    <td>{row.is_grant ? "Yes" : "No"}</td>
                    <td>{row.is_deny ? "Yes" : "No"}</td>
                    <td>{row.is_effective ? "Yes" : "No"}</td>
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
