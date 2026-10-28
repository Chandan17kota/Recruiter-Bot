import type { ReactNode } from "react";
import { Link } from "react-router";

import { ApiError } from "../api/client";

export function LoadingList({ rows = 4, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-label={label} className="space-y-3">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-24 animate-pulse rounded-xl border border-slate-200 bg-white" />
      ))}
      <span className="sr-only">{label}…</span>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-3">{children}</div>}
    </div>
  );
}

/** Renders any query error. API errors use the backend's envelope; others get a generic message. */
export function ErrorState({ error, notFoundTitle = "Not found", backTo }: {
  error: unknown;
  notFoundTitle?: string;
  backTo?: { to: string; label: string };
}) {
  const api = error instanceof ApiError ? error : null;
  let title = "Something went wrong";
  let message = "An unexpected error occurred. Please try again.";

  if (api?.isNotFound) {
    title = notFoundTitle;
    message = api.message;
  } else if (api?.isUnavailable) {
    title = "Service unavailable";
    message = api.status === 0
      ? "Could not reach the API server. Check that the backend is running."
      : "The database is unavailable. Please retry shortly.";
  } else if (api?.status === 422) {
    title = "Invalid request";
    message = api.message;
  } else if (api) {
    message = api.message;
  }

  return (
    <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-6">
      <p className="font-semibold text-rose-900">{title}</p>
      <p className="mt-1 text-sm text-rose-800">{message}</p>
      {api && <p className="mt-2 font-mono text-xs text-rose-700">{api.code}</p>}
      {backTo && (
        <Link to={backTo.to} className="mt-3 inline-block text-sm font-medium text-rose-900 underline">
          {backTo.label}
        </Link>
      )}
    </div>
  );
}
