// Aliases for the generated OpenAPI types (src/api/schema.d.ts). Nothing here is
// hand-written: regenerate with `npm run gen:api` when the backend changes.
import type { components } from "./schema";

type S = components["schemas"];

export type Availability = S["Availability"];
export type Job = S["JobOut"];
export type JobSummary = S["JobSummaryOut"];
export type Candidate = S["CandidateOut"];
export type CandidateSummary = S["CandidateSummaryOut"];
export type Components = S["ComponentsOut"];
export type CultureStatus = S["CultureComponentOut"]["status"];
export type CandidateMatch = S["CandidateMatchOut"];
export type JobMatch = S["JobMatchOut"];
export type JobMatchesResponse = S["JobMatchesResponse"];
export type CandidateMatchesResponse = S["CandidateMatchesResponse"];
export type JobListResponse = S["JobListResponse"];
export type CandidateListResponse = S["CandidateListResponse"];
export type HealthResponse = S["HealthResponse"];
export type ErrorBody = S["ErrorBody"];

/** Fields shared by both match row types, which is what the shared components render. */
export type MatchCore = Pick<
  CandidateMatch,
  "rank" | "score" | "skill_coverage" | "matched_required_skill_count" | "required_skill_count" | "components" | "explanation"
>;

export const AVAILABILITIES: readonly Availability[] = ["immediate", "two_weeks", "not_looking", "unknown"];
