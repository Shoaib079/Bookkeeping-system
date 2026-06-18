# FASTAPI-REACT-50 — Recipe Costing Read Pages

**Mode:** React read page expansion with thin P1 recipe costing read APIs.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-50** from [FASTAPI_REACT_49 audit §7](./FASTAPI_REACT_49_REACT_READ_STAFF_CAPTURE_AUDIT.md).  
**Tag:** `fastapi-react-50-react-read-recipe-costing`

**Prerequisites:** [FASTAPI-REACT-49](./FASTAPI_REACT_49_REACT_READ_STAFF_CAPTURE_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Ingredients page (`/recipes/ingredients`) | ✅ `RecipeIngredientsPage` |
| Recipes page (`/recipes`) | ✅ `RecipesPage` |
| Cost Breakdown page (`/recipes/cost-breakdown`) | ✅ `RecipeCostBreakdownPage` |
| Menu Items page (`/recipes/menu-items`) | ✅ `RecipeMenuItemsPage` |
| `GET /api/v1/recipe-ingredients` | ✅ `read_recipe_costing.compute_recipe_ingredients_list` |
| `GET /api/v1/recipes` | ✅ `read_recipe_costing.compute_recipes_list` |
| `GET /api/v1/recipe-cost-breakdowns` | ✅ `read_recipe_costing.compute_recipe_cost_breakdown` |
| `GET /api/v1/menu-profitability` | ✅ `read_recipe_costing.compute_menu_profitability_list` |

**Accounting / GL behavior:** **UNCHANGED** — read-only ingredient/recipe/menu profitability views. CRUD and posting remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/recipes/ingredients` | `RecipeIngredientsPage` | `/api/v1/recipe-ingredients` |
| `/recipes` | `RecipesPage` | `/api/v1/recipes` |
| `/recipes/cost-breakdown` | `RecipeCostBreakdownPage` | `/api/v1/recipes` + `/api/v1/recipe-cost-breakdowns` |
| `/recipes/menu-items` | `RecipeMenuItemsPage` | `/api/v1/menu-profitability` |

**Real React read routes:** 42 (was 38). **Placeholder routes:** 0 (was 4).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (ingredient/recipe/menu CRUD)
- No GL / posting kernel edits
- No new write API routes
- Read pages use `apiGet` only (`companyScoped: true`)
- Guard uses `view_recipe_costing` (owner/manager — cashier denied)

---

## 5. Deferred (out of FR-50 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-51** | Ops slices or production `COMMIT_MODE_*` flip |
| **RC-AI-01** | AI recipe suggestions |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_50_react_read_recipe_costing.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-51** — production `COMMIT_MODE_*` characterization flip or next epic ops slice; all NAV read placeholders are now wired.
