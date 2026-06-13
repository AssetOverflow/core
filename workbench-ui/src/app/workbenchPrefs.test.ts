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
    setWorkbenchPref("densityMode", "compact");
    // a fresh read models a page reload — values survive
    expect(getWorkbenchPrefs()).toEqual({
      landingRoute: "vault",
      inspectorDefaultOpen: true,
      densityMode: "compact",
    });
  });

  it("falls back to defaults for invalid stored pref values", () => {
    localStorage.setItem(
      PREFS_KEY,
      JSON.stringify({
        landingRoute: "not-a-route",
        inspectorDefaultOpen: "yes",
        densityMode: "wide",
      }),
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
      densityMode: "comfortable",
    });
  });
});
