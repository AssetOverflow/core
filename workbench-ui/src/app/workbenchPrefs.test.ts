import { afterEach, describe, expect, it } from "vitest";
import {
  DEFAULT_PREFS,
  getWorkbenchPrefs,
  setWorkbenchPref,
} from "./workbenchPrefs";

const PREFS_KEY = "core-workbench-prefs";

describe("workbenchPrefs", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("returns defaults when nothing is stored", () => {
    expect(getWorkbenchPrefs()).toEqual(DEFAULT_PREFS);
  });

  it("persists a pref and reads it back (survives reload)", () => {
    setWorkbenchPref("landingRoute", "vault");
    setWorkbenchPref("inspectorDefaultOpen", true);
    // a fresh read models a page reload — values survive
    expect(getWorkbenchPrefs()).toEqual({
      landingRoute: "vault",
      inspectorDefaultOpen: true,
    });
  });

  it("falls back to defaults for an invalid stored landing route", () => {
    localStorage.setItem(
      PREFS_KEY,
      JSON.stringify({ landingRoute: "not-a-route", inspectorDefaultOpen: "yes" }),
    );
    expect(getWorkbenchPrefs()).toEqual(DEFAULT_PREFS);
  });

  it("falls back to defaults on malformed JSON", () => {
    localStorage.setItem(PREFS_KEY, "{not json");
    expect(getWorkbenchPrefs()).toEqual(DEFAULT_PREFS);
  });

  it("merges a partial update without dropping the other pref", () => {
    setWorkbenchPref("inspectorDefaultOpen", true);
    setWorkbenchPref("landingRoute", "packs");
    expect(getWorkbenchPrefs()).toEqual({
      landingRoute: "packs",
      inspectorDefaultOpen: true,
    });
  });
});
