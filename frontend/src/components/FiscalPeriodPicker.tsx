import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { FiscalPeriodsListResponse } from "../lib/api/types";

type FiscalPeriodPickerProps = {
  value: string;
  onChange: (periodId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
  openOnly?: boolean;
  closedOnly?: boolean;
};

export function FiscalPeriodPicker({
  value,
  onChange,
  session,
  disabled = false,
  openOnly = false,
  closedOnly = false,
}: FiscalPeriodPickerProps) {
  const [periods, setPeriods] = useState<FiscalPeriodsListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setPeriods(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const params = new URLSearchParams();
        if (openOnly) {
          params.set("open_only", "true");
        }
        if (closedOnly) {
          params.set("closed_only", "true");
        }
        const query = params.toString();
        const path = query
          ? `/api/v1/fiscal-periods?${query}`
          : "/api/v1/fiscal-periods";
        const data = await apiGet<FiscalPeriodsListResponse>(path, {
          session,
          companyScoped: true,
        });
        if (!cancelled) {
          setPeriods(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load fiscal periods.";
          setError(detail);
          setPeriods(null);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [session, openOnly, closedOnly]);

  return (
    <label>
      Fiscal period
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !periods}
        required
      >
        <option value="">Select fiscal period…</option>
        {periods?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            {row.name} ({row.start_date} – {row.end_date})
            {row.is_closed ? " · Closed" : " · Open"}
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
