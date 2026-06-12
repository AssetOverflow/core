import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { TabBar, type Tab } from "./TabBar";

const TABS: Tab[] = [
  { id: "surfaces", label: "Surfaces" },
  { id: "grounding", label: "Grounding" },
  { id: "verdicts", label: "Verdicts" },
];

function TestTabBar({ initialTab = "surfaces" }: { initialTab?: string }) {
  const [active, setActive] = useState(initialTab);
  return (
    <TabBar tabs={TABS} activeTab={active} onTabChange={setActive}>
      <div data-testid={`panel-${active}`}>Content for {active}</div>
    </TabBar>
  );
}

describe("TabBar", () => {
  it("renders all tabs", () => {
    render(<TestTabBar />);
    expect(screen.getByRole("tab", { name: "Surfaces" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Grounding" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Verdicts" })).toBeInTheDocument();
  });

  it("marks the active tab with aria-selected", () => {
    render(<TestTabBar />);
    expect(screen.getByRole("tab", { name: "Surfaces" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Grounding" })).toHaveAttribute("aria-selected", "false");
  });

  it("renders a tabpanel with correct aria-labelledby", () => {
    render(<TestTabBar />);
    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveAttribute("aria-labelledby", "tab-surfaces");
  });

  it("changes tab on click", () => {
    render(<TestTabBar />);
    fireEvent.click(screen.getByRole("tab", { name: "Grounding" }));
    expect(screen.getByRole("tab", { name: "Grounding" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("panel-grounding")).toBeInTheDocument();
  });

  it("navigates with ArrowRight", () => {
    render(<TestTabBar />);
    const first = screen.getByRole("tab", { name: "Surfaces" });
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Grounding" })).toHaveAttribute("aria-selected", "true");
  });

  it("wraps around with ArrowRight from last", () => {
    render(<TestTabBar initialTab="verdicts" />);
    const last = screen.getByRole("tab", { name: "Verdicts" });
    fireEvent.keyDown(last, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Surfaces" })).toHaveAttribute("aria-selected", "true");
  });

  it("navigates with ArrowLeft", () => {
    render(<TestTabBar initialTab="grounding" />);
    const tab = screen.getByRole("tab", { name: "Grounding" });
    fireEvent.keyDown(tab, { key: "ArrowLeft" });
    expect(screen.getByRole("tab", { name: "Surfaces" })).toHaveAttribute("aria-selected", "true");
  });

  it("wraps around with ArrowLeft from first", () => {
    render(<TestTabBar />);
    const first = screen.getByRole("tab", { name: "Surfaces" });
    fireEvent.keyDown(first, { key: "ArrowLeft" });
    expect(screen.getByRole("tab", { name: "Verdicts" })).toHaveAttribute("aria-selected", "true");
  });

  it("Home jumps to first tab", () => {
    render(<TestTabBar initialTab="verdicts" />);
    const tab = screen.getByRole("tab", { name: "Verdicts" });
    fireEvent.keyDown(tab, { key: "Home" });
    expect(screen.getByRole("tab", { name: "Surfaces" })).toHaveAttribute("aria-selected", "true");
  });

  it("End jumps to last tab", () => {
    render(<TestTabBar />);
    const first = screen.getByRole("tab", { name: "Surfaces" });
    fireEvent.keyDown(first, { key: "End" });
    expect(screen.getByRole("tab", { name: "Verdicts" })).toHaveAttribute("aria-selected", "true");
  });

  it("inactive tabs have tabIndex -1", () => {
    render(<TestTabBar />);
    expect(screen.getByRole("tab", { name: "Grounding" })).toHaveAttribute("tabIndex", "-1");
    expect(screen.getByRole("tab", { name: "Verdicts" })).toHaveAttribute("tabIndex", "-1");
  });

  it("has a tablist role container", () => {
    render(<TestTabBar />);
    expect(screen.getByRole("tablist")).toBeInTheDocument();
  });
});
