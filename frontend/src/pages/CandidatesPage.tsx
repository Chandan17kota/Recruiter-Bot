import { Link } from "react-router";

import { useCandidates } from "../api/queries";
import { AvailabilityBadge, ChipList } from "../components/Chips";
import { AvailabilityCheckboxes } from "../components/MatchFilters";
import { EmptyState, ErrorState, LoadingList } from "../components/States";
import { useUrlFilters } from "../hooks/useUrlFilters";
import { formatYears } from "../lib/format";

export function CandidatesPage() {
  const { filters, update, reset, isFiltered } = useUrlFilters();
  const { data, error, isPending } = useCandidates(filters.availability);

  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">Candidates</h1>
        <p className="text-sm text-slate-600">Pick a candidate to see jobs ranked by match score.</p>
      </div>

      <section aria-label="Filters" className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <AvailabilityCheckboxes value={filters.availability} onChange={(availability) => update({ availability })} />
      </section>

      {isPending ? (
        <LoadingList label="Loading candidates" />
      ) : error && !data ? (
        <ErrorState error={error} />
      ) : !data ? null : data.candidates.length === 0 ? (
        <EmptyState title="No candidates match these filters.">
          {isFiltered && (
            <button type="button" onClick={reset} className="text-sm font-medium text-indigo-700 underline">Reset filters</button>
          )}
        </EmptyState>
      ) : (
        <ul aria-label="Candidates" className="grid gap-3 sm:grid-cols-2">
          {data.candidates.map((c) => (
            <li key={c.id}>
              <Link
                to={`/candidates/${c.id}`}
                className="block h-full space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-indigo-300 hover:shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-semibold">{c.name}</h2>
                  <AvailabilityBadge value={c.availability} />
                  <span className="text-xs text-slate-500">{formatYears(c.experience_years)}</span>
                </div>
                <ChipList items={c.skills} label={`${c.name} skills`} />
                {c.traits && c.traits.length > 0 && (
                  <p className="text-xs text-slate-500">Traits: {c.traits.join(", ")}</p>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
