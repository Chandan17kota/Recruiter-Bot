// Display formatting only. Every number shown here comes from the API already
// computed and rounded; nothing in the frontend derives or adjusts a score.
import type { Availability, CultureStatus } from "../api/types";

/** 92.5 -> "92.50" (the API rounds to 2 places; this only fixes trailing zeros). */
export const formatScore = (score: number) => score.toFixed(2);

/** 0.6 -> "60%", 0.705882 -> "70.59%" (weights arrive as fractions of 1). */
export function formatWeight(weight: number) {
  const pct = weight * 100;
  return `${Number.isInteger(pct) ? pct : pct.toFixed(2)}%`;
}

/** 100 -> "100%", 33.33 -> "33.33%" */
export const formatPercent = (value: number) => `${Number.isInteger(value) ? value : value.toFixed(2)}%`;

export const formatYears = (years: number) => `${years} ${years === 1 ? "yr" : "yrs"}`;

export const AVAILABILITY_LABEL: Record<Availability, string> = {
  immediate: "Immediate",
  two_weeks: "2 weeks",
  not_looking: "Not looking",
  unknown: "Unknown",
};

export const CULTURE_STATUS_LABEL: Record<CultureStatus, string> = {
  scored: "Scored",
  unknown_candidate_traits: "Not scored: candidate traits unknown",
  no_job_keywords: "Not scored: job has no culture keywords",
};
