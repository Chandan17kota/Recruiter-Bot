import { http, HttpResponse } from "msw";

import { ApiError, apiGet, buildQuery } from "../api/client";
import { filtersFromSearch, parseAvailability, parsePercent } from "../hooks/useUrlFilters";
import { formatScore, formatWeight } from "../lib/format";
import { parseId } from "../lib/params";
import { API, envelope, server } from "./server";

describe("URL filter parsing", () => {
  it.each([
    [null, 0], ["", 0], ["50", 50], ["12.5", 12.5], ["0", 0], ["100", 100],
    ["150", 0], ["-1", 0], ["abc", 0], ["NaN", 0], ["Infinity", 0],
  ])("parsePercent(%j) -> %j", (raw, expected) => {
    expect(parsePercent(raw)).toBe(expected);
  });

  it("keeps known availability values only, de-duplicated, in a fixed order", () => {
    expect(parseAvailability(["not_looking", "bogus", "immediate", "immediate"])).toEqual(["immediate", "not_looking"]);
  });

  it("reads all filters from a query string", () => {
    expect(filtersFromSearch(new URLSearchParams("min_score=40&min_skill_coverage=bad&availability=two_weeks"))).toEqual({
      minScore: 40, minSkillCoverage: 0, availability: ["two_weeks"],
    });
  });
});

describe("route ids", () => {
  it.each([["1", 1], ["42", 42], ["0", null], ["-1", null], ["1.5", null], ["abc", null], ["01", null], ["99999999999", null], [undefined, null]])(
    "parseId(%j) -> %j",
    (raw, expected) => expect(parseId(raw)).toBe(expected),
  );
});

describe("formatting (display only)", () => {
  it("shows API scores with two decimals without changing them", () => {
    expect(formatScore(92.5)).toBe("92.50");
    expect(formatScore(18.75)).toBe("18.75");
  });

  it("shows weights as percentages", () => {
    expect(formatWeight(0.6)).toBe("60%");
    expect(formatWeight(0.7059)).toBe("70.59%");
    expect(formatWeight(0)).toBe("0%");
  });
});

describe("API client", () => {
  it("repeats array parameters and drops empty ones", () => {
    expect(buildQuery({ availability: ["immediate", "two_weeks"], min_score: 40, x: null })).toBe(
      "?availability=immediate&availability=two_weeks&min_score=40",
    );
    expect(buildQuery({})).toBe("");
  });

  it("turns the error envelope into an ApiError", async () => {
    server.use(http.get(`${API}/jobs`, () => envelope(503, "DATABASE_UNAVAILABLE", "down")));
    const err = await apiGet("/jobs").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 503, code: "DATABASE_UNAVAILABLE", message: "down", isUnavailable: true });
  });

  it("reports a network failure as status 0", async () => {
    server.use(http.get(`${API}/jobs`, () => HttpResponse.error()));
    const err = await apiGet("/jobs").catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 0, code: "NETWORK_ERROR", isUnavailable: true });
  });

  it("handles a non-envelope error body", async () => {
    server.use(http.get(`${API}/jobs`, () => new HttpResponse("<html>bad gateway</html>", { status: 502 })));
    const err = await apiGet("/jobs").catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 502, code: "HTTP_ERROR" });
  });
});
