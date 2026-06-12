import type { EvidenceSubject } from "./evidenceContext";

// Evidence address codec: URL = subject.  This file owns the entire grammar —
// every EvidenceSubject kind is addressable here, including kinds whose routes
// are still placeholders (the grammar is fixed once; routes grow into it).
//
//   turn        -> /trace/<turnId>
//   proposal    -> /proposals/<proposalId>
//   eval_result -> /evals/<laneId>
//   artifact    -> /replay/<artifactId>
//
// The `inspect` query param carries the inspector's subject as `<kind>:<id>`;
// its presence means the inspector is open on that subject.

export type AddressableSubject = Exclude<EvidenceSubject, { kind: "none" }>;

export const INSPECT_PARAM = "inspect";

export function isAddressable(
  subject: EvidenceSubject,
): subject is AddressableSubject {
  return subject.kind !== "none";
}

export function sameIdentity(a: EvidenceSubject, b: EvidenceSubject): boolean {
  switch (a.kind) {
    case "turn":
      return b.kind === "turn" && b.turnId === a.turnId;
    case "proposal":
      return b.kind === "proposal" && b.proposalId === a.proposalId;
    case "eval_result":
      return b.kind === "eval_result" && b.lane === a.lane;
    case "artifact":
      return b.kind === "artifact" && b.artifactId === a.artifactId;
    case "none":
      return b.kind === "none";
  }
}

function subjectPath(subject: AddressableSubject): string {
  switch (subject.kind) {
    case "turn":
      return `/trace/${subject.turnId}`;
    case "proposal":
      return `/proposals/${encodeURIComponent(subject.proposalId)}`;
    case "eval_result":
      return `/evals/${encodeURIComponent(subject.lane)}`;
    case "artifact":
      return `/replay/${encodeURIComponent(subject.artifactId)}`;
  }
}

export function subjectToInspectValue(subject: AddressableSubject): string {
  switch (subject.kind) {
    case "turn":
      return `turn:${subject.turnId}`;
    case "proposal":
      return `proposal:${subject.proposalId}`;
    case "eval_result":
      return `eval_result:${subject.lane}`;
    case "artifact":
      return `artifact:${subject.artifactId}`;
  }
}

export function subjectToUrl(
  subject: AddressableSubject,
  inspect?: EvidenceSubject | null,
): string {
  const path = subjectPath(subject);
  if (!inspect || !isAddressable(inspect) || sameIdentity(subject, inspect)) {
    return path;
  }
  const params = new URLSearchParams();
  params.set(INSPECT_PARAM, subjectToInspectValue(inspect));
  return `${path}?${params.toString()}`;
}

function parseTurnId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const value = Number(raw);
  return Number.isSafeInteger(value) ? value : null;
}

export function inspectValueToSubject(
  value: string | null,
): AddressableSubject | null {
  if (value === null) return null;
  const sep = value.indexOf(":");
  if (sep <= 0 || sep === value.length - 1) return null;
  const kind = value.slice(0, sep);
  const id = value.slice(sep + 1);
  switch (kind) {
    case "turn": {
      const turnId = parseTurnId(id);
      return turnId === null ? null : { kind: "turn", turnId };
    }
    case "proposal":
      return { kind: "proposal", proposalId: id };
    case "eval_result":
      return { kind: "eval_result", lane: id };
    case "artifact":
      return { kind: "artifact", artifactId: id };
    default:
      return null;
  }
}

function routeParamsToSubject(
  params: Readonly<Record<string, string | undefined>>,
): AddressableSubject | null {
  // React Router populates exactly one of these keys per matched route;
  // precedence below only matters for hand-built (malformed) inputs.
  if (params.turnId !== undefined) {
    const turnId = parseTurnId(params.turnId);
    return turnId === null ? null : { kind: "turn", turnId };
  }
  if (params.proposalId !== undefined) {
    return params.proposalId === ""
      ? null
      : { kind: "proposal", proposalId: params.proposalId };
  }
  if (params.laneId !== undefined) {
    return params.laneId === ""
      ? null
      : { kind: "eval_result", lane: params.laneId };
  }
  if (params.artifactId !== undefined) {
    return params.artifactId === ""
      ? null
      : { kind: "artifact", artifactId: params.artifactId };
  }
  return null;
}

export interface UrlSubjects {
  route: AddressableSubject | null;
  inspect: AddressableSubject | null;
}

// Total inverse of subjectToUrl: malformed input yields null, never throws.
// Returned subjects carry identity only — `data` loads via the route's query.
export function urlToSubject(
  params: Readonly<Record<string, string | undefined>>,
  searchParams: URLSearchParams,
): UrlSubjects {
  return {
    route: routeParamsToSubject(params),
    inspect: inspectValueToSubject(searchParams.get(INSPECT_PARAM)),
  };
}
