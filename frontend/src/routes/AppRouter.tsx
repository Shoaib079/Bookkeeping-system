import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../layouts/AppShell";
import { routeSpecs } from "../lib/routes";
import { PlaceholderPage } from "../pages/PlaceholderPage";

export function AppRouter() {
  const routes = routeSpecs();

  return (
    <Routes>
      <Route element={<AppShell />}>
        {routes.map((route) =>
          route.path === "/" ? (
            <Route key={route.path} index element={<PlaceholderPage />} />
          ) : (
            <Route
              key={route.path}
              path={route.path.replace(/^\//, "")}
              element={<PlaceholderPage />}
            />
          ),
        )}
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
