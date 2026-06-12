import * as Dialog from "@radix-ui/react-dialog";
import { Search } from "lucide-react";
import { useRef, useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate, useInRouterContext } from "react-router-dom";
import {
  useCommands,
  getRecentItems,
  pushRecentItem,
  type Command,
  type RecentItem,
} from "../../../app/commandRegistry";

const NAV_COMMANDS: Command[] = [
  { id: "nav-chat", label: "Open Chat", section: "Navigate", shortcut: "⌘1", action: () => {} },
  { id: "nav-trace", label: "Open Trace", section: "Navigate", shortcut: "⌘2", action: () => {} },
  { id: "nav-replay", label: "Open Replay", section: "Navigate", shortcut: "⌘3", action: () => {} },
  { id: "nav-proposals", label: "Open Proposals", section: "Navigate", shortcut: "⌘4", action: () => {} },
  { id: "nav-evals", label: "Open Evals", section: "Navigate", shortcut: "⌘5", action: () => {} },
  { id: "nav-runs", label: "Open Runs", section: "Navigate", shortcut: "⌘6", action: () => {} },
  { id: "nav-packs", label: "Open Packs", section: "Navigate", shortcut: "⌘7", action: () => {} },
  { id: "nav-vault", label: "Open Vault", section: "Navigate", shortcut: "⌘8", action: () => {} },
  { id: "nav-audit", label: "Open Audit", section: "Navigate", shortcut: "⌘9", action: () => {} },
  { id: "nav-settings", label: "Open Settings", section: "Navigate", shortcut: "⌘0", action: () => {} },
];

const NAV_PATHS: Record<string, string> = {
  "nav-chat": "/chat",
  "nav-trace": "/trace",
  "nav-replay": "/replay",
  "nav-proposals": "/proposals",
  "nav-evals": "/evals",
  "nav-runs": "/runs",
  "nav-packs": "/packs",
  "nav-vault": "/vault",
  "nav-audit": "/audit",
  "nav-settings": "/settings",
};

interface DisplayItem {
  id: string;
  label: string;
  section: string;
  shortcut?: string;
  type: "command" | "recent";
}

interface SectionItem {
  item: DisplayItem;
  globalIndex: number;
}

function RouterCommandPalette(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const registeredCommands = useCommands();

  const activate = useCallback(
    (item: DisplayItem) => {
      const navPath = NAV_PATHS[item.id];
      if (navPath) {
        navigate(navPath);
        pushRecentItem({ label: item.label, path: navPath });
      } else if (item.type === "recent") {
        const recent = getRecentItems().find((r) => r.label === item.label);
        if (recent) navigate(recent.path);
      } else {
        const cmd = registeredCommands.find((c) => c.id === item.id);
        cmd?.action();
      }
      props.onOpenChange(false);
    },
    [navigate, registeredCommands, props],
  );

  const allCommands = useMemo(() => {
    const navCmds: DisplayItem[] = NAV_COMMANDS.map((c) => ({
      ...c,
      type: "command" as const,
    }));
    const regCmds: DisplayItem[] = registeredCommands
      .filter((c) => !NAV_PATHS[c.id])
      .map((c) => ({ ...c, type: "command" as const }));
    return [...navCmds, ...regCmds];
  }, [registeredCommands]);

  return (
    <CommandPaletteContent
      {...props}
      commands={allCommands}
      onActivate={activate}
    />
  );
}

function FallbackCommandPalette(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const commands: DisplayItem[] = NAV_COMMANDS.map((c) => ({
    ...c,
    type: "command" as const,
  }));
  return (
    <CommandPaletteContent
      {...props}
      commands={commands}
      onActivate={() => props.onOpenChange(false)}
    />
  );
}

function CommandPaletteContent({
  open,
  onOpenChange,
  commands,
  onActivate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands: readonly DisplayItem[];
  onActivate: (item: DisplayItem) => void;
}) {
  const [query, setQuery] = useState("");
  const [focusedIndex, setFocusedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const recentItems: DisplayItem[] = useMemo(() => {
    if (query) return [];
    return getRecentItems().map((r) => ({
      id: `recent-${r.path}`,
      label: r.label,
      section: "Recent",
      type: "recent" as const,
    }));
  }, [query]);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    const matchedCmds = q
      ? commands.filter((cmd) => cmd.label.toLowerCase().includes(q))
      : commands;
    return [...recentItems, ...matchedCmds];
  }, [query, commands, recentItems]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setFocusedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    setFocusedIndex(0);
  }, [query]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = filtered[focusedIndex];
      if (item) onActivate(item);
    }
  }

  const sections = useMemo(() => {
    const map = new Map<string, SectionItem[]>();
    filtered.forEach((item, globalIndex) => {
      const existing = map.get(item.section);
      const sectionItem = { item, globalIndex };
      if (existing) {
        existing.push(sectionItem);
      } else {
        map.set(item.section, [sectionItem]);
      }
    });
    return map;
  }, [filtered]);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/55" data-testid="overlay" />
        <Dialog.Content
          className="fixed left-1/2 top-[18vh] w-[min(560px,calc(100vw-32px))] -translate-x-1/2 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-surface-overlay)] p-4 shadow-[var(--shadow-overlay)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
          onKeyDown={handleKeyDown}
        >
          <Dialog.Title className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <Search size={16} aria-hidden />
            Command Palette
          </Dialog.Title>
          <Dialog.Description className="sr-only">
            Search and activate commands. Use arrow keys to navigate, Enter to activate, Escape to close.
          </Dialog.Description>
          <input
            ref={inputRef}
            className="mb-3 w-full rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline focus:outline-2 focus:outline-[var(--color-focus-ring)]"
            placeholder="Type to search commands…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search commands"
          />
          {filtered.length === 0 ? (
            <p className="text-sm text-[var(--color-text-secondary)]">No commands match.</p>
          ) : (
            <ul className="m-0 max-h-72 list-none overflow-y-auto p-0" role="listbox" aria-label="Commands">
              {Array.from(sections.entries()).map(([section, items]) => (
                <li key={section} className="mb-1">
                  <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                    {section}
                  </div>
                  <ul className="m-0 list-none p-0">
                    {items.map(({ item, globalIndex }) => (
                      <li key={item.id} role="option" aria-selected={globalIndex === focusedIndex}>
                        <button
                          className={[
                            "flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition-colors",
                            globalIndex === focusedIndex
                              ? "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)]"
                              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-text-primary)]",
                          ].join(" ")}
                          type="button"
                          onClick={() => onActivate(item)}
                          onMouseEnter={() => setFocusedIndex(globalIndex)}
                          aria-label={item.label}
                        >
                          <span>{item.label}</span>
                          {item.shortcut && (
                            <kbd className="ml-2 rounded border border-[var(--color-border-subtle)] px-1 font-mono text-[10px] text-[var(--color-text-muted)]">
                              {item.shortcut}
                            </kbd>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const inRouter = useInRouterContext();

  if (inRouter) {
    return <RouterCommandPalette open={open} onOpenChange={onOpenChange} />;
  }
  return <FallbackCommandPalette open={open} onOpenChange={onOpenChange} />;
}
