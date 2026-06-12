import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useEvidenceSubject } from "./evidenceContext";
import {
  INSPECT_PARAM,
  inspectValueToSubject,
  isAddressable,
  subjectToInspectValue,
} from "./evidenceAddress";

// Keeps `?inspect=` and the evidence context in sync.
// On first mount a valid `?inspect=` deep link restores the inspector
// (identity-only subject; the owning route loads detail).  After that the
// URL follows state: param present iff the inspector is open on an
// addressable subject.  All writes use replace — selection churn must not
// pollute history.  A malformed `?inspect=` is dropped from the URL.
export function EvidenceUrlSync() {
  const { subject, setSubject, inspectorOpen, setInspectorOpen } =
    useEvidenceSubject();
  const [searchParams, setSearchParams] = useSearchParams();
  const restoredRef = useRef(false);

  useEffect(() => {
    if (!restoredRef.current) {
      restoredRef.current = true;
      const restored = inspectValueToSubject(searchParams.get(INSPECT_PARAM));
      if (restored) {
        setSubject(restored);
        setInspectorOpen(true);
        return;
      }
    }

    const desired =
      inspectorOpen && isAddressable(subject)
        ? subjectToInspectValue(subject)
        : null;
    const current = searchParams.get(INSPECT_PARAM);
    if (desired === current) return;

    const next = new URLSearchParams(searchParams);
    if (desired === null) {
      next.delete(INSPECT_PARAM);
    } else {
      next.set(INSPECT_PARAM, desired);
    }
    setSearchParams(next, { replace: true });
  }, [
    subject,
    inspectorOpen,
    searchParams,
    setSearchParams,
    setSubject,
    setInspectorOpen,
  ]);

  return null;
}
