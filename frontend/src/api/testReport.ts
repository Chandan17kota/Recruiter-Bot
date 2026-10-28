import { useQuery } from "@tanstack/react-query";

// The test report is a static file written by `python -m scripts.test_report`
// (frontend/public/test-report.json), not an API response, so its type lives here
// rather than in the generated OpenAPI types. Keep it in step with that script.

export type TestStatus = "passed" | "failed" | "error" | "skipped";
export type StatusCounts = Record<TestStatus, number>;

export interface TestCase {
  name: string;
  status: TestStatus;
  duration_s: number;
  message: string | null;
}

export interface TestFile {
  path: string;
  counts: StatusCounts;
  duration_s: number;
  tests: TestCase[];
}

export interface TestReport {
  generated_at: string;
  git_commit: string | null;
  generator?: string;
  python_version: string;
  pytest_version?: string;
  pytest_exit_code: number;
  duration_s: number;
  summary: StatusCounts & { total: number };
  files: TestFile[];
}

export class ReportMissingError extends Error {}

function isReport(value: unknown): value is TestReport {
  const r = value as Partial<TestReport> | null;
  return typeof r?.generated_at === "string" && typeof r.summary?.total === "number" && Array.isArray(r.files);
}

export const REPORT_URL = `${import.meta.env.BASE_URL}test-report.json`;

export const useTestReport = () =>
  useQuery({
    queryKey: ["testReport"],
    queryFn: async ({ signal }): Promise<TestReport> => {
      const res = await fetch(new URL(REPORT_URL, window.location.origin), { signal, cache: "no-store" });
      if (res.status === 404) throw new ReportMissingError("No test report has been generated yet.");
      if (!res.ok) throw new Error(`Could not load the test report (HTTP ${res.status}).`);
      // The dev server answers unknown paths with index.html, so check the body too.
      const body: unknown = await res.json().catch(() => null);
      if (!isReport(body)) throw new ReportMissingError("No test report has been generated yet.");
      return body;
    },
    retry: false,
  });
