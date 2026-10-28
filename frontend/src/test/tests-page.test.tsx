import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { renderAt } from "./render";
import { fixtures, server } from "./server";

const testNames = () =>
  screen.queryAllByRole("list", { name: /^Tests in / }).flatMap((list) =>
    Array.from(list.children).map((li) => li.querySelector(".font-mono")!.textContent),
  );

describe("tests page", () => {
  it("summarises the last run", async () => {
    renderAt("/tests");
    expect(await screen.findByText("2 of 5 tests failing")).toBeInTheDocument();
    const counts = screen.getByRole("list", { name: "Counts" });
    expect(counts).toHaveTextContent("Passed: 2");
    expect(counts).toHaveTextContent("Failed: 1");
    expect(counts).toHaveTextContent("Errors: 1");
    expect(counts).toHaveTextContent("Skipped: 1");
    expect(screen.getByText("abc1234")).toBeInTheDocument();
    expect(screen.getByText("12.50 s")).toBeInTheDocument();
  });

  it("groups tests by file and shows failure messages", async () => {
    renderAt("/tests");
    await screen.findByText("2 of 5 tests failing");
    expect(screen.getByText("tests/integration/test_api.py")).toBeInTheDocument();
    expect(screen.getByText("1/3 passed, 1 failing, 1 skipped")).toBeInTheDocument();
    expect(screen.getByText(/assert 44.99 >= 45/)).toBeInTheDocument();
    expect(screen.getByText("fixture 'env' not found")).toBeInTheDocument();
    expect(testNames()).toHaveLength(5);
  });

  it("filters by status through the URL", async () => {
    const user = userEvent.setup();
    const { search } = renderAt("/tests");
    await screen.findByText("2 of 5 tests failing");

    await user.click(screen.getByRole("radio", { name: "Failed & errors" }));
    await waitFor(() => expect(search().get("status")).toBe("problems"));
    expect(testNames()).toEqual(["test_min_score_filter", "test_weights_validation"]);
  });

  it("reads the status filter and search from a shared URL", async () => {
    renderAt("/tests?status=passed&q=golden");
    await screen.findByText("2 of 5 tests failing");
    expect(screen.getByRole("radio", { name: "Passed" })).toBeChecked();
    expect(screen.getByLabelText("Search tests")).toHaveValue("golden");
    expect(testNames()).toEqual(["test_golden_via_api"]);
  });

  it("shows an empty state when nothing matches", async () => {
    renderAt("/tests?q=no-such-test");
    expect(await screen.findByText("No tests match this view.")).toBeInTheDocument();
  });

  it("celebrates an all-green run", async () => {
    const green = structuredClone(fixtures.testReport);
    green.summary = { total: 2, passed: 2, failed: 0, error: 0, skipped: 0 };
    server.use(http.get("*/test-report.json", () => HttpResponse.json(green)));
    renderAt("/tests");
    expect(await screen.findByText("All 2 tests passed")).toBeInTheDocument();
  });

  it("warns when the run included uncommitted changes", async () => {
    server.use(http.get("*/test-report.json", () => HttpResponse.json({ ...fixtures.testReport, git_commit: "abc1234-dirty" })));
    renderAt("/tests");
    expect(await screen.findByText(/included uncommitted changes/)).toBeInTheDocument();
  });

  it.each([
    ["a 404", () => new HttpResponse(null, { status: 404 })],
    ["the dev server's index.html fallback", () => HttpResponse.html("<!doctype html><div id=root></div>")],
  ])("explains how to generate the report on %s", async (_, response) => {
    server.use(http.get("*/test-report.json", response));
    renderAt("/tests");
    expect(await screen.findByText("No test report yet.")).toBeInTheDocument();
    expect(screen.getAllByText("python -m scripts.test_report").length).toBeGreaterThan(0);
  });

  it("has no control that could start a test run", async () => {
    renderAt("/tests");
    await screen.findByText("2 of 5 tests failing");
    const main = screen.getByRole("main");
    expect(within(main).queryByRole("button", { name: /run/i })).not.toBeInTheDocument();
  });
});
