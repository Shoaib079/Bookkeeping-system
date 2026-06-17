import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { ProfitAllocationsListResponse } from "../lib/api/types";

type ProfitAllocationPickerProps = {
  value: string;
  onChange: (allocationId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
};

export function ProfitAllocationPicker({
  value,
  onChange,
  session,
  disabled = false,
}: ProfitAllocationPickerProps) {
  const [allocations, setAllocations] = useState<ProfitAllocationsListResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setAllocations(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const data = await apiGet<ProfitAllocationsListResponse>(
          "/api/v1/profit-allocations",
          {
            session,
            companyScoped: true,
          },
        );
        if (!cancelled) {
          setAllocations(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load profit allocations.";
          setError(detail);
          setAllocations(null);
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
      Profit allocation
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !allocations}
        required
      >
        <option value="">Select allocation…</option>
        {allocations?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            #{row.id} · {row.period_name} · {row.total_net_income}
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
