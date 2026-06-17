import type { ComponentType } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import {
  reactPagesEnabled,
  reactWriteSalesEnabled,
} from "../config/featureFlags";
import { AppShell } from "../layouts/AppShell";
import { routeSpecs, type RouteSpec } from "../lib/routes";
import { HomePage } from "../pages/HomePage";
import { LedgerPage } from "../pages/LedgerPage";
import { NewTransactionPage } from "../pages/NewTransactionPage";
import { PlaceholderPage } from "../pages/PlaceholderPage";

const READ_PAGES: Record<string, ComponentType> = {
  "/": HomePage,
  "/books/general-ledger": LedgerPage,
};

const WRITE_PAGES: Record<string, ComponentType> = {
  "/transactions/new": NewTransactionPage,
};

function RoutePage({ route }: { route: RouteSpec }) {
  if (!reactPagesEnabled()) {
    return <PlaceholderPage />;
  }
  if (route.path in WRITE_PAGES && reactWriteSalesEnabled()) {
    const Page = WRITE_PAGES[route.path];
    return <Page />;
  }
  if (route.path in READ_PAGES) {
    const Page = READ_PAGES[route.path];
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
