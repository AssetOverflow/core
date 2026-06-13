import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { TreeView } from "./TreeView";

const manifest = {
  zeta: "last-alpha",
  alpha: { nested_b: 2, nested_a: 1 },
  items: ["x", "y"],
};

describe("TreeView", () => {
  it("renders top-level keys in deterministic sorted order, collapsed", () => {
    render(<TreeView data={manifest} ariaLabel="Manifest" />);
    const items = screen.getAllByRole("treeitem");
    // alpha, items, zeta — sorted ascending, children hidden until expanded
    expect(items.map((el) => within(el).getAllByText(/.+/)[0].textContent)).toEqual([
      "alpha",
      "items",
      "zeta",
    ]);
    expect(screen.queryByText("nested_a")).not.toBeInTheDocument();
  });

  it("expands a branch with ArrowRight and reveals children sorted", async () => {
    const user = userEvent.setup();
    render(<TreeView data={manifest} ariaLabel="Manifest" />);

    const tree = screen.getByRole("tree", { name: "Manifest" });
    tree.focus();
    // focus starts on the first node (alpha); expand it
    await user.keyboard("{ArrowRight}");

    const visible = screen.getAllByRole("treeitem").map((el) => el.getAttribute("aria-level"));
    // alpha(1) now shows nested_a(2), nested_b(2) before items(1)
    expect(screen.getByText("nested_a")).toBeInTheDocument();
    expect(screen.getByText("nested_b")).toBeInTheDocument();
    const labels = screen.getAllByRole("treeitem").map((el) => within(el).getAllByText(/.+/)[0].textContent);
    expect(labels.slice(0, 3)).toEqual(["alpha", "nested_a", "nested_b"]);
    expect(visible).toContain("2");
  });

  it("collapses an expanded branch with ArrowLeft", async () => {
    const user = userEvent.setup();
    render(<TreeView data={manifest} ariaLabel="Manifest" />);
    const tree = screen.getByRole("tree", { name: "Manifest" });
    tree.focus();

    await user.keyboard("{ArrowRight}");
    expect(screen.getByText("nested_a")).toBeInTheDocument();
    await user.keyboard("{ArrowLeft}");
    expect(screen.queryByText("nested_a")).not.toBeInTheDocument();
  });

  it("moves focus down with ArrowDown / j and marks the focused node selected", async () => {
    const user = userEvent.setup();
    render(<TreeView data={manifest} ariaLabel="Manifest" />);
    const tree = screen.getByRole("tree", { name: "Manifest" });
    tree.focus();

    const items = () => screen.getAllByRole("treeitem");
    expect(items()[0]).toHaveAttribute("aria-selected", "true");
    await user.keyboard("j");
    expect(items()[1]).toHaveAttribute("aria-selected", "true");
    expect(items()[0]).toHaveAttribute("aria-selected", "false");
  });

  it("toggles a branch on click", async () => {
    const user = userEvent.setup();
    render(<TreeView data={manifest} ariaLabel="Manifest" />);

    await user.click(screen.getByText("alpha"));
    expect(screen.getByText("nested_a")).toBeInTheDocument();
    await user.click(screen.getByText("alpha"));
    expect(screen.queryByText("nested_a")).not.toBeInTheDocument();
  });

  it("renders an honest empty state for an empty manifest", () => {
    render(<TreeView data={{}} ariaLabel="Manifest" />);
    expect(screen.getByText("Empty manifest.")).toBeInTheDocument();
  });
});
