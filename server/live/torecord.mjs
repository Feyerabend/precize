// Turn a run downloaded from the live page (live-run.json) into an audit folder, written as
// the server writes it, so that `python -m audit.render` can make a PDF of it.
//   node live/torecord.mjs RUN.json DOCS_DIR OUT_DIR
// DOCS_DIR holds the documents the run read, under the names the page gave them; the fetch
// ledger is rebuilt from them (the run file keeps what was read and when, not the text).
import { createRequire } from "module";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
const require = createRequire(import.meta.url);
const A = require("../playground/audit.js");

const [runFile, docs, out] = process.argv.slice(2);
if (!out) { console.error("usage: node live/torecord.mjs RUN.json DOCS_DIR OUT_DIR"); process.exit(2); }
const r = JSON.parse(readFileSync(runFile, "utf8"));
if (!r.logs || !r.keys) { console.error(`${runFile} is not a run from the live page`); process.exit(1); }

mkdirSync(out + "/.fetched", { recursive: true });
const missing = new Set();
for (const [log, es] of Object.entries(r.logs)) {
  if (!/^[A-Za-z0-9][A-Za-z0-9 ._()\-]{0,63}$/.test(log)) throw new Error(`bad log name ${log}`);
  writeFileSync(`${out}/${log}.jsonl`, es.map(d => A.pyline(A.entry(d))).join("\n") + "\n");
  const led = (r.fetched || []).filter(f => f.log === log).flatMap(({ source, at }) => {
    const m = source.match(/^(.*), lines (\d+)-(\d+)$/);
    if (!m) return [];
    const [path, a, b] = [m[1], +m[2], +m[3]];
    const file = `${docs}/${path}`;
    if (!existsSync(file)) { missing.add(path); return []; }
    const lines = readFileSync(file, "utf8").replace(/\r\n?/g, "\n").split("\n");
    return [JSON.stringify({ source, path, a, b, at, text: lines.slice(a - 1, b).join("\n") })];
  });
  writeFileSync(`${out}/.fetched/${log}.jsonl`, led.length ? led.join("\n") + "\n" : "");
}
writeFileSync(`${out}/keys.json`, JSON.stringify(r.keys, null, 1) + "\n");

// The case box, from what the page put in the run, unless the folder already has one.
if (r.about && !existsSync(`${out}/about.json`)) {
  const flat = s => typeof s === "string" ? s.replace(/\*\*|`/g, "").replace(/\n+/g, " ").replace(/\s+/g, " ").trim() : s;
  const a = Object.fromEntries(Object.entries(r.about).map(([k, v]) => [k, flat(v)]));
  writeFileSync(`${out}/about.json`, JSON.stringify(a, null, 1) + "\n");
}
const n = Object.values(r.logs).reduce((s, es) => s + es.length, 0);
console.log(`${out}: ${Object.keys(r.logs).join(", ")}, ${n} entries, ${(r.fetched || []).length} reads`);
if (missing.size) console.log(`not in ${docs} (left out of the fetch ledger): ${[...missing].join(", ")}`);
