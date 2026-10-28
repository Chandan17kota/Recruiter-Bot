import { useId, useState, type ReactNode } from "react";
import { Link } from "react-router";

import type { MatchCore } from "../api/types";
import { formatPercent, formatScore } from "../lib/format";
import { ScoreBar } from "./ScoreBar";
import { ScoreBreakdown } from "./ScoreBreakdown";

export interface MatchListItem {
  key: string | number;
  match: MatchCore;
  heading: ReactNode;  // linked name or title
  meta?: ReactNode;    // badges under the heading
  aside?: ReactNode;   // display-only extras (quirk, tagline)
}

function MatchRow({ item, tiedWith }: { item: MatchListItem; tiedWith?: number }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const { match } = item;

  return (
    <li className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="grid gap-3 p-4 sm:grid-cols-[3rem_1fr_11rem] sm:items-start">
        <div className="text-2xl font-bold text-slate-400 tabular-nums" aria-label={`Rank ${match.rank}`}>
          #{match.rank}
        </div>

        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold">{item.heading}</h3>
            {item.meta}
            {tiedWith != null && (
              <Link
                to="/about#tie-breaks"
                className="rounded-full bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-800 ring-1 ring-inset ring-violet-600/20 hover:bg-violet-100"
                title={`Same score as #${tiedWith}; order set by the tie-break rules`}
              >
                Tie with #{tiedWith}
              </Link>
            )}
          </div>
          <p className="text-sm text-slate-700">{match.explanation}</p>
          {item.aside}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between">
            <span className="text-xs text-slate-500">Score</span>
            <span className="text-xl font-bold tabular-nums">{formatScore(match.score)}</span>
          </div>
          <ScoreBar score={match.score} label="Match score" />
          <div className="text-xs text-slate-500">
            Skills {match.matched_required_skill_count}/{match.required_skill_count} ({formatPercent(match.skill_coverage)})
          </div>
        </div>
      </div>

      <div className="border-t border-slate-100 px-4">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((o) => !o)}
          className="w-full py-2 text-left text-sm font-medium text-indigo-700 hover:text-indigo-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
        >
          {open ? "Hide" : "Show"} score breakdown
        </button>
        {open && (
          <div id={panelId} className="pb-3">
            <ScoreBreakdown components={match.components} />
          </div>
        )}
      </div>
    </li>
  );
}

/** Rows rendered in the order the API returned them; the frontend never re-sorts. */
export function MatchList({ items, label }: { items: MatchListItem[]; label: string }) {
  // A display hint only: for each row, the first rank of the run of adjacent rows
  // with an identical returned score (if the row isn't that first one).
  let runStart = 0;
  const tiedWith = items.map((item, i) => {
    if (i === 0 || items[i - 1]!.match.score !== item.match.score) {
      runStart = i;
      return undefined;
    }
    return items[runStart]!.match.rank;
  });

  return (
    <ol aria-label={label} className="space-y-3">
      {items.map((item, i) => (
        <MatchRow key={item.key} item={item} tiedWith={tiedWith[i]} />
      ))}
    </ol>
  );
}
