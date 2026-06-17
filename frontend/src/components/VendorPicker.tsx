import { useEffect, useState } from "react";

import { apiGet } from "../lib/api/client";
import type { ReadSession } from "../lib/api/session";
import type { VendorsListResponse } from "../lib/api/types";

type VendorPickerProps = {
  value: string;
  onChange: (vendorId: string) => void;
  session: ReadSession | null;
  disabled?: boolean;
};

export function VendorPicker({
  value,
  onChange,
  session,
  disabled = false,
}: VendorPickerProps) {
  const [vendors, setVendors] = useState<VendorsListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setVendors(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const data = await apiGet<VendorsListResponse>("/api/v1/vendors", {
          session,
          companyScoped: true,
        });
        if (!cancelled) {
          setVendors(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load vendors.";
          setError(detail);
          setVendors(null);
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
      Vendor
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled || !session || !vendors}
        required
      >
        <option value="">Select vendor…</option>
        {vendors?.rows.map((row) => (
          <option key={row.id} value={String(row.id)}>
            {row.name}
          </option>
        ))}
      </select>
      {error ? <span className="erp-error">{error}</span> : null}
    </label>
  );
}
