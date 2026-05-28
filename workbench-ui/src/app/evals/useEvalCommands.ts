import { useEffect } from "react";
import { registerCommands, unregisterCommands } from "../../commands/registry";
import type { EvalLaneSummary } from "../../types/api";

export function useEvalCommands(lanes: EvalLaneSummary[]): void {
  useEffect(() => {
    const cmds = lanes.map((l) => ({
      name: `Open eval lane ${l.lane}`,
      path: `/evals?lane=${encodeURIComponent(l.lane)}`,
    }));
    registerCommands(cmds);
    return () => unregisterCommands(cmds.map((c) => c.path));
  }, [lanes]);
}
