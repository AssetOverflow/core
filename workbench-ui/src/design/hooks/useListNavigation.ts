import { useCallback, useEffect, useRef, useState } from "react";
import {
  useRegisterShortcuts,
  type ShortcutEntry,
} from "../../app/shortcutRegistry";

/**
 * Shared list keyboard navigation (Wave R brief R0d).
 *
 * j/k + ArrowUp/ArrowDown move focus, Home/End jump, Enter activates.
 * Roving tabindex; focus is list-scoped (the handler lives on the list
 * container, not window), with an input guard so typing in an embedded
 * SearchInput never moves the list.
 *
 * Registers its shortcuts in the live shortcut registry while mounted —
 * the KeyboardHelp overlay shows "j / k" only when a navigable list exists.
 */

const LIST_NAV_SHORTCUTS: readonly ShortcutEntry[] = [
  { id: "list-nav-move", keys: "j / k", action: "Navigate lists", order: 40 },
  { id: "list-nav-open", keys: "Enter", action: "Open selected item", order: 41 },
];

function isTextInput(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || target.isContentEditable;
}

export interface UseListNavigationOptions {
  itemCount: number;
  onActivate?: (index: number) => void;
  /** Called whenever focus moves (selection-follows-focus is the caller's choice). */
  onFocusChange?: (index: number) => void;
  /**
   * "container" (default): keys bind to the list element via listProps.
   * "window": keys bind globally while mounted — for routes whose primary
   * surface IS the list (Gmail-style), with the same input guard.
   */
  scope?: "container" | "window";
  /** Escape handler (window scope only) — e.g. clear the selection. */
  onEscape?: () => void;
}

export interface UseListNavigationResult {
  focusedIndex: number;
  setFocusedIndex: (index: number) => void;
  /** Spread onto the list container. */
  listProps: {
    role: "listbox";
    tabIndex: 0;
    onKeyDown: (e: React.KeyboardEvent) => void;
  };
  /** Per-item props: roving tabindex + focus tracking. */
  itemProps: (index: number) => {
    role: "option";
    "aria-selected": boolean;
    tabIndex: 0 | -1;
    onFocus: () => void;
    ref: (el: HTMLElement | null) => void;
  };
}

export function useListNavigation({
  itemCount,
  onActivate,
  onFocusChange,
  scope = "container",
  onEscape,
}: UseListNavigationOptions): UseListNavigationResult {
  const [focusedIndex, setFocusedIndexState] = useState(0);
  const itemRefs = useRef(new Map<number, HTMLElement>());

  useRegisterShortcuts(LIST_NAV_SHORTCUTS);

  const moveFocus = useCallback(
    (index: number) => {
      const clamped = Math.max(0, Math.min(index, itemCount - 1));
      setFocusedIndexState(clamped);
      onFocusChange?.(clamped);
      if (scope === "container") {
        const el = itemRefs.current.get(clamped);
        el?.focus();
        el?.scrollIntoView({ block: "nearest" });
      }
    },
    [itemCount, onFocusChange, scope],
  );

  const handleKey = useCallback(
    (key: string, preventDefault: () => void): void => {
      if (itemCount === 0) return;
      switch (key) {
        case "j":
        case "ArrowDown":
          preventDefault();
          moveFocus(focusedIndex + 1);
          break;
        case "k":
        case "ArrowUp":
          preventDefault();
          moveFocus(focusedIndex - 1);
          break;
        case "Home":
          preventDefault();
          moveFocus(0);
          break;
        case "End":
          preventDefault();
          moveFocus(itemCount - 1);
          break;
        case "Enter":
          preventDefault();
          onActivate?.(focusedIndex);
          break;
      }
    },
    [focusedIndex, itemCount, moveFocus, onActivate],
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (isTextInput(e.target)) return;
      handleKey(e.key, () => e.preventDefault());
    },
    [handleKey],
  );

  useEffect(() => {
    if (scope !== "window") return;
    const onWindowKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTextInput(e.target)) return;
      if (e.key === "Escape") {
        if (onEscape) {
          e.preventDefault();
          onEscape();
        }
        return;
      }
      handleKey(e.key, () => e.preventDefault());
    };
    window.addEventListener("keydown", onWindowKeyDown);
    return () => window.removeEventListener("keydown", onWindowKeyDown);
  }, [scope, handleKey, onEscape]);

  const itemProps = useCallback(
    (index: number) => ({
      role: "option" as const,
      "aria-selected": index === focusedIndex,
      tabIndex: (index === focusedIndex ? 0 : -1) as 0 | -1,
      onFocus: () => setFocusedIndexState(index),
      ref: (el: HTMLElement | null) => {
        if (el) itemRefs.current.set(index, el);
        else itemRefs.current.delete(index);
      },
    }),
    [focusedIndex],
  );

  return {
    focusedIndex,
    setFocusedIndex: moveFocus,
    listProps: { role: "listbox", tabIndex: 0, onKeyDown },
    itemProps,
  };
}
