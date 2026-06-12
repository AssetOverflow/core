// @vitest-environment node
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Doctrine-as-test (ADR-0162 §1): token names are semantic; palette values
 * live ONLY in tokens.css (and its generated TS mirror). A hex or rgb()/
 * hsl() literal anywhere else is palette leakage and fails here.
 */

const SRC = join(__dirname, "..", "..");
const ALLOWED = new Set([
  "design/tokens/tokens.css",
  "design/tokens/tokens.ts", // generated mirror of tokens.css
  // The scanner's own pattern definitions and the drift gate's PR-number
  // comments ("#712" parses as 3-digit hex) are not palette usage:
  "design/doctrine/hexScan.test.ts",
  "design/doctrine/schemaDrift.test.ts",
]);

// Hex colors only: 3/4/6/8 hex digits after '#', not longer (so content
// hashes like "4f80f7e12c7e" without '#' never match).
const HEX_COLOR = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b/g;
const FUNC_COLOR = /\b(?:rgb|rgba|hsl|hsla)\(/g;

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      walk(full, out);
    } else if (/\.(tsx?|css)$/.test(entry)) {
      out.push(full);
    }
  }
  return out;
}

describe("doctrine: no palette literals outside tokens", () => {
  it("src/** carries no hex or rgb()/hsl() color literals", () => {
    const violations: string[] = [];
    for (const file of walk(SRC)) {
      const rel = relative(SRC, file).replaceAll("\\", "/");
      if (ALLOWED.has(rel)) continue;
      const text = readFileSync(file, "utf-8");
      for (const match of text.matchAll(HEX_COLOR)) {
        violations.push(`${rel}: ${match[0]}`);
      }
      for (const match of text.matchAll(FUNC_COLOR)) {
        violations.push(`${rel}: ${match[0]}…)`);
      }
    }
    expect(violations, violations.join("\n")).toEqual([]);
  });
});
