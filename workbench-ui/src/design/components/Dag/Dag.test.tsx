import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DagViewer } from "./Dag";
import { layoutDag } from "./layout";
import golden from "./Dag.layout.golden.json";

const nodes = [
  { id: "b", label: "Beta", detail: { kind: "source" } },
  { id: "a", label: "Alpha", detail: { kind: "source" } },
  { id: "c", label: "Converges", detail: { kind: "derived" } },
  { id: "d", label: "Decision", detail: { kind: "sink" } },
];

const edges = [
  { from: "b", to: "c" },
  { from: "a", to: "c" },
  { from: "c", to: "d" },
];

function compactLayout() {
  const layout = layoutDag(nodes, edges);
  return {
    nodes: layout.nodes.map(({ id, layer, row, x, y }) => ({ id, layer, row, x, y })),
    edges: layout.edges.map(({ from, to, points }) => ({ from, to, points })),
    width: layout.width,
    height: layout.height,
  };
}

describe("Dag", () => {
  it("matches the golden deterministic longest-path layout", () => {
    expect(compactLayout()).toEqual(golden);
  });

  it("rejects cyclic input instead of guessing a layout", () => {
    expect(() =>
      layoutDag(
        [
          { id: "a" },
          { id: "b" },
        ],
        [
          { from: "a", to: "b" },
          { from: "b", to: "a" },
        ],
      ),
    ).toThrow(/acyclic/);
  });

  it("clicking a node selects it and notifies the inspector callback", async () => {
    const user = userEvent.setup();
    const inspect = vi.fn();
    render(<DagViewer nodes={nodes} edges={edges} ariaLabel="Proposal chain DAG" onInspectNode={inspect} />);

    await user.click(screen.getByRole("button", { name: "Inspect Decision" }));

    expect(inspect).toHaveBeenCalledWith(expect.objectContaining({ id: "d", label: "Decision" }));
    expect(screen.getByText(/"sink"/)).toBeInTheDocument();
  });

  it("exposes bounded zoom controls", async () => {
    const user = userEvent.setup();
    render(<DagViewer nodes={nodes} edges={edges} ariaLabel="Proposal chain DAG" />);

    await user.click(screen.getByRole("button", { name: "Zoom in graph" }));
    await user.click(screen.getByRole("button", { name: "Zoom out graph" }));
    await user.click(screen.getByRole("button", { name: "Reset graph view" }));

    expect(screen.getByTestId("dag-viewer")).toBeInTheDocument();
  });

  it("renders a tall, few-layer graph at natural height inside a bounded scroll box", () => {
    // 12 sources -> 12 sinks: 2 layers, 24 rows — a tall sliver that the old
    // fixed-320 viewport squished. The SVG should grow to the layout's natural
    // height (legible, scale ~1), and the wrapper bounds + scrolls it.
    const wideNodes = Array.from({ length: 24 }, (_, i) => ({ id: `n${i}` }));
    const fanEdges = Array.from({ length: 12 }, (_, i) => ({
      from: `n${i}`,
      to: `n${i + 12}`,
    }));
    const layout = layoutDag(wideNodes, fanEdges);
    expect(layout.height).toBeGreaterThan(320); // precondition: genuinely tall

    render(<DagViewer nodes={wideNodes} edges={fanEdges} ariaLabel="Tall fan DAG" />);

    const svg = screen.getByRole("img", { name: "Tall fan DAG" });
    expect(svg).toHaveAttribute("height", String(layout.height));
    const viewport = screen.getByTestId("dag-viewport");
    expect(viewport.style.maxHeight).toBe("560px");
    expect(viewport.className).toContain("overflow-auto");
  });
});
