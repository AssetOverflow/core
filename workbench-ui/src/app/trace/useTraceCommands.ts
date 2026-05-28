import { useEffect } from "react";
import { registerCommands, unregisterCommands } from "../../commands/registry";
import type { ArtifactRef } from "../../types/api";

function shortId(id: string): string {
  return id.length <= 16 ? id : `${id.slice(0, 8)}…${id.slice(-4)}`;
}

export function useTraceCommands(traces: ArtifactRef[]): void {
  useEffect(() => {
    const cmds = traces.map((t) => ({
      name: `Open trace ${shortId(t.artifact_id)}`,
      path: `/trace?traceId=${encodeURIComponent(t.artifact_id)}`,
    }));
    registerCommands(cmds);
    return () => unregisterCommands(cmds.map((c) => c.path));
  }, [traces]);
}
