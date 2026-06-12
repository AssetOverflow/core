import { useEffect } from "react";
import { useSyncExternalStore } from "react";

/**
 * Live registry of keyboard shortcuts.
 *
 * Binding sites register exactly the shortcuts they handle, on mount, and
 * unregister on unmount. KeyboardHelp renders FROM this registry, so the
 * overlay structurally cannot advertise a shortcut nothing handles — the
 * failure mode R0a removed by hand is now impossible by construction.
 */
export interface ShortcutEntry {
  /** Stable id; also the dedupe key (e.g. "list-nav" registered by any list). */
  id: string;
  /** Display chord, e.g. "⌘K", "j / k". */
  keys: string;
  /** What it does, e.g. "Navigate lists". */
  action: string;
  /** Display ordering (lower first); ties broken by keys. */
  order: number;
}

type Listener = () => void;

class ShortcutStore {
  // id -> refcount'd entry: two mounted lists both registering "list-nav"
  // must not duplicate the row, and unmounting one must not remove it.
  private entries = new Map<string, { entry: ShortcutEntry; count: number }>();
  private listeners = new Set<Listener>();
  private cached: readonly ShortcutEntry[] = [];

  register(entries: readonly ShortcutEntry[]) {
    for (const entry of entries) {
      const existing = this.entries.get(entry.id);
      if (existing) {
        existing.count += 1;
      } else {
        this.entries.set(entry.id, { entry, count: 1 });
      }
    }
    this.rebuild();
  }

  unregister(ids: readonly string[]) {
    for (const id of ids) {
      const existing = this.entries.get(id);
      if (!existing) continue;
      existing.count -= 1;
      if (existing.count <= 0) this.entries.delete(id);
    }
    this.rebuild();
  }

  getSnapshot(): readonly ShortcutEntry[] {
    return this.cached;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private rebuild() {
    this.cached = Array.from(this.entries.values())
      .map((e) => e.entry)
      .sort((a, b) => a.order - b.order || a.keys.localeCompare(b.keys));
    for (const l of this.listeners) l();
  }
}

const store = new ShortcutStore();
const subscribe = (l: Listener) => store.subscribe(l);
const getSnapshot = () => store.getSnapshot();

export function useShortcuts(): readonly ShortcutEntry[] {
  return useSyncExternalStore(subscribe, getSnapshot);
}

/** Register shortcuts for the lifetime of the calling component. */
export function useRegisterShortcuts(entries: readonly ShortcutEntry[]) {
  // Entries are expected to be module-level constants; the JSON key keeps
  // the effect honest if a caller builds them inline.
  const key = JSON.stringify(entries);
  useEffect(() => {
    store.register(entries);
    return () => store.unregister(entries.map((e) => e.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}
