import type { EvidenceSubject } from "./evidenceContext";

// Evidence address codec: URL = subject.  This file owns the entire grammar —
// every EvidenceSubject kind is addressable here, including kinds whose routes
// are still placeholders (the grammar is fixed once; routes grow into it).
//
//   turn        -> /trace/<turnId>
//   proposal    -> /proposals/<proposalId>
//   eval_result -> /evals/<laneId>
//   artifact    -> /replay/<artifactId>
//   run         -> /runs/<sessionId>
//   pack        -> /packs/<packId>
//   logos_pack  -> /logos/<packId> (?inspect uses logos:<packId>)
//   logos_entry -> /logos/<packId>?inspect=logos_entry:<packId>/<entryId>
//   logos_gloss -> /logos/<packId>?inspect=logos_gloss:<packId>/<glossId>
//   logos_morphology -> /logos/<packId>?inspect=logos_morphology:<packId>/<morphologyId>
//   vault_entry -> /vault?inspect=vault:<entryIndex>
//   audit_event -> /audit?inspect=audit:<eventId>
//   calibration_class -> /calibration?inspect=calibration:<className>
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
      return (
        b.kind === "proposal" &&
        b.proposalId === a.proposalId &&
        (b.domain ?? "cognition") === (a.domain ?? "cognition")
      );
    case "eval_result":
      return b.kind === "eval_result" && b.lane === a.lane;
    case "artifact":
      return b.kind === "artifact" && b.artifactId === a.artifactId;
    case "run":
      return b.kind === "run" && b.sessionId === a.sessionId;
    case "pack":
      return b.kind === "pack" && b.packId === a.packId;
    case "logos_pack":
      return b.kind === "logos_pack" && b.packId === a.packId;
    case "logos_entry":
      return (
        b.kind === "logos_entry" &&
        b.packId === a.packId &&
        b.entryId === a.entryId
      );
    case "logos_gloss":
      return (
        b.kind === "logos_gloss" &&
        b.packId === a.packId &&
        b.glossId === a.glossId
      );
    case "logos_morphology":
      return (
        b.kind === "logos_morphology" &&
        b.packId === a.packId &&
        b.morphologyId === a.morphologyId
      );
    case "vault_entry":
      return b.kind === "vault_entry" && b.entryIndex === a.entryIndex;
    case "audit_event":
      return b.kind === "audit_event" && b.eventId === a.eventId;
    case "calibration_class":
      return b.kind === "calibration_class" && b.className === a.className;
    case "none":
      return b.kind === "none";
  }
}

interface SubjectAddress {
  path: string;
  params: URLSearchParams;
}

function emptyParams(): URLSearchParams {
  return new URLSearchParams();
}

function subjectAddress(subject: AddressableSubject): SubjectAddress {
  switch (subject.kind) {
    case "turn":
      return { path: `/trace/${subject.turnId}`, params: emptyParams() };
    case "proposal":
      {
        const params = emptyParams();
        if (subject.domain === "math") params.set("domain", "math");
        return {
          path: `/proposals/${encodeURIComponent(subject.proposalId)}`,
          params,
        };
      }
    case "eval_result":
      return { path: `/evals/${encodeURIComponent(subject.lane)}`, params: emptyParams() };
    case "artifact":
      return { path: `/replay/${encodeURIComponent(subject.artifactId)}`, params: emptyParams() };
    case "run":
      return { path: `/runs/${encodeURIComponent(subject.sessionId)}`, params: emptyParams() };
    case "pack":
      return { path: `/packs/${encodeURIComponent(subject.packId)}`, params: emptyParams() };
    case "logos_pack":
      return { path: `/logos/${encodeURIComponent(subject.packId)}`, params: emptyParams() };
    case "logos_entry":
    case "logos_gloss":
    case "logos_morphology":
      {
        const params = emptyParams();
        params.set(INSPECT_PARAM, subjectToInspectValue(subject));
        return { path: `/logos/${encodeURIComponent(subject.packId)}`, params };
      }
    case "vault_entry":
      {
        const params = emptyParams();
        params.set(INSPECT_PARAM, subjectToInspectValue(subject));
        return { path: "/vault", params };
      }
    case "audit_event":
      {
        const params = emptyParams();
        params.set(INSPECT_PARAM, subjectToInspectValue(subject));
        return { path: "/audit", params };
      }
    case "calibration_class":
      {
        const params = emptyParams();
        params.set(INSPECT_PARAM, subjectToInspectValue(subject));
        return { path: "/calibration", params };
      }
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
    case "run":
      return `run:${subject.sessionId}`;
    case "pack":
      return `pack:${subject.packId}`;
    case "logos_pack":
      return `logos:${subject.packId}`;
    case "logos_entry":
      return `logos_entry:${subject.packId}/${subject.entryId}`;
    case "logos_gloss":
      return `logos_gloss:${subject.packId}/${subject.glossId}`;
    case "logos_morphology":
      return `logos_morphology:${subject.packId}/${subject.morphologyId}`;
    case "vault_entry":
      return `vault:${subject.entryIndex}`;
    case "audit_event":
      return `audit:${subject.eventId}`;
    case "calibration_class":
      return `calibration:${subject.className}`;
  }
}

export function subjectToUrl(
  subject: AddressableSubject,
  inspect?: EvidenceSubject | null,
): string {
  const address = subjectAddress(subject);
  const params = new URLSearchParams(address.params);
  if (inspect && isAddressable(inspect) && !sameIdentity(subject, inspect)) {
    params.set(INSPECT_PARAM, subjectToInspectValue(inspect));
  }
  const query = params.toString();
  return query ? `${address.path}?${query}` : address.path;
}

function parseTurnId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const value = Number(raw);
  return Number.isSafeInteger(value) ? value : null;
}

// Pack-scoped sub-entity ids encode as `<packId>/<subId>`. Neither a pack id
// nor a lexicon/gloss/morphology/edge id contains "/", so the first slash is
// the unambiguous separator. Returns null for malformed input (never throws).
function splitPackScoped(
  raw: string,
): { packId: string; subId: string } | null {
  const sep = raw.indexOf("/");
  if (sep <= 0 || sep === raw.length - 1) return null;
  return { packId: raw.slice(0, sep), subId: raw.slice(sep + 1) };
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
    case "run":
      return { kind: "run", sessionId: id };
    case "pack":
      return { kind: "pack", packId: id };
    case "logos":
      return { kind: "logos_pack", packId: id };
    case "logos_entry": {
      const parts = splitPackScoped(id);
      return parts === null
        ? null
        : { kind: "logos_entry", packId: parts.packId, entryId: parts.subId };
    }
    case "logos_gloss": {
      const parts = splitPackScoped(id);
      return parts === null
        ? null
        : { kind: "logos_gloss", packId: parts.packId, glossId: parts.subId };
    }
    case "logos_morphology": {
      const parts = splitPackScoped(id);
      return parts === null
        ? null
        : {
            kind: "logos_morphology",
            packId: parts.packId,
            morphologyId: parts.subId,
          };
    }
    case "vault": {
      const entryIndex = parseTurnId(id);
      return entryIndex === null ? null : { kind: "vault_entry", entryIndex };
    }
    case "audit":
      return { kind: "audit_event", eventId: id };
    case "calibration":
      return { kind: "calibration_class", className: id };
    default:
      return null;
  }
}

function routeParamsToSubject(
  params: Readonly<Record<string, string | undefined>>,
  searchParams: URLSearchParams,
): AddressableSubject | null {
  // React Router populates exactly one of these keys per matched route;
  // precedence below only matters for hand-built (malformed) inputs.
  if (params.turnId !== undefined) {
    const turnId = parseTurnId(params.turnId);
    return turnId === null ? null : { kind: "turn", turnId };
  }
  if (params.proposalId !== undefined) {
    if (params.proposalId === "") return null;
    return searchParams.get("domain") === "math"
      ? { kind: "proposal", proposalId: params.proposalId, domain: "math" }
      : { kind: "proposal", proposalId: params.proposalId };
  }
  if (params.sessionId !== undefined) {
    return params.sessionId === ""
      ? null
      : { kind: "run", sessionId: params.sessionId };
  }
  if (params.packId !== undefined) {
    return params.packId === ""
      ? null
      : { kind: "pack", packId: params.packId };
  }
  if (params.logosPackId !== undefined) {
    return params.logosPackId === ""
      ? null
      : { kind: "logos_pack", packId: params.logosPackId };
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
    route: routeParamsToSubject(params, searchParams),
    inspect: inspectValueToSubject(searchParams.get(INSPECT_PARAM)),
  };
}
