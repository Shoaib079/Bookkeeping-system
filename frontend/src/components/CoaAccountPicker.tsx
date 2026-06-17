import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { CoaListResponse } from "../lib/api/types";

type CoaAccountPickerProps = {
  value: string;
  onChange: (accountId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
};

export function CoaAccountPicker({
  value,
  onChange,
  session,
  disabled = false,
}: CoaAccountPickerProps) {
  const [accounts, setAccounts] = useState<CoaListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setAccounts(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const data = await apiGet<CoaListResponse>("/api/v1/chart-of-accounts", {
          session,
          companyScoped: true,
        });
        if (!cancelled) {
          setAccounts(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load chart of accounts.";
          setError(detail);
          setAccounts(null);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [session]);

  return (
    <label>
      Account
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !accounts}
        required
      >
        <option value="">Select account…</option>
        {accounts?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            {row.account_code} — {row.account_name} ({row.account_type})
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
