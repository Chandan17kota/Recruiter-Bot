import { Link } from "react-router";

import { useJobs } from "../api/queries";
import { ChipList } from "../components/Chips";
import { EmptyState, ErrorState, LoadingList } from "../components/States";
import { formatYears } from "../lib/format";

export function JobsPage() {
  const { data, error, isPending } = useJobs();

  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">Jobs</h1>
        <p className="text-sm text-slate-600">Pick a job to see its candidates ranked by match score.</p>
      </div>

      {isPending ? (
        <LoadingList label="Loading jobs" />
      ) : error ? (
        <ErrorState error={error} />
      ) : data.jobs.length === 0 ? (
        <EmptyState title="No jobs yet. Load the seed with python -m scripts.init_db." />
      ) : (
        <ul aria-label="Jobs" className="grid gap-3 sm:grid-cols-2">
          {data.jobs.map((job) => (
            <li key={job.id}>
              <Link
                to={`/jobs/${job.id}`}
                className="block h-full space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-indigo-300 hover:shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <h2 className="font-semibold">{job.title}</h2>
                  <span className="shrink-0 text-xs text-slate-500">min {formatYears(job.min_experience_years)}</span>
                </div>
                {job.tagline && <p className="text-sm italic text-slate-600">{job.tagline}</p>}
                <ChipList items={job.required_skills} label={`${job.title} required skills`} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
