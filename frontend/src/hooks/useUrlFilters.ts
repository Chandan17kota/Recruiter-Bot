import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";

import type { MatchFilters } from "../api/queries";
import { AVAILABILITIES, type Availability } from "../api/types";

// The URL is the single source of truth for filters, so any filtered view can be
// bookmarked or shared. Parameter names match the API's query parameters.

/** A 0–100 number from the URL; anything else (missing, NaN, out of range) falls back to 0. */
export function parsePercent(raw: string | null): number {
  if (raw == null || raw.trim() === "") return 0;
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 && n <= 100 ? n : 0;
}

/** Known availability values only, de-duplicated, in a fixed order. */
export function parseAvailability(raw: string[]): Availability[] {
  return AVAILABILITIES.filter((a) => raw.includes(a));
}

export function filtersFromSearch(search: URLSearchParams): MatchFilters {
  return {
    minScore: parsePercent(search.get("min_score")),
    minSkillCoverage: parsePercent(search.get("min_skill_coverage")),
    availability: parseAvailability(search.getAll("availability")),
  };
}

export function useUrlFilters() {
  const [search, setSearch] = useSearchParams();
  const filters = useMemo(() => filtersFromSearch(search), [search]);

  const update = useCallback(
    (patch: Partial<MatchFilters>) => {
      setSearch(
        (prev) => {
          const next = new URLSearchParams(prev);
          const merged = { ...filtersFromSearch(prev), ...patch };
          const setOrDelete = (key: string, value: number) =>
            value > 0 ? next.set(key, String(value)) : next.delete(key);
          setOrDelete("min_score", merged.minScore);
          setOrDelete("min_skill_coverage", merged.minSkillCoverage);
          next.delete("availability");
          parseAvailability(merged.availability).forEach((a) => next.append("availability", a));
          return next;
        },
        { replace: true }, // slider drags shouldn't flood the back button
      );
    },
    [setSearch],
  );

  const reset = useCallback(() => setSearch(new URLSearchParams(), { replace: true }), [setSearch]);

  const isFiltered = filters.minScore > 0 || filters.minSkillCoverage > 0 || filters.availability.length > 0;

  return { filters, update, reset, isFiltered };
}
