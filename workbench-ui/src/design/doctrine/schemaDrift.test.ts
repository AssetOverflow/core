// @vitest-environment node
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Doctrine-as-test (Wave R brief R1): the UI cannot silently diverge from
 * the engine's API schemas. `scripts/dump-schemas.py` AST-walks
 * workbench/schemas.py into schema-snapshot.json (committed, same pattern
 * as enum-snapshot.json); this test asserts every dataclass field appears
 * in the matching TS interface in src/types/api.ts.
 *
 * Python class -> TS interface mapping strips a trailing "Schema"
 * (TurnJournalEntrySchema -> TurnJournalEntry).
 *
 * NOT_YET_MIRRORED is the explicit debt list: backend schemas shipped ahead
 * of their routes (R2-B, PR #712). Each R2 route brief shrinks it. A class
 * that gains a TS interface while still listed here FAILS — the list can
 * only shrink.
 */

const NOT_YET_MIRRORED = new Set([
  // R2-B backend read substrate (#712) — TS mirrors land with each R2 route:
  "PackSummary",
  "PackDetail",
  "VaultSummary",
  "VaultEntry",
  // Wave R3 sealed turn replay backend — TS mirrors land with the frontend
  // Replay Moment PR (which also retires the W-026 artifact-keyed
  // ReplayComparison/ReplayDivergence pair on both sides):
  "TurnReplayComparison",
  "TurnReplayDivergence",
]);

const UI_ROOT = join(__dirname, "..", "..", "..");
const snapshot: Record<string, string[]> = JSON.parse(
  readFileSync(join(UI_ROOT, "schema-snapshot.json"), "utf-8"),
);
const apiTs = readFileSync(join(UI_ROOT, "src", "types", "api.ts"), "utf-8");

function interfaceBlock(name: string): string | null {
  const start = apiTs.search(
    new RegExp(`export interface ${name}\\b[^{]*\\{`),
  );
  if (start === -1) return null;
  const open = apiTs.indexOf("{", start);
  let depth = 0;
  for (let i = open; i < apiTs.length; i++) {
    if (apiTs[i] === "{") depth++;
    else if (apiTs[i] === "}") {
      depth--;
      if (depth === 0) return apiTs.slice(open, i + 1);
    }
  }
  return null;
}

describe("doctrine: UI types cover engine schemas", () => {
  const classes = Object.keys(snapshot).sort();

  it("snapshot is non-trivial", () => {
    expect(classes.length).toBeGreaterThan(10);
  });

  for (const pyName of classes) {
    const tsName = pyName.replace(/Schema$/, "");
    const block = interfaceBlock(tsName);

    if (NOT_YET_MIRRORED.has(pyName)) {
      it(`${pyName}: still unmirrored (allowlisted debt)`, () => {
        expect(
          block,
          `${tsName} now exists in api.ts — remove ${pyName} from NOT_YET_MIRRORED`,
        ).toBeNull();
      });
      continue;
    }

    it(`${pyName} -> ${tsName}: every field is mirrored`, () => {
      expect(block, `no TS interface for ${tsName}`).not.toBeNull();
      const missing = snapshot[pyName].filter(
        (field) => !new RegExp(`\\b${field}\\??:`).test(block!),
      );
      expect(missing, `fields missing from ${tsName}: ${missing.join(", ")}`).toEqual([]);
    });
  }
});
