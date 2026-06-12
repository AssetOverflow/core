import { useRef, type ReactNode } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useListNavigation } from "../../hooks/useListNavigation";

export interface VirtualizedListProps<T> {
  items: readonly T[];
  /** Deterministic, stable key per item — never the array index. */
  getKey: (item: T, index: number) => string;
  renderItem: (item: T, index: number, focused: boolean) => ReactNode;
  onActivate?: (item: T, index: number) => void;
  /** Estimated row height in px (virtualizer measurement seed). */
  estimateSize?: number;
  /** Viewport height; the scroll container is this component. */
  height: number | string;
  ariaLabel: string;
  /**
   * Seed rect for environments without layout (happy-dom tests, SSR).
   * Production layout measurement overrides it.
   */
  initialRect?: { width: number; height: number };
}

/**
 * Virtualized list (Wave R brief R0d): @tanstack/react-virtual for the
 * windowing, useListNavigation for the keyboard spine. Long evidence lists
 * (turn journals, audit timelines) render O(viewport), not O(n).
 */
export function VirtualizedList<T>({
  items,
  getKey,
  renderItem,
  onActivate,
  estimateSize = 36,
  height,
  ariaLabel,
  initialRect,
}: VirtualizedListProps<T>) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => estimateSize,
    getItemKey: (index) => getKey(items[index], index),
    overscan: 8,
    initialRect,
  });

  const { listProps, itemProps, focusedIndex } = useListNavigation({
    itemCount: items.length,
    onActivate: (index) => onActivate?.(items[index], index),
    onFocusChange: (index) => virtualizer.scrollToIndex(index),
  });

  return (
    <div
      ref={scrollRef}
      aria-label={ariaLabel}
      className="overflow-y-auto focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      style={{ height }}
      data-testid="virtualized-list"
      {...listProps}
    >
      <div
        style={{
          height: virtualizer.getTotalSize(),
          width: "100%",
          position: "relative",
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const index = virtualItem.index;
          const { ref: itemRef, ...optionProps } = itemProps(index);
          return (
            <div
              key={virtualItem.key}
              {...optionProps}
              data-index={index}
              ref={itemRef}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {renderItem(items[index], index, index === focusedIndex)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
