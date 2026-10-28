import { useMemo } from "react";
import { useSearchParams } from "react-router";

import { ReportMissingError, useTestReport, type TestCase, type TestReport, type TestStatus } from "../api/testReport";
import { EmptyState, ErrorState, LoadingList } from "../components/States";
import { timeAgo } from "../lib/format";

const STATUS_STYLE: Record<TestStatus, { icon: string; label: string; text: string; chip: string }> = {
  passed: { icon: "✓", label: "Passed", text: "text-emerald-700", chip: "bg-emerald-50 text-emerald-800 ring-emerald-600/20" },
  failed: { icon: "✗", label: "Failed", text: "text-rose-700", chip: "bg-rose-50 text-rose-800 ring-rose-600/20" },
  error: { icon: "!", label: "Errors", text: "text-rose-700", chip: "bg-rose-50 text-rose-800 ring-rose-600/20" },
  skipped: { icon: "–", label: "Skipped", text: "text-amber-700", chip: "bg-amber-50 text-amber-800 ring-amber-600/20" },
};

type View = "all" | "problems" | "skipped" | "passed";
const VIEWS: { value: View; label: string }[] = [
  { value: "all", label: "All" },
  { value: "problems", label: "Failed & errors" },
  { value: "skipped", label: "Skipped" },
  { value: "passed", label: "Passed" },
];

const inView = (t: TestCase, view: View) =>
  view === "all" || (view === "problems" ? t.status === "failed" || t.status === "error" : t.status === view);

const formatDuration = (s: number) => (s < 1 ? `${Math.round(s * 1000)} ms` : `${s.toFixed(2)} s`);

/** The report is a saved snapshot, so say so before showing any numbers. */
function SnapshotNotice({ report }: { report: TestReport }) {
  const generated = new Date(report.generated_at);
  return (
    <section aria-label="Snapshot" className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950">
      <p className="font-semibold">Historical snapshot, not a live status</p>
      <p className="mt-1">
        Recorded <time dateTime={report.generated_at} className="font-medium">{generated.toLocaleString()}</time>{" "}
        ({timeAgo(generated)}) on commit <code className="rounded bg-white/70 px-1 font-mono">{report.git_commit ?? "unknown"}</code>.
        Code changed after this run is not reflected here.
      </p>
      {report.git_commit?.endsWith("-dirty") && (
        <p className="mt-1 text-amber-800">The run included uncommitted changes, so the commit above doesn't fully describe the code tested.</p>
      )}
    </section>
  );
}

function Summary({ report }: { report: TestReport }) {
  const { summary } = report;
  const problems = summary.failed + summary.error;

  return (
    <section aria-label="Summary" className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div>
        <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">Result of that run</h2>
        <p className={`text-xl font-bold ${problems ? "text-rose-700" : "text-emerald-700"}`}>
          <span aria-hidden="true">{problems ? "✗ " : "✓ "}</span>
          {problems ? `${problems} of ${summary.total} tests failing` : `All ${summary.passed} tests passed`}
          {!problems && summary.skipped > 0 && `, ${summary.skipped} skipped`}
        </p>
      </div>
      <ul aria-label="Counts" className="flex flex-wrap gap-2">
        {(Object.keys(STATUS_STYLE) as TestStatus[]).map((s) => (
          <li key={s} className={`rounded-full px-3 py-1 text-sm font-medium ring-1 ring-inset ${STATUS_STYLE[s].chip}`}>
            {STATUS_STYLE[s].label}: {summary[s]}
          </li>
        ))}
        <li className="rounded-full px-3 py-1 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-300">
          Total: {summary.total}
        </li>
      </ul>
      <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
        <div className="flex gap-2"><dt className="text-slate-500">Duration</dt><dd>{formatDuration(report.duration_s)}</dd></div>
        <div className="flex gap-2"><dt className="text-slate-500">Python</dt><dd>{report.python_version}</dd></div>
      </dl>
    </section>
  );
}

function TestRow({ test }: { test: TestCase }) {
  const style = STATUS_STYLE[test.status];
  return (
    <li className="py-2">
      <div className="flex items-start gap-2 text-sm">
        <span className={`w-4 shrink-0 text-center font-bold ${style.text}`} aria-hidden="true">{style.icon}</span>
        <span className="sr-only">{style.label.replace(/s$/, "")}:</span>
        <span className="min-w-0 flex-1 break-all font-mono text-xs leading-5">{test.name}</span>
        <span className="shrink-0 text-xs tabular-nums text-slate-500">{formatDuration(test.duration_s)}</span>
      </div>
      {test.message && (
        <pre className="mt-1 ml-6 max-h-60 overflow-auto whitespace-pre-wrap rounded-md bg-slate-900 p-3 text-xs text-slate-100">
          {test.message}
        </pre>
      )}
    </li>
  );
}

export function TestsPage() {
  const { data, error, isPending } = useTestReport();
  const [search, setSearch] = useSearchParams();
  const view = (VIEWS.find((v) => v.value === search.get("status"))?.value ?? "all") as View;
  const q = (search.get("q") ?? "").trim().toLowerCase();

  const setParam = (key: string, value: string | null) =>
    setSearch((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      return next;
    }, { replace: true });

  const files = useMemo(
    () =>
      (data?.files ?? [])
        .map((f) => ({ ...f, shown: f.tests.filter((t) => inView(t, view) && (!q || `${f.path} ${t.name}`.toLowerCase().includes(q))) }))
        .filter((f) => f.shown.length > 0),
    [data, view, q],
  );

  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">Backend test report</h1>
        <p className="text-sm text-slate-600">
          Saved by <code className="rounded bg-slate-100 px-1">python -m scripts.test_report</code>, which runs pytest and
          records its results. This page only displays that file; it can't start a test run.
        </p>
      </div>

      {isPending ? (
        <LoadingList rows={2} label="Loading test results" />
      ) : error instanceof ReportMissingError ? (
        <EmptyState title="No test report yet.">
          <p className="text-sm text-slate-600">
            From the repo root run <code className="rounded bg-slate-100 px-1">python -m scripts.test_report</code>, then reload this page.
          </p>
        </EmptyState>
      ) : error ? (
        <ErrorState error={error} />
      ) : (
        <>
          <SnapshotNotice report={data} />
          <Summary report={data} />

          <h2 className="pt-2 text-lg font-semibold">Test details</h2>
          <section aria-label="Filters" className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <fieldset>
              <legend className="text-sm font-medium">Show</legend>
              <div className="mt-1 flex flex-wrap gap-3">
                {VIEWS.map((v) => (
                  <label key={v.value} className="inline-flex items-center gap-1.5 text-sm">
                    <input type="radio" name="status" checked={view === v.value} className="accent-indigo-600"
                           onChange={() => setParam("status", v.value === "all" ? null : v.value)} />
                    {v.label}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="min-w-56 flex-1">
              <label htmlFor="test-search" className="text-sm font-medium">Search tests</label>
              <input id="test-search" type="search" value={search.get("q") ?? ""} placeholder="e.g. golden, health, seed"
                     onChange={(e) => setParam("q", e.target.value || null)}
                     className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500" />
            </div>
          </section>

          {files.length === 0 ? (
            <EmptyState title="No tests match this view." />
          ) : (
            <ul aria-label="Test files" className="space-y-3">
              {files.map((f) => {
                const problems = f.counts.failed + f.counts.error;
                return (
                  <li key={f.path}>
                    {/* Files with failures start open; the rest start closed unless filtered or searched. */}
                    <details open={problems > 0 || view !== "all" || !!q} className="rounded-xl border border-slate-200 bg-white shadow-sm">
                      <summary className="flex cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3">
                        <span className="font-mono text-sm font-semibold">{f.path}</span>
                        <span className={`text-xs font-medium ${problems ? "text-rose-700" : "text-emerald-700"}`}>
                          {f.counts.passed}/{f.tests.length} passed
                          {problems > 0 && `, ${problems} failing`}
                          {f.counts.skipped > 0 && `, ${f.counts.skipped} skipped`}
                        </span>
                        <span className="ml-auto text-xs tabular-nums text-slate-500">{formatDuration(f.duration_s)}</span>
                      </summary>
                      <ul aria-label={`Tests in ${f.path}`} className="divide-y divide-slate-100 border-t border-slate-100 px-4">
                        {f.shown.map((t, i) => <TestRow key={`${t.name}-${i}`} test={t} />)}
                      </ul>
                    </details>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </>
  );
}
