import type { Availability } from "../api/types";
import { AVAILABILITY_LABEL } from "../lib/format";

const AVAILABILITY_STYLE: Record<Availability, string> = {
  immediate: "bg-emerald-50 text-emerald-800 ring-emerald-600/20",
  two_weeks: "bg-sky-50 text-sky-800 ring-sky-600/20",
  not_looking: "bg-slate-100 text-slate-700 ring-slate-500/20",
  unknown: "bg-amber-50 text-amber-800 ring-amber-600/20",
};

export function AvailabilityBadge({ value }: { value: Availability }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${AVAILABILITY_STYLE[value]}`}>
      {AVAILABILITY_LABEL[value]}
    </span>
  );
}

type Tone = "neutral" | "matched" | "missing";

const TONE_STYLE: Record<Tone, string> = {
  neutral: "bg-white text-slate-700 ring-slate-300",
  matched: "bg-emerald-50 text-emerald-800 ring-emerald-600/30",
  missing: "bg-white text-slate-500 ring-slate-300 ring-dashed line-through decoration-slate-400",
};

// Icons, not just colour, distinguish matched from missing terms.
const TONE_ICON: Record<Tone, string> = { neutral: "", matched: "✓ ", missing: "✗ " };
const TONE_SR: Record<Tone, string> = { neutral: "", matched: "has: ", missing: "missing: " };

export function Chip({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return (
    <li className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE_STYLE[tone]}`}>
      <span aria-hidden="true">{TONE_ICON[tone]}</span>
      <span className="sr-only">{TONE_SR[tone]}</span>
      {label}
    </li>
  );
}

export function ChipList({ items, tone, label }: { items: readonly string[]; tone?: Tone; label: string }) {
  if (!items.length) return null;
  return (
    <ul aria-label={label} className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <Chip key={item} label={item} tone={tone} />
      ))}
    </ul>
  );
}

/** Matched terms first, then missing ones, as returned by the API. */
export function MatchedMissing({ matched, missing, label }: { matched: string[]; missing: string[]; label: string }) {
  if (!matched.length && !missing.length) return null;
  return (
    <ul aria-label={label} className="flex flex-wrap gap-1.5">
      {matched.map((s) => (
        <Chip key={`m-${s}`} label={s} tone="matched" />
      ))}
      {missing.map((s) => (
        <Chip key={`x-${s}`} label={s} tone="missing" />
      ))}
    </ul>
  );
}
