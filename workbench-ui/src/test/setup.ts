import "@testing-library/jest-dom/vitest";

// Node-environment test files (doctrine/*) have no global navigator on
// Node 20 (Node >=21 added one — which is why this only fails in CI).
if (typeof globalThis.navigator === "undefined") {
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: {},
  });
}

Object.defineProperty(navigator, "clipboard", {
  configurable: true,
  value: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>();

  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      clear: vi.fn(() => store.clear()),
      getItem: vi.fn((key: string) => store.get(key) ?? null),
      key: vi.fn((index: number) => Array.from(store.keys())[index] ?? null),
      removeItem: vi.fn((key: string) => {
        store.delete(key);
      }),
      setItem: vi.fn((key: string, value: string) => {
        store.set(key, String(value));
      }),
      get length() {
        return store.size;
      },
    },
  });
}
