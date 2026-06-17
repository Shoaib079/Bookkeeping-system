import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { BankStatementRowsListResponse } from "../lib/api/types";

type StatementRowPickerProps = {
  value: string;
  onChange: (rowId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
};

export function StatementRowPicker({
  value,
  onChange,
  session,
  disabled = false,
}: StatementRowPickerProps) {
  const [rows, setRows] = useState<BankStatementRowsListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setRows(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const data = await apiGet<BankStatementRowsListResponse>(
          "/api/v1/bank-statement-rows",
          {
            session,
            companyScoped: true,
          },
        );
        if (!cancelled) {
          setRows(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load statement rows.";
          setError(detail);
          setRows(null);
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
      Statement row
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !rows}
        required
      >
        <option value="">Select statement row…</option>
        {rows?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            #{row.import_row_index}
            {row.date ? ` · ${row.date}` : ""} · {row.description} · {row.amount}{" "}
            {row.currency}
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
