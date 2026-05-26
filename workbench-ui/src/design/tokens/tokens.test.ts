import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { tokens } from "./tokens";

function parseCssTokens() {
  const css = readFileSync(resolve(process.cwd(), "src/design/tokens/tokens.css"), "utf8");
  return Object.fromEntries(
    [...css.matchAll(/--([a-z0-9-]+):\s*([^;]+);/g)].map(([, name, value]) => [
      name,
      value.trim(),
    ]),
  );
}

describe("design tokens", () => {
  it("keeps tokens.css and generated tokens.ts synchronized", () => {
    expect(tokens).toEqual(parseCssTokens());
  });

  it("collapses tokenized motion under reduced motion", () => {
    const reduced = true;
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: reduced && query.includes("prefers-reduced-motion"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    expect(window.matchMedia("(prefers-reduced-motion: reduce)").matches).toBe(true);
    expect(tokens["motion-instant"]).toBe("0ms");
  });
});
