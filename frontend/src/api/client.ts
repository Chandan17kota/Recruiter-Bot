import type { ErrorBody } from "./types";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

/** An error from the API's {"error": {code, message, details}} envelope, or a network failure. */
export class ApiError extends Error {
  readonly status: number; // 0 = the request never reached the server
  readonly code: string;
  readonly details: ErrorBody["details"];

  constructor(status: number, body: ErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? null;
  }

  get isNotFound() {
    return this.status === 404;
  }

  get isUnavailable() {
    return this.status === 0 || this.status === 503;
  }
}

export type QueryParams = Record<string, string | number | readonly string[] | null | undefined>;

export function buildQuery(params: QueryParams = {}): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null) continue;
    if (Array.isArray(value)) value.forEach((v) => search.append(key, v));
    else search.append(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

function isErrorEnvelope(body: unknown): body is { error: ErrorBody } {
  const err = (body as { error?: Partial<ErrorBody> } | null)?.error;
  return typeof err?.code === "string" && typeof err.message === "string";
}

export async function apiGet<T>(path: string, params?: QueryParams, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}${buildQuery(params)}`, {
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (cause) {
    if ((cause as Error)?.name === "AbortError") throw cause;
    throw new ApiError(0, { code: "NETWORK_ERROR", message: "Could not reach the API server." });
  }

  const body: unknown = await response.json().catch(() => null);
  if (response.ok) return body as T;
  if (isErrorEnvelope(body)) throw new ApiError(response.status, body.error);
  throw new ApiError(response.status, {
    code: "HTTP_ERROR",
    message: `The API returned an unexpected ${response.status} response.`,
  });
}
