import assert from "node:assert/strict";
import { test } from "node:test";
import { EXAMPLES, cleanSequence, requestScore, scanMotifs } from "../src/lib/protein.ts";

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

test("requestScore turns the backend's neighbour lists into named fields", async () => {
  const body = {
    score: 0.91, label: "protective", nearest_homolog: "A0A0A0QTV5", top_features: [["glycine", 0.4]],
    features: {}, explanation: "", neighbours: [["A0A0A0QTV5", 0.93, "CAHS"], ["Q9XGK9", 0.88, ""], ["bad"]],
  };
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify(body), { status: 200 });
  try {
    const r = await requestScore("MAEEY");
    assert.deepEqual(r.neighbours, [
      { accession: "A0A0A0QTV5", cosine: 0.93, family: "CAHS" },
      { accession: "Q9XGK9", cosine: 0.88, family: "" },
    ]);
  } finally {
    globalThis.fetch = original;
  }
});
