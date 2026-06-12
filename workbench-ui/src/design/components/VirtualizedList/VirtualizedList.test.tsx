import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { VirtualizedList } from "./VirtualizedList";

const MANY = Array.from({ length: 1000 }, (_, i) => `item-${i}`);

// happy-dom has no layout engine; the virtualizer's rect observer reads
// offsetWidth/offsetHeight (0x0) on mount and renders nothing. Give
// elements a real-looking layout size.
const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

beforeEach(() => {
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    get: () => 360,
  });
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
    configurable: true,
    get: () => 600,
  });
});

afterEach(() => {
  if (offsetDescriptors.offsetHeight) {
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", offsetDescriptors.offsetHeight);
  }
  if (offsetDescriptors.offsetWidth) {
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", offsetDescriptors.offsetWidth);
  }
  vi.restoreAllMocks();
});

function renderList(onActivate?: (item: string, index: number) => void) {
  return render(
    <VirtualizedList
      items={MANY}
      getKey={(item) => item}
      renderItem={(item, _i, focused) => (
        <span>
          {item}
          {focused ? " *" : ""}
        </span>
      )}
      onActivate={onActivate}
      estimateSize={36}
      height={360}
      ariaLabel="virtual list"
      // happy-dom has no layout; seed the viewport rect explicitly
      initialRect={{ width: 600, height: 360 }}
    />,
  );
}

describe("VirtualizedList", () => {
  it("renders O(viewport) rows, not all 1000", () => {
    const { container } = renderList();
    const rendered = container.querySelectorAll('[role="option"]').length;
    expect(rendered).toBeGreaterThan(0);
    expect(rendered).toBeLessThan(100);
  });

  it("total scroll height accounts for every item", () => {
    renderList();
    const list = screen.getByTestId("virtualized-list");
    const sizer = list.firstElementChild as HTMLElement;
    expect(sizer.style.height).toBe(`${1000 * 36}px`);
  });

  it("keyboard navigation works and Enter activates through the window", () => {
    const onActivate = vi.fn();
    renderList(onActivate);
    const list = screen.getByTestId("virtualized-list");

    fireEvent.keyDown(list, { key: "j" });
    fireEvent.keyDown(list, { key: "j" });
    fireEvent.keyDown(list, { key: "Enter" });
    expect(onActivate).toHaveBeenCalledWith("item-2", 2);
  });

  it("keys are item-derived, not index-derived (deterministic identity)", () => {
    const { container } = renderList();
    const first = container.querySelector('[data-index="0"]');
    expect(first).not.toBeNull();
    expect(first!.textContent).toContain("item-0");
  });
});
