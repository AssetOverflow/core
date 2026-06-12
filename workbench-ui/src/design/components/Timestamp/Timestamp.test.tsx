import { render, screen } from "@testing-library/react";
import { Timestamp } from "./Timestamp";

const ISO = "2026-06-12T10:30:00Z";

describe("Timestamp", () => {
  it("renders a <time> element with datetime attribute", () => {
    render(<Timestamp iso={ISO} />);
    const el = screen.getByTestId("timestamp");
    expect(el.tagName).toBe("TIME");
    expect(el).toHaveAttribute("datetime", ISO);
  });

  it("renders absolute format", () => {
    render(<Timestamp iso={ISO} format="absolute" />);
    const el = screen.getByTestId("timestamp");
    expect(el.textContent).toMatch(/Jun/);
    expect(el.textContent).toMatch(/2026/);
  });

  it("renders relative format", () => {
    const now = new Date();
    const fiveMinAgo = new Date(now.getTime() - 5 * 60_000).toISOString();
    render(<Timestamp iso={fiveMinAgo} format="relative" />);
    const el = screen.getByTestId("timestamp");
    expect(el.textContent).toMatch(/\d+m ago/);
  });

  it("renders both formats by default", () => {
    const now = new Date();
    const twoHoursAgo = new Date(now.getTime() - 2 * 3_600_000).toISOString();
    render(<Timestamp iso={twoHoursAgo} />);
    const el = screen.getByTestId("timestamp");
    expect(el.textContent).toMatch(/2h ago/);
    expect(el.textContent).toMatch(/\d{4}/);
  });

  it("shows 'just now' for very recent timestamps", () => {
    const now = new Date().toISOString();
    render(<Timestamp iso={now} format="relative" />);
    expect(screen.getByTestId("timestamp")).toHaveTextContent("just now");
  });

  it("shows 'yesterday' for timestamps about 1 day old", () => {
    const yesterday = new Date(Date.now() - 30 * 3_600_000).toISOString();
    render(<Timestamp iso={yesterday} format="relative" />);
    expect(screen.getByTestId("timestamp")).toHaveTextContent("yesterday");
  });

  it("has a title tooltip", () => {
    render(<Timestamp iso={ISO} format="relative" />);
    const el = screen.getByTestId("timestamp");
    expect(el.title).toMatch(/Jun/);
  });
});
