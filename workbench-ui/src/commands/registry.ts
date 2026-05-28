export interface DynamicCommand {
  name: string;
  path: string;
}

let extraCommands: DynamicCommand[] = [];
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((fn) => fn());
}

export function registerCommands(cmds: DynamicCommand[]): void {
  const paths = new Set(cmds.map((c) => c.path));
  extraCommands = [...extraCommands.filter((c) => !paths.has(c.path)), ...cmds];
  notify();
}

export function unregisterCommands(paths: string[]): void {
  const pathSet = new Set(paths);
  extraCommands = extraCommands.filter((c) => !pathSet.has(c.path));
  notify();
}

export function getExtraCommands(): DynamicCommand[] {
  return extraCommands;
}

export function subscribeToCommands(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
