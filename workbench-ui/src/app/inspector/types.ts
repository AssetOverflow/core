/**
 * Discriminated union of inspector-visible entities.
 *
 * Read-only by addendum §1: the inspector renders these entities without
 * offering write paths. Any future write path must come through the
 * owning route's proposal-only or mutating pipeline, not from the
 * inspector pane.
 */
export type InspectorEntity =
  | { kind: "artifact"; artifactId: string }
  | { kind: "proposal"; proposalId: string }
  | { kind: "trace-node"; artifactId: string; nodeId?: string }
  | { kind: "replay-diff"; artifactId: string };

export interface InspectorState {
  entity: InspectorEntity | null;
  collapsed: boolean;
}

export const DEFAULT_INSPECTOR_STATE: InspectorState = {
  entity: null,
  collapsed: true,
};
