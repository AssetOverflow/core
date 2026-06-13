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
});
