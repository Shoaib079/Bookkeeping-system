const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export type ApiError = {
  status: number;
  detail: string;
};

export async function apiGet<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    method: "GET",
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    const err: ApiError = {
      status: response.status,
      detail: body.detail ?? response.statusText,
    };
    throw err;
  }
  return (await response.json()) as T;
}
