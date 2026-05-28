import * as Dialog from "@radix-ui/react-dialog";
import { Search } from "lucide-react";
import { useRef, useState, useEffect, useCallback } from "react";
import { useNavigate, useInRouterContext } from "react-router-dom";
import { getExtraCommands, subscribeToCommands } from "../../../commands/registry";

interface Command {
  name: string;
  path: string;
}

const STATIC_COMMANDS: Command[] = [
  { name: "Open Chat", path: "/chat" },
  { name: "New chat session", path: "/chat?reset=1" },
  { name: "Open Proposals", path: "/proposals" },
  { name: "Open Evals", path: "/evals" },
];

function useAllCommands(): Command[] {
  const [extra, setExtra] = useState<Command[]>(getExtraCommands);
  useEffect(() => subscribeToCommands(() => setExtra(getExtraCommands())), []);
  return [...STATIC_COMMANDS, ...extra];
}

// Inner shell that safely calls useNavigate — only rendered inside a Router.
function RouterCommandPalette(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const activate = useCallback(
    (cmd: Command) => {
      navigate(cmd.path);
      props.onOpenChange(false);
    },
    [navigate, props],
  );
  return <CommandPaletteContent {...props} onActivate={activate} />;
}

// Fallback for design-system preview (no Router).
function FallbackCommandPalette(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const activate = useCallback(
    (_cmd: Command) => {
      props.onOpenChange(false);
    },
    [props],
  );
  return <CommandPaletteContent {...props} onActivate={activate} />;
}

function CommandPaletteContent({
  open,
  onOpenChange,
  onActivate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onActivate: (cmd: Command) => void;
}) {
  const [query, setQuery] = useState("");
  const [focusedIndex, setFocusedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const allCommands = useAllCommands();

  const filtered = allCommands.filter((cmd) =>
    cmd.name.toLowerCase().includes(query.toLowerCase()),
  );

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
      const cmd = filtered[focusedIndex];
      if (cmd) onActivate(cmd);
    }
  }

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
            <ul className="m-0 list-none p-0" role="listbox" aria-label="Commands">
              {filtered.map((cmd, i) => (
                <li key={cmd.path} role="option" aria-selected={i === focusedIndex}>
                  <button
                    className={[
                      "w-full rounded px-3 py-2 text-left text-sm transition-colors",
                      i === focusedIndex
                        ? "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)]"
                        : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-text-primary)]",
                    ].join(" ")}
                    type="button"
                    onClick={() => onActivate(cmd)}
                    onMouseEnter={() => setFocusedIndex(i)}
                    aria-label={cmd.name}
                  >
                    {cmd.name}
                  </button>
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
