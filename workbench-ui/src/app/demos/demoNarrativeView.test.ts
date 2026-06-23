import { describe, expect, it } from "vitest";
import type { DemoNarrative } from "../../types/demoNarrative";
import {
  DEMO_PARTNER_BLURB,
  demoNarrativeValidationWarnings,
  demoStepHonestyPair,
} from "./demoNarrativeView";

const narrative: DemoNarrative = {
  narrative_id: "deterministic-turn",
  title: "Deterministic Turn Evidence",
  summary: "Chat to Trace to Replay",
  steps: [
    {
      step_id: "trace",
      order: 1,
      kind: "evidence",
      title: "Open Trace",
      claim: "The journaled turn has trace evidence.",
      what_this_proves: "The selected turn has recorded evidence.",
      what_this_does_not_prove: "It does not prove answer correctness by itself.",
      evidence_links: [
        {
          label: "Trace",
          route: "/trace/1",
          artifact_id: "turn:1",
          digest: "sha256:abc",
          reproducer: "curl /trace/1",
        },
      ],
      failure_mode: null,
    },
  ],
};

describe("demo narrative view helpers", () => {
  it("states the partner demo thesis", () => {
    expect(DEMO_PARTNER_BLURB).toContain("frontier model can propose");
    expect(DEMO_PARTNER_BLURB).toContain("CORE can govern");
    expect(DEMO_PARTNER_BLURB).toContain("Workbench can prove");
  });

  it("accepts valid narratives", () => {
    expect(demoNarrativeValidationWarnings(narrative)).toEqual([]);
  });

  it("requires both proof and non-proof claims", () => {
    expect(
      demoNarrativeValidationWarnings({
        ...narrative,
        steps: [
          {
            ...narrative.steps[0],
            what_this_proves: "",
            what_this_does_not_prove: "",
          },
        ],
      }),
    ).toEqual([
      "step trace is missing what_this_proves",
      "step trace is missing what_this_does_not_prove",
    ]);
  });

  it("requires route-shaped evidence links", () => {
    expect(
      demoNarrativeValidationWarnings({
        ...narrative,
        steps: [
          {
            ...narrative.steps[0],
            evidence_links: [
              {
                label: "bad",
                route: "trace/1",
                artifact_id: null,
                digest: null,
                reproducer: null,
              },
            ],
          },
        ],
      }),
    ).toEqual(["step trace has non-route evidence link: trace/1"]);
  });

  it("renders honesty pair", () => {
    expect(demoStepHonestyPair(narrative.steps[0])).toBe(
      "Proves: The selected turn has recorded evidence. / Does not prove: It does not prove answer correctness by itself.",
    );
  });
});
