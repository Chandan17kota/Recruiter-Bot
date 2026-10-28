import { formatScore } from "../lib/format";

function barColor(score: number) {
  if (score >= 75) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-slate-400";
}

/** A 0–100 score from the API as a bar plus its exact value (the number is always shown). */
export function ScoreBar({ score, label, size = "md" }: { score: number; label: string; size?: "sm" | "md" }) {
  const height = size === "sm" ? "h-1.5" : "h-2.5";
  return (
    <div className="flex items-center gap-2">
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
        aria-valuetext={formatScore(score)}
        className={`w-full overflow-hidden rounded-full bg-slate-200 ${height}`}
      >
        <div className={`${height} rounded-full ${barColor(score)}`} style={{ width: `${Math.min(Math.max(score, 0), 100)}%` }} />
      </div>
    </div>
  );
}
