export type JsonNode =
  | { kind: "object"; entries: { key: string; keyRaw: string; value: JsonNode }[] }
  | { kind: "array"; items: JsonNode[] }
  | { kind: "literal"; raw: string; valueKind: "string" | "number" | "boolean" | "null" };

export type Leaf = { pointer: string; raw: string; valueKind: string };

class Parser {
  private index = 0;

  constructor(private readonly source: string) {}

  parse(): JsonNode {
    this.ws();
    const node = this.value();
    this.ws();
    if (this.index !== this.source.length) throw new Error("Unexpected trailing JSON content.");
    return node;
  }

  private value(): JsonNode {
    this.ws();
    const ch = this.source[this.index];
    if (ch === "{") return this.object();
    if (ch === "[") return this.array();
    if (ch === '"') return { kind: "literal", raw: this.stringRaw(), valueKind: "string" };
    if (ch === "-" || /\d/.test(ch)) return { kind: "literal", raw: this.numberRaw(), valueKind: "number" };
    for (const word of ["true", "false", "null"] as const) {
      if (this.source.startsWith(word, this.index)) {
        this.index += word.length;
        return { kind: "literal", raw: word, valueKind: word === "null" ? "null" : "boolean" };
      }
    }
    throw new Error(`Unexpected JSON token at ${this.index}.`);
  }

  private object(): JsonNode {
    this.index++;
    this.ws();
    const entries: { key: string; keyRaw: string; value: JsonNode }[] = [];
    if (this.source[this.index] === "}") {
      this.index++;
      return { kind: "object", entries };
    }
    while (this.index < this.source.length) {
      const keyRaw = this.stringRaw();
      const key = JSON.parse(keyRaw) as string;
      this.ws();
      this.expect(":");
      const value = this.value();
      entries.push({ key, keyRaw, value });
      this.ws();
      if (this.source[this.index] === "}") {
        this.index++;
        break;
      }
      this.expect(",");
      this.ws();
    }
    entries.sort((a, b) => a.key.localeCompare(b.key));
    return { kind: "object", entries };
  }

  private array(): JsonNode {
    this.index++;
    this.ws();
    const items: JsonNode[] = [];
    if (this.source[this.index] === "]") {
      this.index++;
      return { kind: "array", items };
    }
    while (this.index < this.source.length) {
      items.push(this.value());
      this.ws();
      if (this.source[this.index] === "]") {
        this.index++;
        break;
      }
      this.expect(",");
      this.ws();
    }
    return { kind: "array", items };
  }

  private stringRaw(): string {
    const start = this.index;
    this.expect('"');
    while (this.index < this.source.length) {
      const ch = this.source[this.index++];
      if (ch === "\\") {
        this.index++;
      } else if (ch === '"') {
        return this.source.slice(start, this.index);
      }
    }
    throw new Error("Unterminated string.");
  }

  private numberRaw(): string {
    const start = this.index;
    if (this.source[this.index] === "-") this.index++;
    while (/\d/.test(this.source[this.index] ?? "")) this.index++;
    if (this.source[this.index] === ".") {
      this.index++;
      while (/\d/.test(this.source[this.index] ?? "")) this.index++;
    }
    if ((this.source[this.index] ?? "").toLowerCase() === "e") {
      this.index++;
      if (["+", "-"].includes(this.source[this.index] ?? "")) this.index++;
      while (/\d/.test(this.source[this.index] ?? "")) this.index++;
    }
    return this.source.slice(start, this.index);
  }

  private ws() {
    while (/\s/.test(this.source[this.index] ?? "")) this.index++;
  }

  private expect(ch: string) {
    if (this.source[this.index] !== ch) throw new Error(`Expected ${ch} at ${this.index}.`);
    this.index++;
  }
}

export function parseJsonSource(source: string): JsonNode {
  return new Parser(source).parse();
}

export function pointerPart(value: string) {
  return value.replaceAll("~", "~0").replaceAll("/", "~1");
}

export function leaves(node: JsonNode, pointer = ""): Leaf[] {
  if (node.kind === "literal") return [{ pointer, raw: node.raw, valueKind: node.valueKind }];
  if (node.kind === "array") return node.items.flatMap((item, index) => leaves(item, `${pointer}/${index}`));
  return node.entries.flatMap((entry) => leaves(entry.value, `${pointer}/${pointerPart(entry.key)}`));
}

export function countLeaves(node: JsonNode) {
  return leaves(node).length;
}

export type DiffKind = "added" | "removed" | "changed" | "same";

export function diffLeaves(left: Leaf[], right: Leaf[]) {
  const l = new Map(left.map((leaf) => [leaf.pointer, leaf]));
  const r = new Map(right.map((leaf) => [leaf.pointer, leaf]));
  const pointers = [...new Set([...l.keys(), ...r.keys()])].toSorted();
  return pointers.map((pointer) => {
    const before = l.get(pointer);
    const after = r.get(pointer);
    const kind: DiffKind = before && after ? (before.raw === after.raw ? "same" : "changed") : before ? "removed" : "added";
    return { pointer, before, after, kind };
  });
}
