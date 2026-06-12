import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Panel } from "./Panel";

describe("Panel", () => {
  it("renders title as a heading, toolbar slot, and body", () => {
    render(
      <Panel title="Evidence" toolbar={<button type="button">Filter</button>}>
        <p>body content</p>
      </Panel>,
    );
    expect(screen.getByRole("heading", { name: "Evidence" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Filter" })).toBeInTheDocument();
    expect(screen.getByText("body content")).toBeInTheDocument();
  });

  it("omits the toolbar container when no toolbar is given", () => {
    render(
      <Panel title="Plain">
        <p>x</p>
      </Panel>,
    );
    const header = screen.getByRole("heading", { name: "Plain" }).parentElement;
    expect(header?.querySelectorAll("div").length).toBe(0);
  });
});
