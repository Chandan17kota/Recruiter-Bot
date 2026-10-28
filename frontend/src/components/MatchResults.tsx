import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { EmptyState, ErrorState, LoadingList } from "./States";

/**
 * Loading / error / empty / list states shared by both match pages.
 * `total` is shown exactly as returned by the API.
 */
export function MatchResults<T extends { total: number; matches: unknown[] }>({
  query,
  noun,
  notFoundTitle,
  backTo,
  isFiltered,
  onReset,
  children,
}: {
  query: UseQueryResult<T>;
  noun: string;
  notFoundTitle: string;
  backTo: { to: string; label: string };
  isFiltered: boolean;
  onReset: () => void;
  children: (data: T) => ReactNode;
}) {
  const { data, error, isPending, isPlaceholderData, isFetching } = query;

  if (isPending) return <LoadingList label="Loading matches" />;
  // Keep showing the previous list if only a refetch failed; a failed first load shows the error.
  if (error && !data) return <ErrorState error={error} notFoundTitle={notFoundTitle} backTo={backTo} />;
  if (!data) return null;

  return (
    <section aria-label="Results" aria-busy={isFetching} className="space-y-3">
      {error && <ErrorState error={error} />}
      <p className="text-sm text-slate-600" aria-live="polite">
        {data.total} {noun}{data.total === 1 ? "" : "s"} ranked{isFiltered ? " (filtered)" : ""}
        {isPlaceholderData && <span className="ml-2 text-slate-400">updating…</span>}
      </p>
      {data.matches.length === 0 ? (
        <EmptyState title={`No ${noun}s match these filters.`}>
          {isFiltered && (
            <button type="button" onClick={onReset} className="text-sm font-medium text-indigo-700 underline">
              Reset filters
            </button>
          )}
        </EmptyState>
      ) : (
        <div className={isPlaceholderData ? "opacity-60 transition-opacity" : undefined}>{children(data)}</div>
      )}
    </section>
  );
}
