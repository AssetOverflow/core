import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Chat", to: "/chat" },
  { label: "Trace", to: "/trace" },
  { label: "Replay", to: "/replay" },
  { label: "Demos", to: "/demos" },
  { label: "Proposals", to: "/proposals" },
  { label: "Evals", to: "/evals" },
  { label: "Runs", to: "/runs" },
  { label: "Packs", to: "/packs" },
  { label: "Vault", to: "/vault" },
  { label: "Audit", to: "/audit" },
  { label: "Settings", to: "/settings" },
] as const;

export function LeftNav() {
  return (
    <nav
      data-region="leftnav"
      className="flex h-full flex-col gap-1 overflow-y-auto border-r border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2"
      aria-label="Main navigation"
    >
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            [
              "block rounded px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]",
              isActive
                ? "border-l-2 border-[var(--color-focus-ring)] pl-[10px] text-[var(--color-text-primary)] bg-[var(--color-surface-raised)]"
                : "border-l-2 border-transparent pl-[10px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-raised)]",
            ].join(" ")
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
