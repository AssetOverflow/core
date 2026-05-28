import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import {
  DEFAULT_INSPECTOR_STATE,
  type InspectorEntity,
  type InspectorState,
} from "./types";

type Action =
  | { type: "set-entity"; entity: InspectorEntity | null }
  | { type: "set-collapsed"; collapsed: boolean }
  | { type: "toggle-collapsed" };

function reducer(state: InspectorState, action: Action): InspectorState {
  switch (action.type) {
    case "set-entity":
      // Read-only invariant: never mutate; always return a new object.
      return { ...state, entity: action.entity };
    case "set-collapsed":
      if (state.collapsed === action.collapsed) return state;
      return { ...state, collapsed: action.collapsed };
    case "toggle-collapsed":
      return { ...state, collapsed: !state.collapsed };
    default:
      return state;
  }
}

interface InspectorContextValue {
  state: InspectorState;
  setEntity: (entity: InspectorEntity | null) => void;
  setCollapsed: (collapsed: boolean) => void;
  toggleCollapsed: () => void;
}

// `null` here means "no provider mounted." Hook consumers must tolerate this
// (e.g. preview pages, isolated component tests) by falling back to no-ops.
const InspectorContext = createContext<InspectorContextValue | null>(null);

export function InspectorProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, DEFAULT_INSPECTOR_STATE);

  const setEntity = useCallback(
    (entity: InspectorEntity | null) =>
      dispatch({ type: "set-entity", entity }),
    [],
  );
  const setCollapsed = useCallback(
    (collapsed: boolean) => dispatch({ type: "set-collapsed", collapsed }),
    [],
  );
  const toggleCollapsed = useCallback(
    () => dispatch({ type: "toggle-collapsed" }),
    [],
  );

  const value = useMemo<InspectorContextValue>(
    () => ({ state, setEntity, setCollapsed, toggleCollapsed }),
    [state, setEntity, setCollapsed, toggleCollapsed],
  );

  return (
    <InspectorContext.Provider value={value}>
      {children}
    </InspectorContext.Provider>
  );
}

const NOOP: InspectorContextValue = {
  state: DEFAULT_INSPECTOR_STATE,
  setEntity: () => {},
  setCollapsed: () => {},
  toggleCollapsed: () => {},
};

/**
 * Read + control inspector state. When no `InspectorProvider` is mounted
 * (preview pages, isolated component tests, design-system harness),
 * returns a no-op fallback with the default state. This keeps existing
 * tests passing while the provider rolls out incrementally.
 */
export function useInspector(): InspectorContextValue {
  return useContext(InspectorContext) ?? NOOP;
}

/**
 * Publishes an entity selection into the inspector store while the calling
 * component is mounted. On unmount (or when entity changes to null) the
 * selection is cleared.
 *
 * Pass `null` to skip publishing — useful when a route only sometimes has
 * an entity to expose (e.g. depending on URL state).
 *
 * Read-only: this hook does not write to backend services or external
 * state. It only updates the in-memory inspector context.
 */
export function useInspectorPublish(entity: InspectorEntity | null): void {
  const ctx = useContext(InspectorContext);
  // Stable JSON snapshot for the effect dependency so structural-equal
  // entities do not re-publish each render.
  const entityKey = entity ? JSON.stringify(entity) : null;

  useEffect(() => {
    if (!ctx) return;
    if (entity === null) return;
    ctx.setEntity(entity);
    return () => {
      ctx.setEntity(null);
    };
    // entity captured by entityKey; ctx is stable for the provider's lifetime
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityKey]);
}
