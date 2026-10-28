// MSW stands in for FastAPI. Default handlers serve real responses captured from
// the backend (src/test/fixtures); tests override them per case.
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import candidate1 from "./fixtures/candidate-1-matches.json";
import candidates from "./fixtures/candidates.json";
import job1 from "./fixtures/job-1-matches.json";
import job2 from "./fixtures/job-2-matches.json";
import jobs from "./fixtures/jobs.json";
import testReport from "./fixtures/test-report.json";

export const API = "http://api.test";

export const fixtures = { jobs, candidates, job1, job2, candidate1, testReport };

export const envelope = (status: number, code: string, message: string) =>
  HttpResponse.json({ error: { code, message, details: null } }, { status });

/** Every request URL the API received, for asserting query parameters. */
export const requests: URL[] = [];

export const server = setupServer(
  // Static file served by Vite from frontend/public, not an API route.
  http.get("*/test-report.json", () => HttpResponse.json(testReport)),
  http.get(`${API}/health`, () => HttpResponse.json({ status: "ok", database: "ok" })),
  http.get(`${API}/jobs`, () => HttpResponse.json(jobs)),
  http.get(`${API}/candidates`, () => HttpResponse.json(candidates)),
  http.get(`${API}/jobs/:id/matches`, ({ params }) => {
    if (params.id === "1") return HttpResponse.json(job1);
    if (params.id === "2") return HttpResponse.json(job2);
    return envelope(404, "JOB_NOT_FOUND", `Job ${String(params.id)} does not exist`);
  }),
  http.get(`${API}/candidates/:id/matches`, ({ params }) =>
    params.id === "1"
      ? HttpResponse.json(candidate1)
      : envelope(404, "CANDIDATE_NOT_FOUND", `Candidate ${String(params.id)} does not exist`),
  ),
);

server.events.on("request:start", ({ request }) => {
  requests.push(new URL(request.url));
});

beforeEach(() => {
  requests.length = 0;
});
