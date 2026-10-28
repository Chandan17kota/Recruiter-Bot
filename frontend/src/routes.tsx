import { Navigate, type RouteObject } from "react-router";

import { Layout } from "./components/Layout";
import { AboutPage } from "./pages/AboutPage";
import { CandidateMatchesPage } from "./pages/CandidateMatchesPage";
import { CandidatesPage } from "./pages/CandidatesPage";
import { JobMatchesPage } from "./pages/JobMatchesPage";
import { JobsPage } from "./pages/JobsPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/jobs" replace /> },
      { path: "jobs", element: <JobsPage /> },
      { path: "jobs/:id", element: <JobMatchesPage /> },
      { path: "candidates", element: <CandidatesPage /> },
      { path: "candidates/:id", element: <CandidateMatchesPage /> },
      { path: "about", element: <AboutPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
