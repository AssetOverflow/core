import { render, screen, fireEvent } from "@testing-library/react";
import { MetadataTable } from "./MetadataTable";

describe("MetadataTable", () => {
  it("renders key-value pairs", () => {
    render(
      <MetadataTable
        rows={[
          { key: "trace_hash", value: "abc123" },
          { key: "cost_ms", value: "17" },
        ]}
      />,
    );
    expect(screen.getByText("trace_hash")).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
    expect(screen.getByText("cost_ms")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
  });

  it("renders rows in array order", () => {
    render(
      <MetadataTable
        rows={[
          { key: "z_last", value: "1" },
          { key: "a_first", value: "2" },
        ]}
      />,
    );
    const dts = screen.getAllByRole("term");
    expect(dts[0]).toHaveTextContent("z_last");
    expect(dts[1]).toHaveTextContent("a_first");
  });

  it("shows copy button on hover for copyable rows", () => {
    render(
      <MetadataTable
        rows={[{ key: "hash", value: "abc123def", copyable: true }]}
      />,
    );
    const copyBtn = screen.getByLabelText("Copy abc123def");
    expect(copyBtn).toBeInTheDocument();
  });

  it("copies value to clipboard when copy button clicked", () => {
    render(
      <MetadataTable
        rows={[{ key: "hash", value: "abc123def", copyable: true }]}
      />,
    );
    const copyBtn = screen.getByLabelText("Copy abc123def");
    fireEvent.click(copyBtn);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("abc123def");
  });

  it("does not show copy button for non-copyable rows", () => {
    render(
      <MetadataTable
        rows={[{ key: "status", value: "ok" }]}
      />,
    );
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders ReactNode values", () => {
    render(
      <MetadataTable
        rows={[{ key: "badge", value: <span data-testid="custom-badge">Custom</span> }]}
      />,
    );
    expect(screen.getByTestId("custom-badge")).toBeInTheDocument();
  });

  it("uses definition list semantics", () => {
    render(
      <MetadataTable rows={[{ key: "k", value: "v" }]} />,
    );
    expect(screen.getByTestId("metadata-table").tagName).toBe("DL");
  });
});
