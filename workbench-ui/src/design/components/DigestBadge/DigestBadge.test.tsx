import { render, screen, fireEvent } from "@testing-library/react";
import { DigestBadge } from "./DigestBadge";

const HASH = "4f80f7e12c7e8ca1f1a277f8ccecf2846f08bb9d8f22354e6d3f30eb7fb34c80";

describe("DigestBadge", () => {
  it("renders truncated digest with algorithm prefix", () => {
    render(<DigestBadge digest={HASH} />);
    const badge = screen.getByTestId("digest-badge");
    expect(badge).toHaveTextContent("sha256:4f80f7e12c7e8ca1...");
  });

  it("uses custom algorithm prefix", () => {
    render(<DigestBadge digest={HASH} algorithm="blake3" />);
    expect(screen.getByTestId("digest-badge")).toHaveTextContent("blake3:");
  });

  it("uses custom truncation length", () => {
    render(<DigestBadge digest={HASH} truncate={8} />);
    expect(screen.getByTestId("digest-badge")).toHaveTextContent("sha256:4f80f7e1...");
  });

  it("copies full digest to clipboard on click", () => {
    render(<DigestBadge digest={HASH} />);
    fireEvent.click(screen.getByTestId("digest-badge"));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(`sha256:${HASH}`);
  });

  it("has aria-label with full digest", () => {
    render(<DigestBadge digest={HASH} />);
    const badge = screen.getByTestId("digest-badge");
    expect(badge.getAttribute("aria-label")).toContain(HASH);
  });

  it("shows green dot when verified is true", () => {
    render(<DigestBadge digest={HASH} verified={true} />);
    expect(screen.getByLabelText("Verified")).toBeInTheDocument();
  });

  it("shows red dot when verified is false", () => {
    render(<DigestBadge digest={HASH} verified={false} />);
    expect(screen.getByLabelText("Not verified")).toBeInTheDocument();
  });

  it("shows gray dot when verified is null", () => {
    render(<DigestBadge digest={HASH} verified={null} />);
    expect(screen.getByLabelText("Verification unknown")).toBeInTheDocument();
  });

  it("does not show dot when verified is undefined", () => {
    render(<DigestBadge digest={HASH} />);
    expect(screen.queryByLabelText("Verified")).toBeNull();
    expect(screen.queryByLabelText("Not verified")).toBeNull();
    expect(screen.queryByLabelText("Verification unknown")).toBeNull();
  });

  it("does not truncate short digests", () => {
    render(<DigestBadge digest="abc123" truncate={16} />);
    expect(screen.getByTestId("digest-badge")).toHaveTextContent("sha256:abc123");
    expect(screen.getByTestId("digest-badge")).not.toHaveTextContent("...");
  });
});
