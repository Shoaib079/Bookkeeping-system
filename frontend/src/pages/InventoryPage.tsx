import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { ProductsListResponse } from "../lib/api/types";

export function InventoryPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<ProductsListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<ProductsListResponse>("/api/v1/products", {
          session,
          companyScoped: true,
        });
        if (!cancelled) {
          setPage(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load products.";
          setError(detail);
          setPage(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [session]);

  return (
    <section className="erp-inventory-page">
      <header className="erp-page-header">
        <h1>Inventory</h1>
        <p className="erp-page-header__meta">
          Read-only product catalog via `/api/v1/products`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {page ? (
        <>
          <div className="erp-ledger-summary">
            <span>Products: {page.stats.total}</span>
            <span>Low stock: {page.stats.low_stock}</span>
            <span>Out of stock: {page.stats.out_of_stock}</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Stock</th>
                  <th>Min</th>
                  <th>Status</th>
                  <th>Cost</th>
                  <th>Price</th>
                  <th>Active</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.sku ?? "—"}</td>
                    <td>{row.name}</td>
                    <td>{row.category ?? "—"}</td>
                    <td>
                      {row.quantity}
                      {row.unit_of_measure ? ` ${row.unit_of_measure}` : ""}
                    </td>
                    <td>{row.min_stock}</td>
                    <td>{row.stock_status}</td>
                    <td>{row.cost_price}</td>
                    <td>{row.unit_price}</td>
                    <td>{row.is_active ? "Yes" : "No"}</td>
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
