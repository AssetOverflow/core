import { useCallback, useEffect, useRef } from "react";

/**
 * A single-slot setTimeout owned by the component lifecycle.
 *
 * Scheduling replaces any pending timeout; unmount clears it. This prevents
 * the bare-handler `setTimeout` pattern from firing state updates after
 * unmount and from holding the event loop open at test teardown.
 */
export function useManagedTimeout(): (fn: () => void, ms: number) => void {
  const ref = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    return () => {
      if (ref.current !== undefined) clearTimeout(ref.current);
    };
  }, []);

  return useCallback((fn: () => void, ms: number) => {
    if (ref.current !== undefined) clearTimeout(ref.current);
    ref.current = setTimeout(fn, ms);
  }, []);
}
