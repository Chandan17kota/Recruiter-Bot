import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import min50 from "./fixtures/job-1-matches-min50.json";
import { lastRequest, renderAt } from "./render";
import { API, envelope, fixtures, requests, server } from "./server";

/** The match rows of a ranked list (its direct children, not the chips nested inside). */
async function matchRows(listName: RegExp): Promise<HTMLElement[]> {
  const list = await screen.findByRole("list", { name: listName });
  return Array.from(list.children) as HTMLElement[];
}

describe("job matches page", () => {
  it("renders the API's ranking in order, with scores exactly as returned", async () => {
    renderAt("/jobs/1");
    await screen.findByRole("heading", { level: 1, name: "Backend Detective" });

    const items = await matchRows(/candidates ranked for backend detective/i);
    expect(items).toHaveLength(fixtures.job1.matches.length);
    fixtures.job1.matches.forEach((m, i) => {
      expect(within(items[i]!).getByText(m.candidate.name)).toBeInTheDocument();
      expect(within(items[i]!).getByText(m.score.toFixed(2))).toBeInTheDocument();
    });
    expect(screen.getByText("15 candidates ranked")).toBeInTheDocument();
    expect(within(items[0]!).getByText(fixtures.job1.matches[0]!.explanation)).toBeInTheDocument();
  });

  it("never recalculates: shows whatever score the API sends", async () => {
    const tampered = structuredClone(fixtures.job1);
    tampered.matches[0]!.score = 12.34; // inconsistent with its components on purpose
    server.use(http.get(`${API}/jobs/1/matches`, () => HttpResponse.json(tampered)));
    renderAt("/jobs/1");
    const [first] = await matchRows(/candidates ranked/i);
    expect(within(first!).getByText("12.34")).toBeInTheDocument();
    expect(within(first!).queryByText("92.50")).not.toBeInTheDocument();
  });

  it("marks equal scores as ties pointing at the first tied rank", async () => {
    renderAt("/jobs/2");
    await screen.findByRole("heading", { level: 1, name: "Rapid Prototyping Engineer" });
    const items = await matchRows(/candidates ranked/i);
    expect(within(items[1]!).queryByText(/tie with/i)).not.toBeInTheDocument(); // Rick, first at 85
    expect(within(items[2]!).getByText("Tie with #2")).toBeInTheDocument();     // MacGyver
    expect(within(items[4]!).getByText("Tie with #4")).toBeInTheDocument();     // inside the run of 25.00s
  });

  it("loads filters from the URL and sends them to the API", async () => {
    renderAt("/jobs/1?min_score=50&availability=immediate&availability=two_weeks");
    await screen.findByRole("heading", { level: 1, name: "Backend Detective" });

    const req = lastRequest(requests, "/jobs/1/matches")!;
    expect(req.searchParams.get("min_score")).toBe("50");
    expect(req.searchParams.getAll("availability")).toEqual(["immediate", "two_weeks"]);
    expect(screen.getByRole("checkbox", { name: "Immediate" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "2 weeks" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Not looking" })).not.toBeChecked();
    expect(screen.getByLabelText("Minimum score")).toHaveValue("50");
  });

  it("ignores invalid filter values in the URL", async () => {
    renderAt("/jobs/1?min_score=500&availability=soon");
    await screen.findByRole("heading", { level: 1, name: "Backend Detective" });
    const req = lastRequest(requests, "/jobs/1/matches")!;
    expect(req.searchParams.has("min_score")).toBe(false);
    expect(req.searchParams.has("availability")).toBe(false);
  });

  it("writes checkbox changes to the URL and refetches", async () => {
    const user = userEvent.setup();
    const { search } = renderAt("/jobs/1");
    await screen.findByRole("heading", { level: 1, name: "Backend Detective" });

    await user.click(screen.getByRole("checkbox", { name: "Immediate" }));
    await waitFor(() => expect(search().getAll("availability")).toEqual(["immediate"]));
    await waitFor(() => expect(lastRequest(requests, "/jobs/1/matches")!.searchParams.getAll("availability")).toEqual(["immediate"]));
  });

  it("writes slider changes to the URL after the user pauses", async () => {
    server.use(http.get(`${API}/jobs/1/matches`, ({ request }) =>
      HttpResponse.json(new URL(request.url).searchParams.get("min_score") === "50"
        ? min50
        : fixtures.job1),
    ));
    const { search } = renderAt("/jobs/1");
    await screen.findByText("15 candidates ranked");

    fireEvent.change(screen.getByLabelText("Minimum score"), { target: { value: "50" } });
    await waitFor(() => expect(search().get("min_score")).toBe("50"));
    expect(await screen.findByText("1 candidate ranked (filtered)")).toBeInTheDocument();
  });

  it("shows the score breakdown with the weights the API applied", async () => {
    const user = userEvent.setup();
    renderAt("/jobs/1");
    await screen.findByRole("heading", { level: 1, name: "Backend Detective" });
    const first = (await matchRows(/candidates ranked/i))[0]!;

    await user.click(within(first).getByRole("button", { name: /show score breakdown/i }));
    expect(within(first).getByText("weight 60%")).toBeInTheDocument();
    expect(within(first).getByText("weight 25%")).toBeInTheDocument();
    expect(within(first).getByText("weight 15%")).toBeInTheDocument();
    expect(within(first).getByRole("list", { name: "Culture keywords" })).toHaveTextContent("analytical");
    expect(within(first).getByText(/8 yrs against a 3 yrs minimum/)).toBeInTheDocument();
  });

  it("explains when culture was not scored and weights were rescaled", async () => {
    const user = userEvent.setup();
    const data = structuredClone(fixtures.job1);
    const m = data.matches[0]!;
    Object.assign(m.components.culture, { status: "unknown_candidate_traits", score: null, weight_applied: 0, matched: [], missing: [] });
    m.components.skills.weight_applied = 0.7059;
    m.components.experience.weight_applied = 0.2941;
    server.use(http.get(`${API}/jobs/1/matches`, () => HttpResponse.json(data)));

    renderAt("/jobs/1");
    await screen.findByRole("heading", { level: 1, name: "Backend Detective" });
    const first = (await matchRows(/candidates ranked/i))[0]!;
    await user.click(within(first).getByRole("button", { name: /show score breakdown/i }));
    expect(within(first).getByText(/Not scored: candidate traits unknown/)).toHaveTextContent("70.59% skills / 29.41% experience");
  });

  it("shows an empty state that can reset the filters", async () => {
    const user = userEvent.setup();
    server.use(http.get(`${API}/jobs/1/matches`, ({ request }) =>
      HttpResponse.json(new URL(request.url).searchParams.has("min_score")
        ? { ...fixtures.job1, total: 0, matches: [] }
        : fixtures.job1),
    ));
    const { search } = renderAt("/jobs/1?min_score=99");
    expect(await screen.findByText("No candidates match these filters.")).toBeInTheDocument();

    await user.click(within(screen.getByRole("region", { name: "Results" })).getByRole("button", { name: "Reset filters" }));
    await waitFor(() => expect(search().toString()).toBe(""));
    expect(await screen.findByText("15 candidates ranked")).toBeInTheDocument();
  });

  it("shows the API's 404 message for an unknown job", async () => {
    renderAt("/jobs/999");
    expect(await screen.findByText("Job not found")).toBeInTheDocument();
    expect(screen.getByText("Job 999 does not exist")).toBeInTheDocument();
    expect(screen.getByText("JOB_NOT_FOUND")).toBeInTheDocument();
  });

  it("shows a service-unavailable message on 503", async () => {
    server.use(http.get(`${API}/jobs/1/matches`, () => envelope(503, "DATABASE_UNAVAILABLE", "The database is unavailable")));
    renderAt("/jobs/1");
    expect(await screen.findByText("Service unavailable")).toBeInTheDocument();
  });

  it("treats a malformed id as not found without calling the API", async () => {
    renderAt("/jobs/abc");
    expect(await screen.findByText("That job doesn't exist")).toBeInTheDocument();
    expect(lastRequest(requests, "/jobs/abc/matches")).toBeUndefined();
  });
});

describe("candidate matches page", () => {
  it("renders ranked jobs with the same row and breakdown components", async () => {
    const user = userEvent.setup();
    renderAt("/candidates/1");
    await screen.findByRole("heading", { level: 1, name: "Sherlock H." });

    const items = await matchRows(/jobs ranked for sherlock/i);
    expect(items).toHaveLength(6);
    expect(within(items[0]!).getByRole("link", { name: "Backend Detective" })).toHaveAttribute("href", "/jobs/1");
    expect(within(items[0]!).getByText("92.50")).toBeInTheDocument();
    await user.click(within(items[0]!).getByRole("button", { name: /show score breakdown/i }));
    expect(within(items[0]!).getByText("weight 60%")).toBeInTheDocument();
  });

  it("offers score filters but no availability filter", async () => {
    renderAt("/candidates/1?min_skill_coverage=50");
    await screen.findByRole("heading", { level: 1, name: "Sherlock H." });
    expect(screen.queryByRole("group", { name: "Availability" })).not.toBeInTheDocument();
    expect(lastRequest(requests, "/candidates/1/matches")!.searchParams.get("min_skill_coverage")).toBe("50");
  });

  it("shows the API's 404 for an unknown candidate", async () => {
    renderAt("/candidates/77");
    expect(await screen.findByText("Candidate not found")).toBeInTheDocument();
    expect(screen.getByText("Candidate 77 does not exist")).toBeInTheDocument();
  });
});
