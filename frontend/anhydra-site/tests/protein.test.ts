import assert from "node:assert/strict";
import { test } from "node:test";
import { EXAMPLES, cleanSequence, scanMotifs } from "../src/lib/protein.ts";

test("cleanSequence drops FASTA headers and whitespace", () => {
  assert.equal(cleanSequence(">sp|X|Y\nmae ey\r\nKLK\n"), "MAEEYKLK");
});

test("scanMotifs finds the dehydrin K-segment in the dehydrin example", () => {
  const dehydrin = EXAMPLES.find((e) => e.id === "dehydrin")!;
  const kinds = scanMotifs(dehydrin.seq).map((m) => m.kind);
  assert.ok(kinds.includes("kseg"));
});

test("scanMotifs finds nothing in the folded control", () => {
  const folded = EXAMPLES.find((e) => e.id === "folded")!;
  assert.deepEqual(scanMotifs(folded.seq), []);
});
