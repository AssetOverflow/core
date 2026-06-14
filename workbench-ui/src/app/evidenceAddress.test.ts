import { describe, expect, it } from "vitest";
import type { EvidenceSubject } from "./evidenceContext";
import {
  type AddressableSubject,
  INSPECT_PARAM,
  inspectValueToSubject,
  isAddressable,
  sameIdentity,
  subjectToInspectValue,
  subjectToUrl,
  urlToSubject,
} from "./evidenceAddress";

// Simulates React Router's contribution to urlToSubject: match the path
// against the app's route patterns and produce the params record.
function routerParamsFor(url: string): Record<string, string | undefined> {
  const pathname = new URL(url, "http://localhost").pathname;
  const [, base, raw] = pathname.split("/");
  const segment = raw === undefined ? undefined : decodeURIComponent(raw);
  switch (base) {
    case "trace":
      return segment === undefined ? {} : { turnId: segment };
    case "proposals":
      return segment === undefined ? {} : { proposalId: segment };
    case "runs":
      return segment === undefined ? {} : { sessionId: segment };
    case "packs":
      return segment === undefined ? {} : { packId: segment };
    case "logos":
      return segment === undefined ? {} : { logosPackId: segment };
    case "evals":
      return segment === undefined ? {} : { laneId: segment };
    case "replay":
      return segment === undefined ? {} : { artifactId: segment };
    default:
      return {};
  }
}

function roundTrip(subject: AddressableSubject) {
  const url = subjectToUrl(subject);
  const search = new URL(url, "http://localhost").searchParams;
  return urlToSubject(routerParamsFor(url), search);
}

const KINDS: Array<{ name: string; subject: AddressableSubject; path: string }> = [
  { name: "turn", subject: { kind: "turn", turnId: 42 }, path: "/trace/42" },
  {
    name: "proposal",
    subject: { kind: "proposal", proposalId: "proposal-pending-001abcdef" },
    path: "/proposals/proposal-pending-001abcdef",
  },
  {
    name: "eval_result",
    subject: { kind: "eval_result", lane: "gsm8k_math" },
    path: "/evals/gsm8k_math",
  },
  {
    name: "artifact",
    subject: { kind: "artifact", artifactId: "art-trace-1" },
    path: "/replay/art-trace-1",
  },
  {
    name: "run",
    subject: { kind: "run", sessionId: "session-1" },
    path: "/runs/session-1",
  },
  {
    name: "pack",
    subject: { kind: "pack", packId: "en/core pack" },
    path: "/packs/en%2Fcore%20pack",
  },
  {
    name: "logos_pack",
    subject: { kind: "logos_pack", packId: "he_logos_micro_v1" },
    path: "/logos/he_logos_micro_v1",
  },
];

const INSPECT_ONLY_KINDS: Array<{ name: string; subject: AddressableSubject; path: string }> = [
  {
    name: "vault_entry",
    subject: { kind: "vault_entry", entryIndex: 7 },
    path: "/vault?inspect=vault%3A7",
  },
  {
    name: "audit_event",
    subject: { kind: "audit_event", eventId: "audit:event/1" },
    path: "/audit?inspect=audit%3Aaudit%3Aevent%2F1",
  },
  {
    name: "calibration_class",
    subject: { kind: "calibration_class", className: "additive class" },
    path: "/calibration?inspect=calibration%3Aadditive+class",
  },
];

describe("subjectToUrl", () => {
  it.each(KINDS)("addresses a $name subject canonically", ({ subject, path }) => {
    expect(subjectToUrl(subject)).toBe(path);
  });

  it.each(INSPECT_ONLY_KINDS)(
    "addresses inspect-only $name subject through ?inspect=",
    ({ subject, path }) => {
      expect(subjectToUrl(subject)).toBe(path);
    },
  );

  it("percent-encodes ids containing reserved characters", () => {
    const url = subjectToUrl({ kind: "proposal", proposalId: "a/b c?d" });
    expect(url).toBe("/proposals/a%2Fb%20c%3Fd");
  });

  it("preserves math proposal corridor in canonical addresses", () => {
    const url = subjectToUrl({
      kind: "proposal",
      proposalId: "math-proposal-1",
      domain: "math",
    });
    expect(url).toBe("/proposals/math-proposal-1?domain=math");
  });

  it("appends ?inspect= when the inspector holds a different subject", () => {
    const url = subjectToUrl(
      { kind: "proposal", proposalId: "abc" },
      { kind: "turn", turnId: 7 },
    );
    expect(url).toBe("/proposals/abc?inspect=turn%3A7");
  });

  it("omits ?inspect= for the same subject, an absent inspect, or kind none", () => {
    const subject: AddressableSubject = { kind: "proposal", proposalId: "abc" };
    expect(subjectToUrl(subject, { kind: "proposal", proposalId: "abc" })).toBe(
      "/proposals/abc",
    );
    expect(subjectToUrl(subject, null)).toBe("/proposals/abc");
    expect(subjectToUrl(subject, { kind: "none" })).toBe("/proposals/abc");
  });
});

describe("urlToSubject round-trip", () => {
  it.each(KINDS)("recovers a $name subject from its URL", ({ subject }) => {
    const { route, inspect } = roundTrip(subject);
    expect(route).not.toBeNull();
    expect(sameIdentity(route!, subject)).toBe(true);
    expect(inspect).toBeNull();
  });

  it.each(INSPECT_ONLY_KINDS)(
    "recovers an inspect-only $name subject from its URL",
    ({ subject }) => {
      const url = subjectToUrl(subject);
      const search = new URL(url, "http://localhost").searchParams;
      const { route, inspect } = urlToSubject(routerParamsFor(url), search);
      expect(route).toBeNull();
      expect(inspect).not.toBeNull();
      expect(sameIdentity(inspect!, subject)).toBe(true);
    },
  );

  it("recovers math proposal domain from the route query", () => {
    const subject: AddressableSubject = {
      kind: "proposal",
      proposalId: "math-proposal-1",
      domain: "math",
    };
    const { route } = roundTrip(subject);
    expect(route).toEqual(subject);
  });

  it("recovers ids containing reserved characters", () => {
    const subject: AddressableSubject = {
      kind: "artifact",
      artifactId: "art/with space:colon",
    };
    const { route } = roundTrip(subject);
    expect(route).toEqual({ kind: "artifact", artifactId: "art/with space:colon" });
  });

  it("recovers both route and inspect subjects from a full address", () => {
    const url = subjectToUrl(
      { kind: "eval_result", lane: "gsm8k_math" },
      { kind: "proposal", proposalId: "abc" },
    );
    const search = new URL(url, "http://localhost").searchParams;
    const { route, inspect } = urlToSubject(routerParamsFor(url), search);
    expect(route).toEqual({ kind: "eval_result", lane: "gsm8k_math" });
    expect(inspect).toEqual({ kind: "proposal", proposalId: "abc" });
  });
});

describe("urlToSubject malformed input", () => {
  it.each([
    ["non-numeric turn id", { turnId: "abc" }],
    ["negative turn id", { turnId: "-1" }],
    ["fractional turn id", { turnId: "1.5" }],
    ["overflowing turn id", { turnId: "99999999999999999999" }],
    ["empty proposal id", { proposalId: "" }],
    ["empty session id", { sessionId: "" }],
    ["empty pack id", { packId: "" }],
    ["empty logos pack id", { logosPackId: "" }],
    ["empty lane id", { laneId: "" }],
    ["empty artifact id", { artifactId: "" }],
    ["no params at all", {}],
  ] as Array<[string, Record<string, string | undefined>]>)(
    "returns route null for %s",
    (_label, params) => {
      const { route } = urlToSubject(params, new URLSearchParams());
      expect(route).toBeNull();
    },
  );

  it.each([
    ["garbage", "garbage"],
    ["unknown kind", "bogus:1"],
    ["empty id", "proposal:"],
    ["empty kind", ":abc"],
    ["non-numeric turn", "turn:abc"],
    ["non-numeric vault entry", "vault:abc"],
    ["empty value", ""],
  ])("returns inspect null for %s", (_label, value) => {
    const params = new URLSearchParams();
    params.set(INSPECT_PARAM, value);
    const { inspect } = urlToSubject({}, params);
    expect(inspect).toBeNull();
  });

  it("never throws on arbitrary junk", () => {
    const junk = ["::::", "turn:", "🦊", "a".repeat(10_000), "%%%"];
    for (const value of junk) {
      const params = new URLSearchParams();
      params.set(INSPECT_PARAM, value);
      expect(() => urlToSubject({ turnId: value }, params)).not.toThrow();
    }
  });
});

describe("inspect value codec", () => {
  it.each(KINDS)("round-trips a $name inspect value", ({ subject }) => {
    const recovered = inspectValueToSubject(subjectToInspectValue(subject));
    expect(recovered).not.toBeNull();
    expect(sameIdentity(recovered!, subject)).toBe(true);
  });

  it.each(INSPECT_ONLY_KINDS)("round-trips a $name inspect value", ({ subject }) => {
    const recovered = inspectValueToSubject(subjectToInspectValue(subject));
    expect(recovered).not.toBeNull();
    expect(sameIdentity(recovered!, subject)).toBe(true);
  });

  it("preserves ids containing colons (splits on the first only)", () => {
    expect(inspectValueToSubject("proposal:a:b")).toEqual({
      kind: "proposal",
      proposalId: "a:b",
    });
  });

  it("returns null for null input", () => {
    expect(inspectValueToSubject(null)).toBeNull();
  });
});

describe("isAddressable / sameIdentity", () => {
  it("treats none as not addressable", () => {
    expect(isAddressable({ kind: "none" })).toBe(false);
    expect(isAddressable({ kind: "turn", turnId: 1 })).toBe(true);
  });

  it("compares identity, ignoring loaded data", () => {
    const a: EvidenceSubject = { kind: "turn", turnId: 1 };
    const b: EvidenceSubject = { kind: "turn", turnId: 1 };
    const c: EvidenceSubject = { kind: "turn", turnId: 2 };
    expect(sameIdentity(a, b)).toBe(true);
    expect(sameIdentity(a, c)).toBe(false);
    expect(sameIdentity(a, { kind: "proposal", proposalId: "1" })).toBe(false);
    expect(
      sameIdentity(
        { kind: "proposal", proposalId: "same", domain: "math" },
        { kind: "proposal", proposalId: "same" },
      ),
    ).toBe(false);
    expect(sameIdentity({ kind: "none" }, { kind: "none" })).toBe(true);
  });
});

describe("logos sub-entity addresses (LG-3)", () => {
  const PACK = "he_logos_micro_v1";
  const subEntities: Array<{ subject: AddressableSubject; inspect: string }> = [
    {
      subject: { kind: "logos_entry", packId: PACK, entryId: "he-001" },
      inspect: `logos_entry:${PACK}/he-001`,
    },
    {
      subject: { kind: "logos_gloss", packId: PACK, glossId: "gloss-1" },
      inspect: `logos_gloss:${PACK}/gloss-1`,
    },
    {
      subject: { kind: "logos_morphology", packId: PACK, morphologyId: "he-morph-001" },
      inspect: `logos_morphology:${PACK}/he-morph-001`,
    },
  ];

  it.each(subEntities)(
    "addresses $subject.kind under the pack route with an inspect value",
    ({ subject, inspect }) => {
      expect(subjectToInspectValue(subject)).toBe(inspect);
      const url = subjectToUrl(subject);
      expect(url).toBe(`/logos/${PACK}?${INSPECT_PARAM}=${encodeURIComponent(inspect)}`);
    },
  );

  it.each(subEntities)(
    "round-trips $subject.kind: route resolves to the pack, inspect to the sub-entity",
    ({ subject }) => {
      const { route, inspect } = roundTrip(subject);
      expect(route).toEqual({ kind: "logos_pack", packId: PACK });
      expect(inspect).toEqual(subject);
    },
  );

  it("rejects a malformed pack-scoped inspect value (no separator)", () => {
    expect(inspectValueToSubject("logos_entry:onlypack")).toBeNull();
    expect(inspectValueToSubject("logos_gloss:trailing/")).toBeNull();
  });

  it("distinguishes a logos_pack from a logos_entry sharing the pack id", () => {
    expect(
      sameIdentity(
        { kind: "logos_pack", packId: PACK },
        { kind: "logos_entry", packId: PACK, entryId: "he-001" },
      ),
    ).toBe(false);
  });
});
