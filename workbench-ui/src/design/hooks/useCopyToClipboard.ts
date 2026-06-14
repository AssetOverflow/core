import { useCallback, useState } from "react";
import { copyText } from "../lib";
import { useManagedTimeout } from "./useManagedTimeout";

/**
 * Shared click-to-copy feedback. Returns `copied` (true for `resetMs` after a
 * successful copy) and a `copy(text)` action. Used by every copy affordance so
 * tooltip + transient confirmation behave identically across the workbench.
 */
export function useCopyToClipboard(resetMs = 1500) {
  const [copied, setCopied] = useState(false);
  const scheduleReset = useManagedTimeout();

  const copy = useCallback(
    (text: string) => {
      void copyText(text).then(() => {
        setCopied(true);
        scheduleReset(() => setCopied(false), resetMs);
      });
    },
    [scheduleReset, resetMs],
  );

  return { copied, copy };
}
