import type { ReadSession } from "./session";
import { normalizeApiErrorDetail } from "./apiError";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export type ApiError = {
  status: number;
  detail: string;
};

export type ApiGetOptions = {
  session?: ReadSession | null;
  companyScoped?: boolean;
  init?: RequestInit;
};

export async function apiGet<T>(
  path: string,
  options?: ApiGetOptions | RequestInit,
): Promise<T> {
  const normalized: ApiGetOptions =
    options && ("session" in options || "companyScoped" in options || "init" in options)
      ? (options as ApiGetOptions)
      : { init: options as RequestInit | undefined };

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(normalized.init?.headers as Record<string, string> | undefined),
  };

  if (normalized.session?.accessToken) {
    headers.Authorization = `Bearer ${normalized.session.accessToken}`;
  }
  if (normalized.companyScoped && normalized.session?.companyId) {
    headers["X-Company-Id"] = String(normalized.session.companyId);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...normalized.init,
    method: "GET",
    headers,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: unknown;
    };
    const err: ApiError = {
      status: response.status,
      detail:
        normalizeApiErrorDetail(body.detail) ||
        response.statusText ||
        "Request failed.",
    };
    throw err;
  }
  return (await response.json()) as T;
}
