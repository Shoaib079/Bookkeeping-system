import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { PartnersListResponse } from "../lib/api/types";

type PartnerPickerProps = {
  value: string;
  onChange: (partnerId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
};

export function PartnerPicker({
  value,
  onChange,
  session,
  disabled = false,
}: PartnerPickerProps) {
  const [partners, setPartners] = useState<PartnersListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setPartners(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const data = await apiGet<PartnersListResponse>("/api/v1/partners", {
          session,
          companyScoped: true,
        });
        if (!cancelled) {
          setPartners(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load partners.";
          setError(detail);
          setPartners(null);
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
      Partner
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !partners}
        required
      >
        <option value="">Select partner…</option>
        {partners?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            {row.name}
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
