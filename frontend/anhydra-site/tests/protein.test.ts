import assert from "node:assert/strict";
import { test } from "node:test";
import { cleanSequence, loadExamples, requestScore, scanMotifs } from "../src/lib/protein.ts";

test("cleanSequence drops FASTA headers and whitespace", () => {
  assert.equal(cleanSequence(">sp|X|Y\nmae ey\r\nKLK\n"), "MAEEYKLK");
});

test("scanMotifs finds the dehydrin K-segment", () => {
  const kinds = scanMotifs("MAGHHQEKKGIMDKIKEKLPGQH").map((m) => m.kind);
  assert.ok(kinds.includes("kseg"));
});

test("scanMotifs finds nothing in ubiquitin, a folded protein", () => {
  const ubiquitin = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG";
  assert.deepEqual(scanMotifs(ubiquitin), []);
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

test("loadExamples keeps well-formed entries and survives a missing file", async () => {
  const original = globalThis.fetch;
  const good = { id: "lea", label: "LEA", accession: "C6TDD1", name: "LEA-2", seq: "MLETEQ" };
  try {
    globalThis.fetch = async () => new Response(JSON.stringify([good, { ...good, seq: "mletEQ1" }, { id: "x" }]));
    assert.deepEqual(await loadExamples(), [good]);
    globalThis.fetch = async () => new Response("Not found", { status: 404 });
    assert.deepEqual(await loadExamples(), []);
  } finally {
    globalThis.fetch = original;
  }
});
