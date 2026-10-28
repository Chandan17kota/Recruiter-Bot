import { useEffect, useRef, useState } from "react";

import type { MatchFilters as Filters } from "../api/queries";
import { AVAILABILITIES, type Availability } from "../api/types";
import { AVAILABILITY_LABEL } from "../lib/format";

const COMMIT_DELAY_MS = 300;

function PercentSlider({ id, label, value, onCommit }: { id: string; label: string; value: number; onCommit: (v: number) => void }) {
  // Local state while dragging; the URL (and so the API request) updates once the user pauses.
  const [draft, setDraft] = useState(value);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => setDraft(value), [value]); // follow external changes such as "Reset"
  useEffect(() => () => clearTimeout(timer.current), []);

  const change = (v: number) => {
    setDraft(v);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => onCommit(v), COMMIT_DELAY_MS);
  };

  return (
    <div className="min-w-48 flex-1">
      <div className="flex items-baseline justify-between">
        <label htmlFor={id} className="text-sm font-medium">{label}</label>
        <output htmlFor={id} className="text-sm tabular-nums text-slate-600">≥ {draft}</output>
      </div>
      <input
        id={id}
        type="range"
        min={0}
        max={100}
        step={1}
        value={draft}
        onChange={(e) => change(Number(e.target.value))}
        className="mt-1 w-full accent-indigo-600"
      />
    </div>
  );
}

export function AvailabilityCheckboxes({ value, onChange }: { value: Availability[]; onChange: (v: Availability[]) => void }) {
  const toggle = (a: Availability) => onChange(value.includes(a) ? value.filter((x) => x !== a) : [...value, a]);
  return (
    <fieldset>
      <legend className="text-sm font-medium">Availability</legend>
      <div className="mt-1 flex flex-wrap gap-3">
        {AVAILABILITIES.map((a) => (
          <label key={a} className="inline-flex items-center gap-1.5 text-sm">
            <input type="checkbox" checked={value.includes(a)} onChange={() => toggle(a)} className="accent-indigo-600" />
            {AVAILABILITY_LABEL[a]}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function MatchFilters({
  filters,
  onChange,
  onReset,
  isFiltered,
  showAvailability,
}: {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
  isFiltered: boolean;
  showAvailability: boolean;
}) {
  return (
    <section aria-label="Filters" className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-end gap-6">
        <PercentSlider id="min-score" label="Minimum score" value={filters.minScore}
                       onCommit={(v) => onChange({ minScore: v })} />
        <PercentSlider id="min-coverage" label="Minimum skill coverage %" value={filters.minSkillCoverage}
                       onCommit={(v) => onChange({ minSkillCoverage: v })} />
        {showAvailability && (
          <AvailabilityCheckboxes value={filters.availability} onChange={(availability) => onChange({ availability })} />
        )}
        <button
          type="button"
          onClick={onReset}
          disabled={!isFiltered}
          className="rounded-md px-3 py-1.5 text-sm font-medium text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Reset filters
        </button>
      </div>
    </section>
  );
}
