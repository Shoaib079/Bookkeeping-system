import type { ReadSession } from "./session";
import { ApiError } from "./client";
import { normalizeApiErrorDetail } from "./apiError";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export type ApiPostOptions = {
  session: ReadSession;
  init?: RequestInit;
};

function authHeaders(session: ReadSession): Record<string, string> {
  return {
    Accept: "application/json",
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.accessToken}`,
    "X-Company-Id": String(session.companyId),
  };
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  options: ApiPostOptions,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options.init,
    method: "POST",
    headers: {
      ...authHeaders(options.session),
      ...(options.init?.headers as Record<string, string> | undefined),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as {
      detail?: unknown;
    };
    const err: ApiError = {
      status: response.status,
      detail:
        normalizeApiErrorDetail(payload.detail) ||
        response.statusText ||
        "Request failed.",
    };
    throw err;
  }
  return (await response.json()) as T;
}
