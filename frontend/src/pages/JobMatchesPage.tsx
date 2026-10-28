import { Link, useParams } from "react-router";

import { useJobMatches } from "../api/queries";
import { AvailabilityBadge, ChipList } from "../components/Chips";
import { MatchFilters } from "../components/MatchFilters";
import { MatchList } from "../components/MatchList";
import { MatchResults } from "../components/MatchResults";
import { useUrlFilters } from "../hooks/useUrlFilters";
import { formatYears } from "../lib/format";
import { parseId } from "../lib/params";
import { NotFoundPage } from "./NotFoundPage";

export function JobMatchesPage() {
  const jobId = parseId(useParams().id);
  return jobId == null ? <NotFoundPage what="job" /> : <JobMatches jobId={jobId} />;
}

function JobMatches({ jobId }: { jobId: number }) {
  const { filters, update, reset, isFiltered } = useUrlFilters();
  const query = useJobMatches(jobId, filters);
  const job = query.data?.job;

  return (
    <>
      <Link to="/jobs" className="text-sm text-indigo-700 hover:underline">← All jobs</Link>

      {job && (
        <header className="space-y-2">
          <h1 className="text-2xl font-bold">{job.title}</h1>
          {job.tagline && <p className="italic text-slate-600">{job.tagline}</p>}
          <p className="text-sm text-slate-600">Minimum experience: {formatYears(job.min_experience_years)}</p>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">Required skills:</span>
            <ChipList items={job.required_skills} label="Required skills" />
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">Culture keywords:</span>
            {job.culture_keywords.length ? <ChipList items={job.culture_keywords} label="Culture keywords" /> : <span className="text-slate-500">none</span>}
          </div>
        </header>
      )}

      <MatchFilters filters={filters} onChange={update} onReset={reset} isFiltered={isFiltered} showAvailability />

      <MatchResults query={query} noun="candidate" notFoundTitle="Job not found" backTo={{ to: "/jobs", label: "Back to all jobs" }}
                    onReset={reset} isFiltered={isFiltered}>
        {(data) => (
          <MatchList
            label={`Candidates ranked for ${data.job.title}`}
            items={data.matches.map((m) => ({
              key: m.candidate.id,
              match: m,
              heading: <Link to={`/candidates/${m.candidate.id}`} className="hover:underline">{m.candidate.name}</Link>,
              meta: (
                <>
                  <AvailabilityBadge value={m.candidate.availability} />
                  <span className="text-xs text-slate-500">{formatYears(m.candidate.experience_years)}</span>
                </>
              ),
              aside: m.candidate.quirk && (
                <p className="text-xs text-slate-500"><span className="font-medium">Quirk (not scored):</span> {m.candidate.quirk}</p>
              ),
            }))}
          />
        )}
      </MatchResults>
    </>
  );
}
