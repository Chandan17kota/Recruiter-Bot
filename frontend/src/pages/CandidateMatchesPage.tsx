import { Link, useParams } from "react-router";

import { useCandidateMatches } from "../api/queries";
import { AvailabilityBadge, ChipList } from "../components/Chips";
import { MatchFilters } from "../components/MatchFilters";
import { MatchList } from "../components/MatchList";
import { MatchResults } from "../components/MatchResults";
import { useUrlFilters } from "../hooks/useUrlFilters";
import { formatYears } from "../lib/format";
import { parseId } from "../lib/params";
import { NotFoundPage } from "./NotFoundPage";

export function CandidateMatchesPage() {
  const candidateId = parseId(useParams().id);
  return candidateId == null ? <NotFoundPage what="candidate" /> : <CandidateMatches candidateId={candidateId} />;
}

function CandidateMatches({ candidateId }: { candidateId: number }) {
  const { filters, update, reset, isFiltered } = useUrlFilters();
  const query = useCandidateMatches(candidateId, filters);
  const candidate = query.data?.candidate;

  return (
    <>
      <Link to="/candidates" className="text-sm text-indigo-700 hover:underline">← All candidates</Link>

      {candidate && (
        <header className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold">{candidate.name}</h1>
            <AvailabilityBadge value={candidate.availability} />
            <span className="text-sm text-slate-600">{formatYears(candidate.experience_years)} experience</span>
          </div>
          {candidate.quirk && <p className="italic text-slate-600">{candidate.quirk}</p>}
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">Skills:</span>
            <ChipList items={candidate.skills} label="Skills" />
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">Traits:</span>
            {candidate.traits == null ? (
              <span className="text-amber-700">unknown</span>
            ) : candidate.traits.length ? (
              <ChipList items={candidate.traits} label="Traits" />
            ) : (
              <span className="text-slate-500">none</span>
            )}
          </div>
        </header>
      )}

      {/* Availability is a property of the candidate, so it isn't a filter here. */}
      <MatchFilters filters={filters} onChange={update} onReset={reset} isFiltered={isFiltered} showAvailability={false} />

      <MatchResults query={query} noun="job" notFoundTitle="Candidate not found"
                    backTo={{ to: "/candidates", label: "Back to all candidates" }} onReset={reset} isFiltered={isFiltered}>
        {(data) => (
          <MatchList
            label={`Jobs ranked for ${data.candidate.name}`}
            items={data.matches.map((m) => ({
              key: m.job.id,
              match: m,
              heading: <Link to={`/jobs/${m.job.id}`} className="hover:underline">{m.job.title}</Link>,
              meta: <span className="text-xs text-slate-500">min {formatYears(m.job.min_experience_years)}</span>,
              aside: m.job.tagline && <p className="text-xs italic text-slate-500">{m.job.tagline}</p>,
            }))}
          />
        )}
      </MatchResults>
    </>
  );
}
