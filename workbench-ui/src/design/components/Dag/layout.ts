export interface DagNodeInput {
  id: string;
  label?: string;
  detail?: unknown;
}

export interface DagEdgeInput {
  from: string;
  to: string;
  label?: string;
}

export interface DagLayoutOptions {
  nodeWidth?: number;
  nodeHeight?: number;
  columnGap?: number;
  rowGap?: number;
  padding?: number;
}

export interface DagLayoutNode extends Required<Pick<DagNodeInput, "id">> {
  label: string;
  detail?: unknown;
  layer: number;
  row: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DagLayoutEdge {
  from: string;
  to: string;
  label?: string;
  points: { x1: number; y1: number; x2: number; y2: number };
}

export interface DagLayout {
  nodes: DagLayoutNode[];
  edges: DagLayoutEdge[];
  width: number;
  height: number;
}

const DEFAULTS = {
  nodeWidth: 144,
  nodeHeight: 44,
  columnGap: 72,
  rowGap: 18,
  padding: 24,
} satisfies Required<DagLayoutOptions>;

function insertSorted(values: string[], value: string) {
  values.push(value);
  values.sort((a, b) => a.localeCompare(b));
}

export function layoutDag(
  nodes: readonly DagNodeInput[],
  edges: readonly DagEdgeInput[],
  options: DagLayoutOptions = {},
): DagLayout {
  const opts = { ...DEFAULTS, ...options };
  const byId = new Map<string, DagNodeInput>();
  for (const node of nodes) {
    if (!node.id.trim()) throw new Error("DAG node id must be non-empty");
    if (byId.has(node.id)) throw new Error(`duplicate DAG node id: ${node.id}`);
    byId.set(node.id, node);
  }

  const outgoing = new Map<string, string[]>();
  const indegree = new Map<string, number>();
  const layer = new Map<string, number>();
  for (const id of Array.from(byId.keys()).sort()) {
    outgoing.set(id, []);
    indegree.set(id, 0);
    layer.set(id, 0);
  }
  for (const edge of edges) {
    if (!byId.has(edge.from)) throw new Error(`DAG edge source not found: ${edge.from}`);
    if (!byId.has(edge.to)) throw new Error(`DAG edge target not found: ${edge.to}`);
    outgoing.get(edge.from)!.push(edge.to);
    indegree.set(edge.to, indegree.get(edge.to)! + 1);
  }
  for (const targets of outgoing.values()) targets.sort((a, b) => a.localeCompare(b));

  const ready = Array.from(indegree)
    .filter(([, degree]) => degree === 0)
    .map(([id]) => id)
    .sort((a, b) => a.localeCompare(b));
  const topo: string[] = [];

  while (ready.length > 0) {
    const id = ready.shift()!;
    topo.push(id);
    for (const target of outgoing.get(id)!) {
      layer.set(target, Math.max(layer.get(target)!, layer.get(id)! + 1));
      const nextDegree = indegree.get(target)! - 1;
      indegree.set(target, nextDegree);
      if (nextDegree === 0) insertSorted(ready, target);
    }
  }

  if (topo.length !== nodes.length) {
    throw new Error("DAG layout requires an acyclic graph");
  }

  const layers = new Map<number, string[]>();
  for (const id of topo) {
    const index = layer.get(id)!;
    if (!layers.has(index)) layers.set(index, []);
    layers.get(index)!.push(id);
  }
  for (const ids of layers.values()) ids.sort((a, b) => a.localeCompare(b));

  const layoutNodes: DagLayoutNode[] = [];
  for (const [layerIndex, ids] of Array.from(layers).sort((a, b) => a[0] - b[0])) {
    ids.forEach((id, row) => {
      const node = byId.get(id)!;
      layoutNodes.push({
        id,
        label: node.label || id,
        detail: node.detail,
        layer: layerIndex,
        row,
        x: opts.padding + layerIndex * (opts.nodeWidth + opts.columnGap),
        y: opts.padding + row * (opts.nodeHeight + opts.rowGap),
        width: opts.nodeWidth,
        height: opts.nodeHeight,
      });
    });
  }

  const placed = new Map(layoutNodes.map((node) => [node.id, node]));
  const layoutEdges = [...edges]
    .sort((a, b) => a.from.localeCompare(b.from) || a.to.localeCompare(b.to))
    .map((edge) => {
      const from = placed.get(edge.from)!;
      const to = placed.get(edge.to)!;
      return {
        from: edge.from,
        to: edge.to,
        label: edge.label,
        points: {
          x1: from.x + from.width,
          y1: from.y + from.height / 2,
          x2: to.x,
          y2: to.y + to.height / 2,
        },
      };
    });

  const maxLayer = Math.max(0, ...layoutNodes.map((node) => node.layer));
  const maxRows = Math.max(1, ...Array.from(layers.values()).map((ids) => ids.length));
  return {
    nodes: layoutNodes,
    edges: layoutEdges,
    width:
      opts.padding * 2 +
      (maxLayer + 1) * opts.nodeWidth +
      maxLayer * opts.columnGap,
    height:
      opts.padding * 2 +
      maxRows * opts.nodeHeight +
      (maxRows - 1) * opts.rowGap,
  };
}
