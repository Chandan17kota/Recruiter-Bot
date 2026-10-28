import { NavLink, Outlet } from "react-router";

import { useHealth } from "../api/queries";

function HealthBanner() {
  const { data, isError } = useHealth();
  if (!isError && data?.database !== "unavailable") return null;
  const message = isError
    ? "Cannot reach the API server. Is the backend running on port 8000?"
    : "The database is unavailable. Results will load once it is back.";
  return (
    <div role="alert" className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-900">
      {message}
    </div>
  );
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-indigo-50 text-indigo-800" : "text-slate-600 hover:text-slate-900"}`;

export function Layout() {
  return (
    <div className="min-h-screen">
      <HealthBanner />
      <header className="border-b border-slate-200 bg-white">
        <nav aria-label="Main" className="mx-auto flex max-w-5xl flex-wrap items-center gap-2 px-4 py-3">
          <NavLink to="/" className="mr-4 text-lg font-bold">
            Recruiter Bot
          </NavLink>
          <NavLink to="/jobs" className={linkClass}>Jobs</NavLink>
          <NavLink to="/candidates" className={linkClass}>Candidates</NavLink>
          <NavLink to="/about" className={linkClass}>How scoring works</NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl space-y-6 px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
