import { useEffect, useRef, useCallback } from "react";
import { useRegisterShortcuts, type ShortcutEntry } from "../../../app/shortcutRegistry";
import { Search, X } from "lucide-react";

export interface SearchInputProps {
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  shortcut?: string;
}

const SEARCH_SHORTCUT: readonly ShortcutEntry[] = [
  { id: "search-focus", keys: "/", action: "Focus search input", order: 42 },
];

export function SearchInput({
  placeholder,
  value,
  onChange,
  shortcut = "/",
}: SearchInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  useRegisterShortcuts(SEARCH_SHORTCUT);

  const handleChange = useCallback(
    (raw: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => onChange(raw), 150);
    },
    [onChange],
  );

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== shortcut) return;
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) return;
      e.preventDefault();
      inputRef.current?.focus();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [shortcut]);

  return (
    <div
      className="relative flex items-center"
      data-testid="search-input"
    >
      <Search
        size={14}
        className="absolute left-2 text-[var(--color-text-muted)]"
        aria-hidden
      />
      <input
        ref={inputRef}
        type="search"
        aria-label={placeholder}
        placeholder={placeholder}
        defaultValue={value}
        onChange={(e) => handleChange(e.target.value)}
        className="w-full rounded-md border bg-transparent py-1.5 pl-7 pr-7 text-sm transition-colors placeholder:text-[var(--color-text-muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
        style={{
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-primary)",
          fontSize: "var(--text-sm)",
          transitionDuration: "var(--motion-duration-fast)",
          transitionTimingFunction: "var(--motion-ease-standard)",
        }}
      />
      {value && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => {
            onChange("");
            if (inputRef.current) inputRef.current.value = "";
            inputRef.current?.focus();
          }}
          className="absolute right-2 flex items-center text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
        >
          <X size={14} aria-hidden />
        </button>
      )}
      <kbd
        className="absolute right-2 rounded border px-1 text-[10px] text-[var(--color-text-muted)]"
        style={{
          borderColor: "var(--color-border-subtle)",
          display: value ? "none" : undefined,
        }}
        aria-hidden
      >
        {shortcut}
      </kbd>
    </div>
  );
}
