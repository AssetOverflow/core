import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { StableJsonViewer } from "./StableJsonViewer";
import { diffLeaves, leaves, parseJsonSource } from "./jsonModel";

async function sha256Hex(source: string): Promise<string> {
  const bytes = new TextEncoder().encode(source);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

describe("StableJsonViewer invariants", () => {
  it("renders object keys in deterministic lexicographic order", () => {
    render(<StableJsonViewer source='{"z":1,"a":2}' />);
    const rows = within(screen.getByTestId("json-rows")).getAllByRole("button");
    expect(rows.map((row) => row.textContent)).toEqual(["/a 2", "/z 1"]);
  });

  it("preserves source string bytes without smart quotes or entity coercion", () => {
    const source = "{\"quote\":\"a \\\"raw\\\" & <tag>\"}";
    render(<StableJsonViewer source={source} />);
    expect(screen.getByText(/"a \\"raw\\" & <tag>"/)).toBeInTheDocument();
  });

  it("preserves numeric notation and int/float distinction", () => {
    render(<StableJsonViewer source='{"epsilon":1e-6,"int":1,"float":1.0}' />);
    expect(screen.getByText((_, node) => node?.textContent === "/epsilon 1e-6")).toBeInTheDocument();
    expect(screen.getByText((_, node) => node?.textContent === "/int 1")).toBeInTheDocument();
    expect(screen.getByText((_, node) => node?.textContent === "/float 1.0")).toBeInTheDocument();
  });

  it("copy-path returns a JSON Pointer", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    render(<StableJsonViewer source='{"scenes":[0,0,0,{"detail":{"object":"lens"}}]}' />);
    await user.click(screen.getByText(/\/scenes\/3\/detail\/object/));
    expect(writeText).toHaveBeenCalledWith("/scenes/3/detail/object");
  });

  it("diff mode is side-by-side and marks only changed leaves with glyphs", () => {
    render(<StableJsonViewer source='{"same":1,"changed":1}' compareSource='{"same":1,"changed":2,"added":3}' />);
    expect(screen.getByTestId("json-diff")).toBeInTheDocument();
    expect(screen.getAllByLabelText("changed")).toHaveLength(2);
    expect(screen.getAllByLabelText("added")).toHaveLength(2);
    expect(screen.getAllByLabelText("same")).toHaveLength(2);

    const modelDiff = diffLeaves(leaves(parseJsonSource('{"a":1}')), leaves(parseJsonSource('{"a":2}')));
    expect(modelDiff).toMatchObject([{ pointer: "/a", kind: "changed" }]);
  });

  it("virtualizes large documents and refuses inline render above 16 MiB", () => {
    const manyLeaves = `{"items":[${Array.from({ length: 1001 }, (_, i) => i).join(",")}]}`;
    const { rerender } = render(<StableJsonViewer source={manyLeaves} />);
    expect(screen.getByTestId("virtualized-json")).toHaveTextContent("virtualized 1000 of 1001 leaves");

    rerender(<StableJsonViewer source={`{"blob":"${"x".repeat(16 * 1024 * 1024)}"}`} />);
    expect(screen.getByText(/larger than 16 MiB/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open in external viewer/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Copy path/ })).toBeInTheDocument();
  });

  it("renders a sha256 digest badge over the source bytes and copies the full digest on click", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const source = '{"a":1}';
    const expectedDigest = await sha256Hex(source);

    render(<StableJsonViewer source={source} />);

    const digestButton = await screen.findByRole("button", { name: /sha256:/ });
    // The badge displays the truncated prefix.
    await waitFor(() => {
      expect(digestButton.textContent).toBe(`sha256:${expectedDigest.slice(0, 12)}`);
    });
    // Clicking the badge copies the FULL digest, not the truncated prefix.
    await user.click(digestButton);
    expect(writeText).toHaveBeenCalledWith(expectedDigest);
  });
});
