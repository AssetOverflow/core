import { useEffect } from "react";
import { registerCommands, unregisterCommands } from "../../commands/registry";
import type { ArtifactRef } from "../../types/api";

function shortId(id: string): string {
  return id.length <= 16 ? id : `${id.slice(0, 8)}…${id.slice(-4)}`;
}

export function useRunCommands(runs: ArtifactRef[]): void {
  useEffect(() => {
    const cmds = runs.map((r) => ({
      name: `Open run ${shortId(r.artifact_id)}`,
      path: `/runs?runId=${encodeURIComponent(r.artifact_id)}`,
    }));
    registerCommands(cmds);
    return () => unregisterCommands(cmds.map((c) => c.path));
  }, [runs]);
}
