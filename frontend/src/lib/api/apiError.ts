/** Shared FastAPI error detail normalization (read + write clients). */

import type { ApiError } from "./client";

/**
 * Normalize ``detail`` from a FastAPI error body to displayable text.
 *
 * Origin: FASTAPI-REACT-08 ``writeClient.ts`` handled ``{ message }`` objects;
 * read ``client.ts`` passed ``detail`` through raw, and pages used
 * ``String(detail)`` → ``[object Object]`` (REACT-LOCAL-OBS-01).
 */
export function normalizeApiErrorDetail(detail: unknown): string {
  if (detail == null || detail === "") {
    return "";
  }
  if (typeof detail === "string") {
    return detail;
  }
  if (typeof detail === "number" || typeof detail === "boolean") {
    return String(detail);
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => normalizeApiErrorDetail(item))
      .filter((part) => part.length > 0);
    return parts.join("; ");
  }
  if (typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === "string" && record.message) {
      return record.message;
    }
    const loc = Array.isArray(record.loc)
      ? record.loc.map(String).join(".")
      : "";
    const msg = typeof record.msg === "string" ? record.msg : "";
    if (loc && msg) {
      return `${loc}: ${msg}`;
    }
    if (msg) {
      return msg;
    }
    try {
      return JSON.stringify(detail, null, 2);
    } catch {
      return "Request failed.";
    }
  }
  return String(detail);
}

/** Catch-block helper — never returns ``[object Object]``. */
export function errorMessageFromCatch(
  err: unknown,
  fallback = "Request failed.",
): string {
  if (err && typeof err === "object" && "detail" in err) {
    const formatted = normalizeApiErrorDetail((err as ApiError).detail);
    if (formatted) {
      return formatted;
    }
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return fallback;
}
