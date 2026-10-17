const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

// Run the actual TS client/hooks with controlled Vite configuration and transport.
module.exports = function loadModules(env = {}, fetch = globalThis.fetch) {
  const cache = new Map();
  function load(file) {
    const full = path.resolve(__dirname, '../src', file);
    if (cache.has(full)) return cache.get(full);
    const source = fs.readFileSync(full, 'utf8').replaceAll('import.meta.env', JSON.stringify(env));
    const { outputText } = ts.transpileModule(source, { compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2021, jsx: ts.JsxEmit.ReactJSX,
    } });
    const exports = {};
    cache.set(full, exports);
    vm.runInNewContext(outputText, {
      exports, require(name) {
        if (!name.startsWith('.')) return require(name);
        const relative = path.relative(path.resolve(__dirname, '../src'), path.resolve(path.dirname(full), name));
        const extension = fs.existsSync(path.resolve(path.dirname(full), name + '.ts')) ? '.ts' : '.tsx';
        return load(relative + extension);
      }, fetch, AbortController, setTimeout, clearTimeout, Error, console,
    }, { filename: full });
    return exports;
  }
  return load;
};
