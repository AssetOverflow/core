import { useCallback, useMemo, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";
import { useRegisterShortcuts, type ShortcutEntry } from "../../../app/shortcutRegistry";

const TREE_NAV_SHORTCUTS: readonly ShortcutEntry[] = [
  { id: "tree-nav-move", keys: "↑ / ↓", action: "Move through tree", order: 42 },
  { id: "tree-nav-expand", keys: "← / →", action: "Collapse / expand node", order: 43 },
];

// Registered only while the tree holds focus, so KeyboardHelp never
// advertises tree controls when no tree is interactable.
function TreeNavShortcuts() {
  useRegisterShortcuts(TREE_NAV_SHORTCUTS);
  return null;
}

type Json = unknown;

interface FlatNode {
  id: string;
  depth: number;
  label: string;
  value: Json;
  expandable: boolean;
  expanded: boolean;
}

function isContainer(value: Json): value is Record<string, Json> | Json[] {
  return value !== null && typeof value === "object";
}

// Deterministic child order: object keys sorted ascending, array indices in
// order. No layout depends on insertion order or animation.
function childEntries(value: Record<string, Json> | Json[]): [string, Json][] {
  if (Array.isArray(value)) return value.map((item, i) => [String(i), item]);
  return Object.keys(value)
    .sort()
    .map((key) => [key, (value as Record<string, Json>)[key]]);
}

function leafPreview(value: Json): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function containerPreview(value: Record<string, Json> | Json[]): string {
  return Array.isArray(value) ? `[${value.length}]` : `{${Object.keys(value).length}}`;
}

function flatten(root: Json, expanded: ReadonlySet<string>): FlatNode[] {
  const out: FlatNode[] = [];
  const walk = (label: string, value: Json, id: string, depth: number) => {
    const expandable = isContainer(value) && childEntries(value).length > 0;
    const isOpen = expandable && expanded.has(id);
    out.push({ id, depth, label, value, expandable, expanded: isOpen });
    if (isOpen && isContainer(value)) {
      for (const [childKey, childValue] of childEntries(value)) {
        walk(childKey, childValue, `${id}.${childKey}`, depth + 1);
      }
    }
  };
  if (isContainer(root)) {
    for (const [key, value] of childEntries(root)) walk(key, value, key, 0);
  }
  return out;
}

export function TreeView({ data, ariaLabel }: { data: Json; ariaLabel: string }) {
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(() => new Set());
  const [focusIndex, setFocusIndex] = useState(0);
  const [hasFocus, setHasFocus] = useState(false);
  const ref = useRef<HTMLUListElement>(null);

  const nodes = useMemo(() => flatten(data, expanded), [data, expanded]);
  const focused = nodes[Math.min(focusIndex, nodes.length - 1)];

  const toggle = useCallback((id: string, open: boolean) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (open) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (nodes.length === 0) return;
      const node = nodes[Math.min(focusIndex, nodes.length - 1)];
      switch (e.key) {
        case "ArrowDown":
        case "j":
          e.preventDefault();
          setFocusIndex((i) => Math.min(i + 1, nodes.length - 1));
          break;
        case "ArrowUp":
        case "k":
          e.preventDefault();
          setFocusIndex((i) => Math.max(i - 1, 0));
          break;
        case "ArrowRight":
          e.preventDefault();
          if (node.expandable && !node.expanded) toggle(node.id, true);
          else if (node.expandable) setFocusIndex((i) => Math.min(i + 1, nodes.length - 1));
          break;
        case "ArrowLeft":
          e.preventDefault();
          if (node.expandable && node.expanded) toggle(node.id, false);
          else {
            const parentDepth = node.depth - 1;
            for (let i = focusIndex - 1; i >= 0; i--) {
              if (nodes[i].depth === parentDepth) {
                setFocusIndex(i);
                break;
              }
            }
          }
          break;
        case "Home":
          e.preventDefault();
          setFocusIndex(0);
          break;
        case "End":
          e.preventDefault();
          setFocusIndex(nodes.length - 1);
          break;
        case "Enter":
          e.preventDefault();
          if (node.expandable) toggle(node.id, !node.expanded);
          break;
        default:
          break;
      }
    },
    [nodes, focusIndex, toggle],
  );

  if (nodes.length === 0) {
    return (
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">Empty manifest.</p>
    );
  }

  return (
    <>
      {hasFocus ? <TreeNavShortcuts /> : null}
      <ul
        ref={ref}
        role="tree"
        aria-label={ariaLabel}
        tabIndex={0}
        onFocus={() => setHasFocus(true)}
        onBlur={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node)) setHasFocus(false);
        }}
        onKeyDown={onKeyDown}
        className="m-0 grid list-none gap-0.5 p-0 font-mono text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      >
        {nodes.map((node, index) => (
          <li
            key={node.id}
            role="treeitem"
            aria-level={node.depth + 1}
            aria-expanded={node.expandable ? node.expanded : undefined}
            aria-selected={node === focused}
            onClick={() => {
              setFocusIndex(index);
              if (node.expandable) toggle(node.id, !node.expanded);
            }}
            style={{ paddingLeft: `${node.depth * 16}px` }}
            className={`flex cursor-default items-start gap-1 rounded px-1 py-0.5 ${
              hasFocus && node === focused ? "bg-[var(--color-selected-bg)]" : ""
            }`}
          >
            <span className="mt-0.5 w-3 shrink-0 text-[var(--color-text-muted)]">
              {node.expandable ? (
                <ChevronRight
                  size={11}
                  aria-hidden
                  className={node.expanded ? "rotate-90" : ""}
                />
              ) : null}
            </span>
            <span className="text-[var(--color-text-secondary)]">{node.label}</span>
            <span className="text-[var(--color-text-muted)]">:</span>
            <span className="min-w-0 break-all text-[var(--color-text-primary)]">
              {node.expandable
                ? containerPreview(node.value as Record<string, Json> | Json[])
                : leafPreview(node.value)}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}
