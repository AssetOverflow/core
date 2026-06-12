import {
  type ReactNode,
  type CSSProperties,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

export interface SplitPaneProps {
  direction: "horizontal" | "vertical";
  defaultSplit?: number;
  minSize?: number;
  id?: string;
  children: [ReactNode, ReactNode];
}

function storageKey(id: string) {
  return `core-split-${id}`;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function SplitPane({
  direction,
  defaultSplit = 50,
  minSize = 120,
  id,
  children,
}: SplitPaneProps) {
  const [split, setSplit] = useState(() => {
    if (id) {
      const stored = localStorage.getItem(storageKey(id));
      if (stored !== null) {
        const parsed = Number(stored);
        if (!Number.isNaN(parsed)) return parsed;
      }
    }
    return defaultSplit;
  });
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  useEffect(() => {
    if (id) localStorage.setItem(storageKey(id), String(split));
  }, [split, id]);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      dragging.current = true;
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const isHorizontal = direction === "horizontal";
      const pos = isHorizontal ? e.clientX - rect.left : e.clientY - rect.top;
      const total = isHorizontal ? rect.width : rect.height;
      if (total === 0) return;
      const minPct = (minSize / total) * 100;
      const pct = clamp((pos / total) * 100, minPct, 100 - minPct);
      setSplit(pct);
    },
    [direction, minSize],
  );

  const onPointerUp = useCallback(() => {
    dragging.current = false;
  }, []);

  const isHorizontal = direction === "horizontal";

  const containerStyle: CSSProperties = {
    display: "flex",
    flexDirection: isHorizontal ? "row" : "column",
    width: "100%",
    height: "100%",
    overflow: "hidden",
  };

  const firstStyle: CSSProperties = isHorizontal
    ? { width: `${split}%`, minWidth: minSize, overflow: "auto" }
    : { height: `${split}%`, minHeight: minSize, overflow: "auto" };

  const secondStyle: CSSProperties = isHorizontal
    ? { flex: 1, minWidth: minSize, overflow: "auto" }
    : { flex: 1, minHeight: minSize, overflow: "auto" };

  const handleStyle: CSSProperties = {
    flexShrink: 0,
    cursor: isHorizontal ? "col-resize" : "row-resize",
    background: "var(--color-border-subtle)",
    transition: `background var(--motion-duration-fast) var(--motion-ease-standard)`,
    ...(isHorizontal
      ? { width: 4, minHeight: "100%" }
      : { height: 4, minWidth: "100%" }),
  };

  return (
    <div ref={containerRef} style={containerStyle} data-testid="split-pane">
      <div style={firstStyle} data-testid="split-pane-first">
        {children[0]}
      </div>
      <div
        role="separator"
        aria-orientation={isHorizontal ? "vertical" : "horizontal"}
        aria-valuenow={Math.round(split)}
        tabIndex={0}
        style={handleStyle}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onKeyDown={(e) => {
          const step = 2;
          if (
            (isHorizontal && e.key === "ArrowLeft") ||
            (!isHorizontal && e.key === "ArrowUp")
          ) {
            e.preventDefault();
            setSplit((s) => clamp(s - step, 5, 95));
          } else if (
            (isHorizontal && e.key === "ArrowRight") ||
            (!isHorizontal && e.key === "ArrowDown")
          ) {
            e.preventDefault();
            setSplit((s) => clamp(s + step, 5, 95));
          }
        }}
        className="hover:bg-[var(--color-border-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
        data-testid="split-pane-handle"
      />
      <div style={secondStyle} data-testid="split-pane-second">
        {children[1]}
      </div>
    </div>
  );
}
