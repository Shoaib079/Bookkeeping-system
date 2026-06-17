import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { ReceivableSalesListResponse } from "../lib/api/types";

type ReceivableSalePickerProps = {
  value: string;
  onChange: (saleId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
};

export function ReceivableSalePicker({
  value,
  onChange,
  session,
  disabled = false,
}: ReceivableSalePickerProps) {
  const [sales, setSales] = useState<ReceivableSalesListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setSales(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const data = await apiGet<ReceivableSalesListResponse>(
          "/api/v1/receivable-sales",
          {
            session,
            companyScoped: true,
          },
        );
        if (!cancelled) {
          setSales(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load credit sales.";
          setError(detail);
          setSales(null);
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
      Credit sale
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !sales}
        required
      >
        <option value="">Select credit sale…</option>
        {sales?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            {row.invoice_number} · {row.customer_name} · balance {row.balance}
            {row.currency ? ` ${row.currency}` : ""}
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
