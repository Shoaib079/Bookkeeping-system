import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { MenuProfitabilityListResponse } from "../lib/api/types";

function formatMoney(value: number | null): string {
  if (value == null) {
    return "—";
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPct(value: number | null): string {
  if (value == null) {
    return "—";
  }
  return `${value}%`;
}

export function RecipeMenuItemsPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [page, setPage] = useState<MenuProfitabilityListResponse | null>(null);
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
        const data = await apiGet<MenuProfitabilityListResponse>(
          "/api/v1/menu-profitability",
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setPage(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load menu profitability.";
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
    <section className="erp-recipe-menu-items-page">
      <header className="erp-page-header">
        <h1>Menu Items</h1>
        <p className="erp-page-header__meta">
          Read-only menu profitability via `/api/v1/menu-profitability`
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
            <span>Menu items: {page.row_count}</span>
            <span>Target food cost: {page.target_food_cost_pct}%</span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Recipe</th>
                  <th>Recipe cost</th>
                  <th>Price (gross)</th>
                  <th>Price (net)</th>
                  <th>Gross profit</th>
                  <th>Food cost %</th>
                  <th>Markup %</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row) => (
                  <tr key={row.menu_item_id}>
                    <td>{row.menu_item_name}</td>
                    <td>{row.recipe_name}</td>
                    <td>{formatMoney(row.recipe_cost)}</td>
                    <td>{formatMoney(row.selling_price_gross)}</td>
                    <td>{formatMoney(row.selling_price_net)}</td>
                    <td>{formatMoney(row.gross_profit)}</td>
                    <td>{formatPct(row.food_cost_pct)}</td>
                    <td>{formatPct(row.markup_pct)}</td>
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
