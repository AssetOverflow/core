import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { useManagedTimeout } from "./useManagedTimeout";

function Flasher() {
  const [on, setOn] = useState(false);
  const schedule = useManagedTimeout();
  return (
    <button
      type="button"
      onClick={() => {
        setOn(true);
        schedule(() => setOn(false), 1000);
      }}
    >
      {on ? "on" : "off"}
    </button>
  );
}

describe("useManagedTimeout", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fires the scheduled callback after the delay", () => {
    render(<Flasher />);

    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toHaveTextContent("on");

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByRole("button")).toHaveTextContent("off");
  });

  it("re-scheduling replaces the pending timeout (single slot)", () => {
    render(<Flasher />);

    fireEvent.click(screen.getByRole("button"));
    act(() => {
      vi.advanceTimersByTime(600);
    });
    fireEvent.click(screen.getByRole("button"));
    // The first timeout (due at t=1000) was replaced; at t=1100 the flag is
    // still on because the second timeout fires at t=1600.
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(screen.getByRole("button")).toHaveTextContent("on");
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(screen.getByRole("button")).toHaveTextContent("off");
  });

  it("unmount clears the pending timeout (no post-unmount callback)", () => {
    const { unmount } = render(<Flasher />);

    fireEvent.click(screen.getByRole("button"));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
