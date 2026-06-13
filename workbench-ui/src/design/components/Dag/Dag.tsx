import { useMemo, useRef, useState } from "react";
import { RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { layoutDag, type DagEdgeInput, type DagLayoutNode, type DagNodeInput } from "./layout";

export interface DagViewerProps {
  nodes: readonly DagNodeInput[];
  edges: readonly DagEdgeInput[];
  ariaLabel: string;
  height?: number;
  onInspectNode?: (node: DagLayoutNode) => void;
}

function clippedLabel(label: string) {
  return label.length > 22 ? `${label.slice(0, 19)}...` : label;
}

function edgePath(points: { x1: number; y1: number; x2: number; y2: number }) {
  const dx = Math.max(32, (points.x2 - points.x1) / 2);
  return `M ${points.x1} ${points.y1} C ${points.x1 + dx} ${points.y1}, ${points.x2 - dx} ${points.y2}, ${points.x2} ${points.y2}`;
}

export function DagViewer({
  nodes,
  edges,
  ariaLabel,
  height = 320,
  onInspectNode,
}: DagViewerProps) {
  const layout = useMemo(() => layoutDag(nodes, edges), [nodes, edges]);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [selectedId, setSelectedId] = useState<string | null>(layout.nodes[0]?.id ?? null);
  const drag = useRef<{ x: number; y: number } | null>(null);
  const selected = layout.nodes.find((node) => node.id === selectedId) ?? null;

  function selectNode(node: DagLayoutNode) {
    setSelectedId(node.id);
    onInspectNode?.(node);
  }

  function resetView() {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  }

  return (
    <div className="grid gap-3" data-testid="dag-viewer">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-xs font-semibold text-[var(--color-text-secondary)]">
            Deterministic DAG
          </div>
          <div className="font-mono text-[10px] text-[var(--color-text-muted)]">
            {layout.nodes.length} nodes / {layout.edges.length} edges
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            aria-label="Zoom out graph"
            className="inline-flex h-8 w-8 items-center justify-center rounded border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
            onClick={() => setScale((value) => Math.max(0.6, Number((value - 0.15).toFixed(2))))}
            type="button"
          >
            <ZoomOut size={15} aria-hidden />
          </button>
          <button
            aria-label="Reset graph view"
            className="inline-flex h-8 w-8 items-center justify-center rounded border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
            onClick={resetView}
            type="button"
          >
            <RotateCcw size={14} aria-hidden />
          </button>
          <button
            aria-label="Zoom in graph"
            className="inline-flex h-8 w-8 items-center justify-center rounded border border-[var(--color-border-subtle)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
            onClick={() => setScale((value) => Math.min(1.8, Number((value + 0.15).toFixed(2))))}
            type="button"
          >
            <ZoomIn size={15} aria-hidden />
          </button>
        </div>
      </div>

      <svg
        role="img"
        aria-label={ariaLabel}
        className="w-full cursor-grab rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
        height={height}
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        tabIndex={0}
        onPointerDown={(event) => {
          drag.current = { x: event.clientX, y: event.clientY };
          const target = event.currentTarget as SVGSVGElement & {
            setPointerCapture?: (pointerId: number) => void;
          };
          target.setPointerCapture?.(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!drag.current) return;
          const dx = event.clientX - drag.current.x;
          const dy = event.clientY - drag.current.y;
          drag.current = { x: event.clientX, y: event.clientY };
          setOffset((value) => ({ x: value.x + dx / scale, y: value.y + dy / scale }));
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
      >
        <g transform={`translate(${offset.x} ${offset.y}) scale(${scale})`}>
          {layout.edges.map((edge) => (
            <path
              key={`${edge.from}->${edge.to}`}
              d={edgePath(edge.points)}
              fill="none"
              stroke="var(--color-border-strong)"
              strokeWidth={1.5}
            />
          ))}
          {layout.nodes.map((node) => {
            const isSelected = selectedId === node.id;
            return (
              <g
                key={node.id}
                role="button"
                aria-label={`Inspect ${node.label}`}
                tabIndex={0}
                transform={`translate(${node.x} ${node.y})`}
                onClick={(event) => {
                  event.stopPropagation();
                  selectNode(node);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    selectNode(node);
                  }
                }}
                className="cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                <rect
                  width={node.width}
                  height={node.height}
                  rx={6}
                  fill={isSelected ? "var(--color-selected-bg)" : "var(--color-surface-raised)"}
                  stroke={isSelected ? "var(--color-selected-border)" : "var(--color-border-subtle)"}
                  strokeWidth={isSelected ? 2 : 1}
                />
                <text
                  x={12}
                  y={18}
                  fill="var(--color-text-primary)"
                  fontFamily="var(--font-mono)"
                  fontSize={11}
                  fontWeight={650}
                >
                  {clippedLabel(node.label)}
                </text>
                <text
                  x={12}
                  y={34}
                  fill="var(--color-text-muted)"
                  fontFamily="var(--font-mono)"
                  fontSize={9}
                >
                  L{node.layer} / R{node.row}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      <div className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
        {selected ? (
          <div className="grid gap-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs font-semibold text-[var(--color-text-primary)]">
                {selected.label}
              </span>
              <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
                {selected.id}
              </span>
            </div>
            <pre className="m-0 max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-[var(--color-text-secondary)]">
              {JSON.stringify(selected.detail ?? { id: selected.id }, null, 2)}
            </pre>
          </div>
        ) : (
          <p className="m-0 text-xs text-[var(--color-text-muted)]">Select a node to inspect it.</p>
        )}
      </div>
    </div>
  );
}
