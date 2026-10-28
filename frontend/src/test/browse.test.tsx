import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { lastRequest, renderAt } from "./render";
import { API, envelope, fixtures, requests, server } from "./server";

describe("jobs list", () => {
  it("lists every job with a link to its matches", async () => {
    renderAt("/jobs");
    const list = await screen.findByRole("list", { name: "Jobs" });
    const links = within(list).getAllByRole("link");
    expect(links).toHaveLength(fixtures.jobs.total);
    expect(within(list).getByRole("link", { name: /Backend Detective/ })).toHaveAttribute("href", "/jobs/1");
  });

  it("redirects / to the jobs list", async () => {
    const { router } = renderAt("/");
    await screen.findByRole("list", { name: "Jobs" });
    expect(router.state.location.pathname).toBe("/jobs");
  });

  it("shows the error envelope's message when the API fails", async () => {
    server.use(http.get(`${API}/jobs`, () => envelope(500, "INTERNAL_ERROR", "An internal error occurred")));
    renderAt("/jobs");
    expect(await screen.findByText("An internal error occurred")).toBeInTheDocument();
  });
});

describe("candidates list", () => {
  it("lists every candidate", async () => {
    renderAt("/candidates");
    const list = await screen.findByRole("list", { name: "Candidates" });
    expect(within(list).getAllByRole("link")).toHaveLength(15);
    expect(within(list).getByRole("link", { name: /Sherlock H\./ })).toHaveAttribute("href", "/candidates/1");
  });

  it("filters by availability through the URL and the API", async () => {
    const user = userEvent.setup();
    server.use(http.get(`${API}/candidates`, ({ request }) => {
      const wanted = new URL(request.url).searchParams.getAll("availability");
      const rows = fixtures.candidates.candidates.filter((c) => !wanted.length || wanted.includes(c.availability));
      return HttpResponse.json({ filters_applied: { availability: wanted.length ? wanted : null }, total: rows.length, candidates: rows });
    }));
    const { search } = renderAt("/candidates");
    await screen.findByRole("list", { name: "Candidates" });

    await user.click(screen.getByRole("checkbox", { name: "Not looking" }));
    await waitFor(() => expect(search().getAll("availability")).toEqual(["not_looking"]));
    await waitFor(() => expect(within(screen.getByRole("list", { name: "Candidates" })).getAllByRole("link")).toHaveLength(4));
    expect(lastRequest(requests, "/candidates")!.searchParams.getAll("availability")).toEqual(["not_looking"]);
  });
});

describe("app shell", () => {
  it("shows a banner when the database is unavailable", async () => {
    server.use(http.get(`${API}/health`, () => HttpResponse.json({ status: "degraded", database: "unavailable" }, { status: 503 })));
    renderAt("/about");
    expect(await screen.findByText(/database is unavailable/i)).toBeInTheDocument();
  });

  it("shows no banner when healthy", async () => {
    renderAt("/about");
    await screen.findByRole("heading", { name: "How scoring works" });
    await waitFor(() => expect(lastRequest(requests, "/health")).toBeDefined());
    expect(screen.queryByText(/unavailable|cannot reach/i)).not.toBeInTheDocument();
  });

  it("renders a not-found page for unknown routes", async () => {
    renderAt("/nope");
    expect(await screen.findByText("Page not found")).toBeInTheDocument();
  });
});
