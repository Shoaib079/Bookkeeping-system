import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { WorkersListResponse } from "../lib/api/types";

type WorkerPickerProps = {
  value: string;
  onChange: (workerId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
};

export function WorkerPicker({
  value,
  onChange,
  session,
  disabled = false,
}: WorkerPickerProps) {
  const [workers, setWorkers] = useState<WorkersListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setWorkers(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const data = await apiGet<WorkersListResponse>("/api/v1/workers", {
          session,
          companyScoped: true,
        });
        if (!cancelled) {
          setWorkers(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load workers.";
          setError(detail);
          setWorkers(null);
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
      Worker
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !workers}
        required
      >
        <option value="">Select worker…</option>
        {workers?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            {row.name}
            {row.role ? ` — ${row.role}` : ""}
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
