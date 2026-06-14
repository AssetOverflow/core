import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { layoutDag } from "../../design/components/Dag/layout";
import type { LogosAlignmentRow } from "../../types/api";
import { AlignmentTab, alignmentToDag } from "./LogosAlignmentTab";
import golden from "./LogosAlignment.layout.golden.json";

// Fixture mirrors the golden generator exactly: he -> grc -> en resonance plus
// one undeclared en-collapse-* target (invalid).
const FIXTURE: LogosAlignmentRow[] = [
  {
    edge_id: "edge-he-grc-1",
    source_id: "he-001",
    target_id: "grc-001",
    relation: "cross_lang.logos.utterance",
    weight: 0.95,
    evidence_ids: ["John1:1", "Gen1:1"],
    target_pack_id: "grc_logos_micro_v1",
    target_resolved: true,
    invalid_target: false,
  },
  {
    edge_id: "edge-grc-en-1",
    source_id: "grc-001",
    target_id: "en-024",
    relation: "cross_lang.logos.utterance.en",
    weight: 0.95,
    evidence_ids: ["John1:1"],
    target_pack_id: "en_core_cognition_v1",
    target_resolved: true,
    invalid_target: false,
  },
  {
    edge_id: "edge-grc-collapse-1",
    source_id: "grc-023",
    target_id: "en-collapse-breath",
    relation: "cross_lang.no_english_collapse",
    weight: 0.0,
    evidence_ids: ["adr-0073c"],
    target_pack_id: null,
    target_resolved: false,
    invalid_target: true,
  },
];

function compactLayout(rows: readonly LogosAlignmentRow[]) {
  const { nodes, edges } = alignmentToDag(rows);
  const layout = layoutDag(nodes, edges);
  return {
    nodes: layout.nodes.map(({ id, layer, row, x, y }) => ({ id, layer, row, x, y })),
    edges: layout.edges.map(({ from, to, points }) => ({ from, to, points })),
    width: layout.width,
    height: layout.height,
  };
}

describe("alignmentToDag", () => {
  it("matches the committed golden deterministic layout", () => {
    expect(compactLayout(FIXTURE)).toEqual(golden);
  });

  it("is order-independent in node placement (sorted) and re-runs identically", () => {
    const reversed = [...FIXTURE].reverse();
    // Nodes are sorted, so node placement is invariant to edge order.
    expect(compactLayout(reversed).nodes).toEqual(compactLayout(FIXTURE).nodes);
    // And the projection itself is referentially deterministic.
    expect(alignmentToDag(FIXTURE)).toEqual(alignmentToDag(FIXTURE));
  });

  it("derives one node per distinct id and one edge per row", () => {
    const { nodes, edges } = alignmentToDag(FIXTURE);
    expect(nodes.map((n) => n.id)).toEqual([
      "en-024",
      "en-collapse-breath",
      "grc-001",
      "grc-023",
      "he-001",
    ]);
    expect(edges).toHaveLength(FIXTURE.length);
  });
});

describe("AlignmentTab", () => {
  it("renders the resonance graph, edge cards, and an honest invalid-target warning", () => {
    render(<AlignmentTab rows={FIXTURE} selectedEdgeId={null} onSelect={() => {}} />);

    expect(screen.getByLabelText("CORE-Logos cross-language alignment graph")).toBeInTheDocument();
    expect(screen.getByText("3 alignment edges")).toBeInTheDocument();
    // The undeclared collapse anchor surfaces as invalid — not smoothed over.
    expect(screen.getByText("1 invalid target")).toBeInTheDocument();
    expect(
      screen.getByText(/invalid target — en-collapse-breath resolves to no declared lexicon entry/),
    ).toBeInTheDocument();
    expect(screen.getAllByText("John1:1").length).toBeGreaterThan(0);
    expect(screen.getByText("Gen1:1")).toBeInTheDocument();
  });

  it("invokes onSelect with the row when an edge card is activated", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<AlignmentTab rows={FIXTURE} selectedEdgeId={null} onSelect={onSelect} />);

    await user.click(screen.getByText("cross_lang.logos.utterance"));
    expect(onSelect).toHaveBeenCalledWith(FIXTURE[0]);
  });

  it("renders an honest empty state when the pack declares no edges", () => {
    render(<AlignmentTab rows={[]} selectedEdgeId={null} onSelect={() => {}} />);
    expect(
      screen.getByText("This pack declares no cross-language alignment edges."),
    ).toBeInTheDocument();
  });
});
