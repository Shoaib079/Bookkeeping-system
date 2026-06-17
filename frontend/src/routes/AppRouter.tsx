import type { ComponentType } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { reactPagesEnabled } from "../config/featureFlags";
import { AppShell } from "../layouts/AppShell";
import { routeSpecs, type RouteSpec } from "../lib/routes";
import { HomePage } from "../pages/HomePage";
import { LedgerPage } from "../pages/LedgerPage";
import { PlaceholderPage } from "../pages/PlaceholderPage";

const REAL_PAGES: Record<string, ComponentType> = {
  "/": HomePage,
  "/books/general-ledger": LedgerPage,
};

function RoutePage({ route }: { route: RouteSpec }) {
  if (reactPagesEnabled() && route.path in REAL_PAGES) {
    const Page = REAL_PAGES[route.path];
    return <Page />;
  }
  return <PlaceholderPage />;
}

export function AppRouter() {
  const routes = routeSpecs();

  return (
    <Routes>
      <Route element={<AppShell />}>
        {routes.map((route) =>
          route.path === "/" ? (
            <Route key={route.path} index element={<RoutePage route={route} />} />
          ) : (
            <Route
              key={route.path}
              path={route.path.replace(/^\//, "")}
              element={<RoutePage route={route} />}
            />
          ),
        )}
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
