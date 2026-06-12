import { fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useGlobalKeyboard } from "./useGlobalKeyboard";

function Harness({
  onTogglePalette = () => {},
  onToggleInspector = () => {},
  onShowHelp = () => {},
  onCopyEvidenceLink = () => {},
}: Partial<Parameters<typeof useGlobalKeyboard>[0]>) {
  useGlobalKeyboard({
    onTogglePalette,
    onToggleInspector,
    onShowHelp,
    onCopyEvidenceLink,
  });
  return <input data-testid="field" />;
}

function renderHarness(handlers: Partial<Parameters<typeof useGlobalKeyboard>[0]>) {
  return render(
    <MemoryRouter>
      <Harness {...handlers} />
    </MemoryRouter>,
  );
}

describe("useGlobalKeyboard Cmd+Shift+C", () => {
  afterEach(() => {
    document.body.focus();
  });

  it("invokes onCopyEvidenceLink, not the palette", () => {
    const onCopyEvidenceLink = vi.fn();
    const onTogglePalette = vi.fn();
    renderHarness({ onCopyEvidenceLink, onTogglePalette });

    fireEvent.keyDown(window, { key: "C", metaKey: true, shiftKey: true });

    expect(onCopyEvidenceLink).toHaveBeenCalledTimes(1);
    expect(onTogglePalette).not.toHaveBeenCalled();
  });

  it("does not fire while an input is focused", () => {
    const onCopyEvidenceLink = vi.fn();
    const { getByTestId } = renderHarness({ onCopyEvidenceLink });

    getByTestId("field").focus();
    fireEvent.keyDown(window, { key: "C", metaKey: true, shiftKey: true });

    expect(onCopyEvidenceLink).not.toHaveBeenCalled();
  });

  it("does not fire on Cmd+C without Shift", () => {
    const onCopyEvidenceLink = vi.fn();
    renderHarness({ onCopyEvidenceLink });

    fireEvent.keyDown(window, { key: "c", metaKey: true });

    expect(onCopyEvidenceLink).not.toHaveBeenCalled();
  });

  it("Cmd+K still toggles the palette", () => {
    const onTogglePalette = vi.fn();
    renderHarness({ onTogglePalette });

    fireEvent.keyDown(window, { key: "k", metaKey: true });

    expect(onTogglePalette).toHaveBeenCalledTimes(1);
  });
});
