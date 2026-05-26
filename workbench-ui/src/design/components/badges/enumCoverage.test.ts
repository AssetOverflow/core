import { describe, expect, it } from "vitest";
import snapshot from "../../../../enum-snapshot.json";
import {
  epistemicStateMeta,
  groundingSourceMeta,
  normativeClearanceMeta,
  reviewStateMeta,
} from "./mappings";

function expectExactCoverage(name: string, engineValues: string[], uiValues: string[]) {
  expect(
    uiValues.toSorted(),
    `${name} badge mapping must exactly match engine enum values`,
  ).toEqual(engineValues.toSorted());
  expect(new Set(uiValues).size, `${name} badge mapping has duplicate values`).toBe(uiValues.length);
}

describe("build-time enum coverage", () => {
  it("tracks every ratified EpistemicState value exactly once", () => {
    expectExactCoverage(
      "EpistemicState",
      snapshot.EpistemicState,
      Object.keys(epistemicStateMeta),
    );
  });

  it("tracks every ratified NormativeClearance value exactly once", () => {
    expectExactCoverage(
      "NormativeClearance",
      snapshot.NormativeClearance,
      Object.keys(normativeClearanceMeta),
    );
  });

  it("tracks every ratified ReviewState value exactly once", () => {
    expectExactCoverage("ReviewState", snapshot.ReviewState, Object.keys(reviewStateMeta));
  });

  it("tracks every ratified GroundingSource value exactly once", () => {
    expectExactCoverage(
      "GroundingSource",
      snapshot.GroundingSource,
      Object.keys(groundingSourceMeta),
    );
  });
});
