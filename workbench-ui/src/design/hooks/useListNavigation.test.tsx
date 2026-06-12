import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useListNavigation } from "./useListNavigation";

function List({
  items,
  onActivate,
}: {
  items: string[];
  onActivate?: (index: number) => void;
}) {
  const { listProps, itemProps, focusedIndex } = useListNavigation({
    itemCount: items.length,
    onActivate,
  });
  return (
    <div aria-label="test list" {...listProps}>
      <input aria-label="embedded search" />
      {items.map((item, i) => (
        <div key={item} {...itemProps(i)}>
          {item}
          {i === focusedIndex ? " *" : ""}
        </div>
      ))}
    </div>
  );
}

const ITEMS = ["alpha", "beta", "gamma"];

function focusedOf(container: HTMLElement): string | null {
  const focused = container.querySelector('[aria-selected="true"]');
  return focused?.textContent?.replace(" *", "") ?? null;
}

describe("useListNavigation", () => {
  it("j/ArrowDown move down, k/ArrowUp move up, clamped at both ends", () => {
    const { container } = render(<List items={ITEMS} />);
    const list = screen.getByLabelText("test list");

    expect(focusedOf(container)).toBe("alpha");
    fireEvent.keyDown(list, { key: "k" });
    expect(focusedOf(container)).toBe("alpha");

    fireEvent.keyDown(list, { key: "j" });
    expect(focusedOf(container)).toBe("beta");
    fireEvent.keyDown(list, { key: "ArrowDown" });
    expect(focusedOf(container)).toBe("gamma");
    fireEvent.keyDown(list, { key: "j" });
    expect(focusedOf(container)).toBe("gamma");

    fireEvent.keyDown(list, { key: "ArrowUp" });
    expect(focusedOf(container)).toBe("beta");
  });

  it("Home/End jump to the ends", () => {
    const { container } = render(<List items={ITEMS} />);
    const list = screen.getByLabelText("test list");

    fireEvent.keyDown(list, { key: "End" });
    expect(focusedOf(container)).toBe("gamma");
    fireEvent.keyDown(list, { key: "Home" });
    expect(focusedOf(container)).toBe("alpha");
  });

  it("Enter activates the focused item", () => {
    const onActivate = vi.fn();
    render(<List items={ITEMS} onActivate={onActivate} />);
    const list = screen.getByLabelText("test list");

    fireEvent.keyDown(list, { key: "j" });
    fireEvent.keyDown(list, { key: "Enter" });
    expect(onActivate).toHaveBeenCalledWith(1);
  });

  it("typing in an embedded input never moves the list (input guard)", () => {
    const { container } = render(<List items={ITEMS} />);
    const input = screen.getByLabelText("embedded search");

    fireEvent.keyDown(input, { key: "j" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(focusedOf(container)).toBe("alpha");
  });

  it("window scope: keys work globally, Escape clears, input guard holds", () => {
    const onEscape = vi.fn();
    function WindowList() {
      const { focusedIndex } = (
        // eslint-disable-next-line react-hooks/rules-of-hooks
        useListNavigation({ itemCount: 3, scope: "window", onEscape })
      );
      return (
        <div>
          <input aria-label="search" />
          <span data-testid="focused">{focusedIndex}</span>
        </div>
      );
    }
    render(<WindowList />);

    fireEvent.keyDown(window, { key: "j" });
    expect(screen.getByTestId("focused").textContent).toBe("1");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onEscape).toHaveBeenCalled();

    screen.getByLabelText("search").focus();
    fireEvent.keyDown(screen.getByLabelText("search"), { key: "j" });
    expect(screen.getByTestId("focused").textContent).toBe("1");
  });

  it("roving tabindex: exactly the focused item is tabbable", () => {
    const { container } = render(<List items={ITEMS} />);
    const list = screen.getByLabelText("test list");
    fireEvent.keyDown(list, { key: "j" });

    const options = container.querySelectorAll('[role="option"]');
    expect(options[0].getAttribute("tabindex")).toBe("-1");
    expect(options[1].getAttribute("tabindex")).toBe("0");
    expect(options[2].getAttribute("tabindex")).toBe("-1");
  });
});
