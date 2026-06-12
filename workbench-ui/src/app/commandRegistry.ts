import { useCallback, useSyncExternalStore } from "react";

export interface Command {
  id: string;
  label: string;
  section: string;
  shortcut?: string;
  action: () => void;
}

type Listener = () => void;

class CommandStore {
  private commands = new Map<string, Command>();
  private listeners = new Set<Listener>();
  private cached: readonly Command[] = [];

  register(cmds: readonly Command[]) {
    for (const cmd of cmds) {
      this.commands.set(cmd.id, cmd);
    }
    this.cached = Array.from(this.commands.values());
    this.notify();
  }

  unregister(ids: readonly string[]) {
    for (const id of ids) {
      this.commands.delete(id);
    }
    this.cached = Array.from(this.commands.values());
    this.notify();
  }

  getSnapshot(): readonly Command[] {
    return this.cached;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    for (const l of this.listeners) l();
  }
}

const store = new CommandStore();
const subscribe = (l: Listener) => store.subscribe(l);
const getSnapshot = () => store.getSnapshot();

export function useCommands(): readonly Command[] {
  return useSyncExternalStore(subscribe, getSnapshot);
}

export function useCommandRegistry() {
  const register = useCallback((cmds: readonly Command[]) => {
    store.register(cmds);
  }, []);

  const unregister = useCallback((ids: readonly string[]) => {
    store.unregister(ids);
  }, []);

  return { register, unregister };
}

const RECENT_KEY = "core-recent-evidence";
const MAX_RECENT = 10;

export interface RecentItem {
  label: string;
  path: string;
  timestamp: number;
}

export function getRecentItems(): RecentItem[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as RecentItem[];
  } catch {
    return [];
  }
}

export function pushRecentItem(item: Omit<RecentItem, "timestamp">) {
  const items = getRecentItems().filter((r) => r.path !== item.path);
  items.unshift({ ...item, timestamp: Date.now() });
  if (items.length > MAX_RECENT) items.length = MAX_RECENT;
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(items));
  } catch {
    // Recent-item persistence is best-effort. Restricted/private storage
    // contexts must not break command activation.
  }
}
