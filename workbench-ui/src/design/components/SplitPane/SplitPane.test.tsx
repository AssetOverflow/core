import { render, screen, fireEvent } from "@testing-library/react";
import { SplitPane } from "./SplitPane";

beforeEach(() => {
  localStorage.clear();
});

describe("SplitPane", () => {
  it("renders two children", () => {
    render(
      <SplitPane direction="horizontal">
        <div>Left</div>
        <div>Right</div>
      </SplitPane>,
    );
    expect(screen.getByText("Left")).toBeInTheDocument();
    expect(screen.getByText("Right")).toBeInTheDocument();
  });

  it("renders a separator with correct orientation for horizontal", () => {
    render(
      <SplitPane direction="horizontal">
        <div>A</div>
        <div>B</div>
      </SplitPane>,
    );
    const handle = screen.getByRole("separator");
    expect(handle).toHaveAttribute("aria-orientation", "vertical");
  });

  it("renders a separator with correct orientation for vertical", () => {
    render(
      <SplitPane direction="vertical">
        <div>A</div>
        <div>B</div>
      </SplitPane>,
    );
    const handle = screen.getByRole("separator");
    expect(handle).toHaveAttribute("aria-orientation", "horizontal");
  });

  it("adjusts split via keyboard (ArrowRight for horizontal)", () => {
    render(
      <SplitPane direction="horizontal" defaultSplit={50}>
        <div>A</div>
        <div>B</div>
      </SplitPane>,
    );
    const handle = screen.getByRole("separator");
    fireEvent.keyDown(handle, { key: "ArrowRight" });
    expect(handle).toHaveAttribute("aria-valuenow", "52");
  });

  it("adjusts split via keyboard (ArrowLeft for horizontal)", () => {
    render(
      <SplitPane direction="horizontal" defaultSplit={50}>
        <div>A</div>
        <div>B</div>
      </SplitPane>,
    );
    const handle = screen.getByRole("separator");
    fireEvent.keyDown(handle, { key: "ArrowLeft" });
    expect(handle).toHaveAttribute("aria-valuenow", "48");
  });

  it("persists split to localStorage when id is provided", () => {
    render(
      <SplitPane direction="horizontal" defaultSplit={40} id="test-split">
        <div>A</div>
        <div>B</div>
      </SplitPane>,
    );
    expect(localStorage.getItem("core-split-test-split")).toBe("40");
  });

  it("restores split from localStorage", () => {
    localStorage.setItem("core-split-restore-test", "65");
    render(
      <SplitPane direction="horizontal" id="restore-test">
        <div>A</div>
        <div>B</div>
      </SplitPane>,
    );
    const handle = screen.getByRole("separator");
    expect(handle).toHaveAttribute("aria-valuenow", "65");
  });

  it("is focusable via tabIndex", () => {
    render(
      <SplitPane direction="horizontal">
        <div>A</div>
        <div>B</div>
      </SplitPane>,
    );
    const handle = screen.getByRole("separator");
    expect(handle).toHaveAttribute("tabIndex", "0");
  });
});
