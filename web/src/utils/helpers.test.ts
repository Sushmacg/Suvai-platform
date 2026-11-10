import { describe, expect, it } from "vitest";
import { addDays, isoDate } from "./dates";
import { mapsLink, rupees, timeRange } from "./format";
import { parseCoords } from "./maps";

describe("parseCoords", () => {
  it("reads @lat,lng links", () => expect(parseCoords("https://www.google.com/maps/place/Stall/@12.9716,77.5946,15z")).toEqual([12.9716, 77.5946]));
  it("reads !3d!4d links", () => expect(parseCoords("https://x/data=!3d12.5!4d76.1")).toEqual([12.5, 76.1]));
  it("reads q=lat,lng links", () => expect(parseCoords("https://maps.google.com/?q=13.0,77.0")).toEqual([13.0, 77.0]));
  it("reads a plain pair", () => expect(parseCoords("12.97, 77.59")).toEqual([12.97, 77.59]));
  it("rejects short links", () => expect(parseCoords("https://maps.app.goo.gl/abc123")).toBeNull());
  it("rejects out-of-range values", () => expect(parseCoords("@95.0,10.0")).toBeNull());
});

describe("dates", () => {
  it("formats local dates", () => expect(isoDate(new Date(2026, 0, 5))).toBe("2026-01-05"));
  it("addDays(0) is today", () => expect(addDays(0)).toBe(isoDate()));
});

describe("format", () => {
  it("formats rupees", () => expect(rupees("73240")).toContain("73,240"));
  it("formats a time range", () => expect(timeRange("09:00:00", "13:00:00")).toBe("09:00 - 13:00"));
  it("builds a maps link", () => expect(mapsLink(12.5, 76.1)).toContain("query=12.5,76.1"));
});