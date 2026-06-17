import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { BankAccountsListResponse } from "../lib/api/types";

type BankAccountPickerProps = {
  value: string;
  onChange: (bankAccountId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
  label?: string;
  excludeCreditCard?: boolean;
};

export function BankAccountPicker({
  value,
  onChange,
  session,
  disabled = false,
  label = "Bank account",
  excludeCreditCard = false,
}: BankAccountPickerProps) {
  const [accounts, setAccounts] = useState<BankAccountsListResponse | null>(null);
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
        const path = excludeCreditCard
          ? "/api/v1/bank-accounts?exclude_kind=credit_card"
          : "/api/v1/bank-accounts";
        const data = await apiGet<BankAccountsListResponse>(path, {
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
              : "Failed to load bank accounts.";
          setError(detail);
          setAccounts(null);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [session, excludeCreditCard]);

  return (
    <label>
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !accounts}
        required
      >
        <option value="">Select bank account…</option>
        {accounts?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            {row.name}
            {row.currency ? ` (${row.currency})` : ""}
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
