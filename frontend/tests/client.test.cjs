const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const ts = require('typescript');

function loadClient(fetch) {
  const compile = (relative, imports = {}) => {
    const source = fs.readFileSync(path.join(__dirname, '../src', relative), 'utf8')
      .replaceAll('import.meta.env', '({})');
    const { outputText } = ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2021 },
    });
    const exports = {};
    vm.runInNewContext(outputText, {
      exports, require: (name) => {
        if (!(name in imports)) throw new Error(`Unexpected import ${name}`);
        return imports[name];
      }, fetch, AbortController, setTimeout, clearTimeout,
    });
    return exports;
  };
  return compile('api/client.ts', {
    '../types': compile('types.ts'),
    './mock': { mockScore: () => { throw new Error('Release requests must not use fixtures'); } },
  });
}

test('accepted length matches the encoder budget, including FASTA', () => {
  const client = loadClient();
  assert.equal(client.validateSequence('>record\n' + 'A'.repeat(1022)), null);
  assert.match(client.validateSequence('A'.repeat(1023)), /limit is 1022/);
  assert.match(client.validateSequence('A'.repeat(19)), /at least 20/);
});

test('invalid symbols and multiple FASTA records are rejected', () => {
  const client = loadClient();
  assert.match(client.validateSequence('A'.repeat(40) + 'X'), /standard/);
  assert.match(client.validateSequence('>a\n' + 'A'.repeat(40) + '\n>b\nAAAA'), /one sequence/);
});

test('real scoring sends original FASTA and never invents a fallback', async () => {
  let request;
  const response = { score: .7, label: 'protective' };
  const client = loadClient(async (url, options) => {
    request = { url, options };
    return { ok: true, json: async () => response };
  });
  const sequence = '>id\n' + 'A'.repeat(40);
  const result = await client.scoreSequence({ sequence });
  assert.equal(request.url, '/score');
  assert.equal(JSON.parse(request.options.body).sequence, sequence);
  assert.equal(result.isMock, false);
  assert.equal(result.data, response);
});

test('unavailable models surface as errors rather than fixture scores', async () => {
  const client = loadClient(async () => ({
    ok: false, status: 503, json: async () => ({ detail: 'Model unavailable' }),
  }));
  await assert.rejects(client.scoreSequence({ sequence: 'A'.repeat(40) }),
    (error) => error.kind === 'model_untrained' && error.message === 'Model unavailable');
});
