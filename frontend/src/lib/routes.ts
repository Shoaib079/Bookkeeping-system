export type RouteSpec = {
  routeKey: string;
  path: string;
};

export type RouteManifest = {
  version: string;
  routes: RouteSpec[];
};

import manifest from "../generated/routes.json";

export const routeManifest = manifest as RouteManifest;

export function routeSpecs(): RouteSpec[] {
  return routeManifest.routes;
}
