import type { Components } from "../api/types";
import { CULTURE_STATUS_LABEL, formatScore, formatWeight, formatYears } from "../lib/format";
import { MatchedMissing } from "./Chips";
import { ScoreBar } from "./ScoreBar";

function Row({ title, score, weight, children }: { title: string; score: number | null; weight: number; children: React.ReactNode }) {
  return (
    <div className="grid gap-2 py-3 sm:grid-cols-[9rem_1fr]">
      <div>
        <div className="text-sm font-semibold">{title}</div>
        <div className="text-xs text-slate-500">weight {formatWeight(weight)}</div>
      </div>
      <div className="space-y-2">
        {score == null ? (
          <div className="text-sm text-slate-500">Not scored</div>
        ) : (
          <div className="grid grid-cols-[1fr_3.5rem] items-center gap-2">
            <ScoreBar score={score} label={`${title} score`} size="sm" />
            <span className="text-right text-sm tabular-nums">{formatScore(score)}</span>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}

/** The per-component breakdown exactly as returned by the API. */
export function ScoreBreakdown({ components }: { components: Components }) {
  const { skills, experience, culture } = components;
  const cultureScored = culture.status === "scored";

  return (
    <div className="divide-y divide-slate-200">
      <Row title="Skills" score={skills.score} weight={skills.weight_applied}>
        <MatchedMissing matched={skills.matched} missing={skills.missing} label="Required skills" />
      </Row>

      <Row title="Experience" score={experience.score} weight={experience.weight_applied}>
        <p className="text-sm text-slate-600">
          {formatYears(experience.candidate_years)} against a {formatYears(experience.required_years)} minimum{" "}
          <span className={experience.meets_minimum ? "text-emerald-700" : "text-amber-700"}>
            ({experience.meets_minimum ? "meets minimum" : "below minimum"})
          </span>
        </p>
      </Row>

      <Row title="Culture" score={culture.score} weight={culture.weight_applied}>
        {cultureScored ? (
          <MatchedMissing matched={culture.matched} missing={culture.missing} label="Culture keywords" />
        ) : (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {CULTURE_STATUS_LABEL[culture.status]}. Culture was left out and the other weights were rescaled to{" "}
            {formatWeight(skills.weight_applied)} skills / {formatWeight(experience.weight_applied)} experience.
          </p>
        )}
      </Row>
    </div>
  );
}
