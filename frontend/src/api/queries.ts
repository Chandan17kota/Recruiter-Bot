import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ApiError, apiGet } from "./client";
import type {
  Availability,
  CandidateListResponse,
  CandidateMatchesResponse,
  HealthResponse,
  JobListResponse,
  JobMatchesResponse,
} from "./types";

export interface MatchFilters {
  minScore: number;
  minSkillCoverage: number;
  availability: Availability[]; // empty = no filter
}

function matchParams(f: MatchFilters, withAvailability: boolean) {
  return {
    min_score: f.minScore || null,
    min_skill_coverage: f.minSkillCoverage || null,
    availability: withAvailability && f.availability.length ? f.availability : null,
  };
}

export const useJobs = () =>
  useQuery({ queryKey: ["jobs"], queryFn: ({ signal }) => apiGet<JobListResponse>("/jobs", undefined, signal) });

export const useCandidates = (availability: Availability[]) =>
  useQuery({
    queryKey: ["candidates", availability],
    queryFn: ({ signal }) =>
      apiGet<CandidateListResponse>("/candidates", { availability: availability.length ? availability : null }, signal),
    placeholderData: keepPreviousData,
  });

export const useJobMatches = (jobId: number, filters: MatchFilters) =>
  useQuery({
    queryKey: ["jobMatches", jobId, filters],
    queryFn: ({ signal }) => apiGet<JobMatchesResponse>(`/jobs/${jobId}/matches`, matchParams(filters, true), signal),
    placeholderData: keepPreviousData, // keep the list on screen while a filter change loads
  });

export const useCandidateMatches = (candidateId: number, filters: MatchFilters) =>
  useQuery({
    queryKey: ["candidateMatches", candidateId, filters],
    queryFn: ({ signal }) =>
      apiGet<CandidateMatchesResponse>(`/candidates/${candidateId}/matches`, matchParams(filters, false), signal),
    placeholderData: keepPreviousData,
  });

/** Health: a degraded database answers 503 with a HealthResponse body, not the error envelope. */
export const useHealth = () =>
  useQuery({
    queryKey: ["health"],
    queryFn: async ({ signal }): Promise<HealthResponse> => {
      try {
        return await apiGet<HealthResponse>("/health", undefined, signal);
      } catch (e) {
        if (e instanceof ApiError && e.status === 503) return { status: "degraded", database: "unavailable" };
        throw e;
      }
    },
    refetchInterval: 30_000,
    retry: false,
  });
