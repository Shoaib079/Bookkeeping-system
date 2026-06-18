import { useEffect, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type {
  RecipeCostBreakdownResponse,
  RecipesListResponse,
} from "../lib/api/types";

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function RecipeCostBreakdownPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [recipes, setRecipes] = useState<RecipesListResponse | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [breakdown, setBreakdown] = useState<RecipeCostBreakdownResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    let cancelled = false;
    async function loadRecipes() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<RecipesListResponse>("/api/v1/recipes", {
          session,
          companyScoped: true,
        });
        if (!cancelled) {
          setRecipes(data);
          setSelectedId(data.rows[0]?.id ?? null);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load recipes.";
          setError(detail);
          setRecipes(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void loadRecipes();
    return () => {
      cancelled = true;
    };
  }, [session]);

  useEffect(() => {
    if (!session || selectedId == null) {
      setBreakdown(null);
      return;
    }
    let cancelled = false;
    async function loadBreakdown() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<RecipeCostBreakdownResponse>(
          `/api/v1/recipe-cost-breakdowns?recipe_id=${selectedId}`,
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setBreakdown(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load recipe cost breakdown.";
          setError(detail);
          setBreakdown(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void loadBreakdown();
    return () => {
      cancelled = true;
    };
  }, [session, selectedId]);

  return (
    <section className="erp-recipe-cost-breakdown-page">
      <header className="erp-page-header">
        <h1>Cost Breakdown</h1>
        <p className="erp-page-header__meta">
          Read-only recipe costing via `/api/v1/recipe-cost-breakdowns`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      {session && recipes && recipes.rows.length > 0 ? (
        <label className="erp-field">
          <span>Recipe</span>
          <select
            value={selectedId ?? ""}
            onChange={(event) => setSelectedId(Number(event.target.value))}
          >
            {recipes.rows.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {breakdown ? (
        <>
          <div className="erp-ledger-summary">
            <span>Total: {formatMoney(breakdown.total_cost)}</span>
            <span>
              Per portion: {formatMoney(breakdown.cost_per_yield_unit)}
            </span>
            <span>
              Yield: {breakdown.yield_quantity} {breakdown.yield_unit}
            </span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Component</th>
                  <th>Quantity</th>
                  <th>Waste</th>
                  <th>Line cost</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.line_costs.map((line, index) => (
                  <tr key={`${line.line_id ?? index}-${line.name}`}>
                    <td>{line.name}</td>
                    <td>
                      {line.quantity} {line.unit}
                    </td>
                    <td>{line.waste_percent}%</td>
                    <td>{formatMoney(line.line_cost)}</td>
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
