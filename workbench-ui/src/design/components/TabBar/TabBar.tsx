import { useRef, useCallback, type ReactNode, type KeyboardEvent } from "react";

export interface Tab {
  id: string;
  label: string;
}

export interface TabBarProps {
  tabs: readonly Tab[];
  activeTab: string;
  onTabChange: (id: string) => void;
  children: ReactNode;
}

export function TabBar({ tabs, activeTab, onTabChange, children }: TabBarProps) {
  const tablistRef = useRef<HTMLDivElement>(null);

  const focusTab = useCallback(
    (index: number) => {
      const tablist = tablistRef.current;
      if (!tablist) return;
      const buttons = tablist.querySelectorAll<HTMLButtonElement>('[role="tab"]');
      buttons[index]?.focus();
      onTabChange(tabs[index].id);
    },
    [onTabChange, tabs],
  );

  const onKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const currentIndex = tabs.findIndex((t) => t.id === activeTab);
      if (currentIndex === -1) return;

      switch (e.key) {
        case "ArrowRight": {
          e.preventDefault();
          focusTab((currentIndex + 1) % tabs.length);
          break;
        }
        case "ArrowLeft": {
          e.preventDefault();
          focusTab((currentIndex - 1 + tabs.length) % tabs.length);
          break;
        }
        case "Home": {
          e.preventDefault();
          focusTab(0);
          break;
        }
        case "End": {
          e.preventDefault();
          focusTab(tabs.length - 1);
          break;
        }
      }
    },
    [tabs, activeTab, focusTab],
  );

  return (
    <div data-testid="tab-bar">
      <div
        ref={tablistRef}
        role="tablist"
        className="flex gap-0 border-b border-[var(--color-border-subtle)]"
        onKeyDown={onKeyDown}
      >
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              role="tab"
              type="button"
              id={`tab-${tab.id}`}
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onTabChange(tab.id)}
              className="relative px-3 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
              style={{
                color: isActive
                  ? "var(--color-text-primary)"
                  : "var(--color-text-muted)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                transitionDuration: "var(--motion-duration-fast)",
                transitionTimingFunction: "var(--motion-ease-standard)",
              }}
            >
              {tab.label}
              {isActive && (
                <span
                  className="absolute bottom-0 left-0 right-0 h-[2px]"
                  style={{ background: "var(--color-focus-ring)" }}
                  aria-hidden
                />
              )}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id={`tabpanel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        tabIndex={0}
        className="py-3"
      >
        {children}
      </div>
    </div>
  );
}
