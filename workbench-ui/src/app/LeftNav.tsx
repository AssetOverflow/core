import { NavLink } from "react-router-dom";
import { leftNavSections } from "./routes";

// Routes derive from the single registry (routes.ts), grouped by wayfinding
// section. Adding a route in one place only is no longer possible — LeftNav,
// the command palette, ⌘-digits, and the landing dropdown all read the same
// list.
const NAV_SECTIONS = leftNavSections();

export function LeftNav() {
  return (
    <nav
      data-region="leftnav"
      className="flex h-full flex-col gap-[var(--density-nav-gap)] overflow-y-auto border-r border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-[var(--density-nav-padding)]"
      aria-label="Main navigation"
    >
      {NAV_SECTIONS.map(({ section, routes }) => (
        <div
          key={section}
          role="group"
          aria-label={section}
          className="flex flex-col gap-[var(--density-nav-gap)]"
        >
          <div className="px-[var(--density-nav-item-padding-x)] pb-0.5 pt-[var(--density-nav-section-padding-top)] text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            {section}
          </div>
          {routes.map((route) => (
            <NavLink
              key={route.path}
              to={route.path}
              title={route.description}
              className={({ isActive }) =>
                [
                  "block rounded px-[var(--density-nav-item-padding-x)] py-[var(--density-nav-item-padding-y)] text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]",
                  isActive
                    ? "border-l-2 border-[var(--color-focus-ring)] pl-[calc(var(--density-nav-item-padding-x)-2px)] text-[var(--color-text-primary)] bg-[var(--color-surface-raised)]"
                    : "border-l-2 border-transparent pl-[calc(var(--density-nav-item-padding-x)-2px)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-raised)]",
                ].join(" ")
              }
            >
              {route.label}
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  );
}
