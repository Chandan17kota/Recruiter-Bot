import { Link } from "react-router";

export function NotFoundPage({ what }: { what?: "job" | "candidate" }) {
  const back = what === "candidate" ? { to: "/candidates", label: "Back to all candidates" } : { to: "/jobs", label: "Back to all jobs" };
  return (
    <div role="alert" className="rounded-xl border border-slate-200 bg-white p-8 text-center">
      <p className="text-lg font-semibold">{what ? `That ${what} doesn't exist` : "Page not found"}</p>
      <Link to={back.to} className="mt-3 inline-block text-sm font-medium text-indigo-700 underline">{back.label}</Link>
    </div>
  );
}
