import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { PreviewPage } from "./PreviewPage";

describe("/preview", () => {
  it("renders every primitive with network unavailable", () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("network blocked"))));
    render(<PreviewPage />);
    expect(screen.getByRole("heading", { name: "CORE Workbench Design System v1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Primitives" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Badges" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "States" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Stable JSON Viewer" })).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("opens CommandPalette with mod+k and closes overlays with Escape", async () => {
    const user = userEvent.setup();
    render(<PreviewPage />);
    await user.keyboard("{Control>}k{/Control}");
    expect(screen.getByRole("dialog", { name: "Command Palette" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Command Palette" })).not.toBeInTheDocument();
  });

  it("keeps tab order in DOM order for preview actions", async () => {
    const user = userEvent.setup();
    render(<PreviewPage />);
    await user.tab();
    expect(screen.getByRole("button", { name: "Primary action" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Quiet action" })).toHaveFocus();
  });
});
