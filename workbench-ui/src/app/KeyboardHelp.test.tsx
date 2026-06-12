import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KeyboardHelp } from "./KeyboardHelp";
import { useRegisterShortcuts } from "./shortcutRegistry";
import { useListNavigation } from "../design/hooks/useListNavigation";

function HostWithBinding() {
  useRegisterShortcuts([
    { id: "test-binding", keys: "⌘T", action: "Test verb", order: 1 },
  ]);
  return <KeyboardHelp open onOpenChange={() => {}} />;
}

function HostWithList() {
  useListNavigation({ itemCount: 3 });
  return <KeyboardHelp open onOpenChange={() => {}} />;
}

describe("KeyboardHelp (registry-driven)", () => {
  it("renders rows from the shortcut registry, not a hand-maintained list", () => {
    render(<HostWithBinding />);
    expect(screen.getByText("Test verb")).toBeInTheDocument();
    expect(screen.getByText("⌘T")).toBeInTheDocument();
  });

  it("shows nothing for shortcuts no mounted component binds", () => {
    render(<KeyboardHelp open onOpenChange={() => {}} />);
    // No binder mounted in this render — the overlay cannot advertise j/k.
    expect(screen.queryByText("Navigate lists")).not.toBeInTheDocument();
  });

  it("list-navigation rows appear exactly while a navigable list is mounted", () => {
    const { unmount } = render(<HostWithList />);
    expect(screen.getByText("Navigate lists")).toBeInTheDocument();
    expect(screen.getByText("Open selected item")).toBeInTheDocument();
    unmount();

    render(<KeyboardHelp open onOpenChange={() => {}} />);
    expect(screen.queryByText("Navigate lists")).not.toBeInTheDocument();
  });
});
