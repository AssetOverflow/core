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
      className="flex h-full flex-col gap-1 overflow-y-auto border-r border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2"
      aria-label="Main navigation"
    >
      {NAV_SECTIONS.map(({ section, routes }) => (
        <div key={section} role="group" aria-label={section} className="flex flex-col gap-1">
          <div className="px-3 pb-0.5 pt-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            {section}
          </div>
          {routes.map((route) => (
            <NavLink
              key={route.path}
              to={route.path}
              title={route.description}
              className={({ isActive }) =>
                [
                  "block rounded px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]",
                  isActive
                    ? "border-l-2 border-[var(--color-focus-ring)] pl-[10px] text-[var(--color-text-primary)] bg-[var(--color-surface-raised)]"
                    : "border-l-2 border-transparent pl-[10px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-raised)]",
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
