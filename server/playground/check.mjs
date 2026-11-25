// Compare the JS report (audit.js) with the Python one (audit/reports.py) on every
// audit in data/, and check that every signature verifies in JS.
//   node playground/check.mjs
import { createRequire } from "module";
import { execFileSync } from "child_process";
import { readFileSync, writeFileSync, mkdtempSync } from "fs";
import { tmpdir } from "os";
const require = createRequire(import.meta.url);
const A = require("./audit.js");
const here = new URL(".", import.meta.url).pathname;
globalThis.window = {};
new Function(readFileSync(here + "trials.js", "utf8"))();
const py = JSON.parse(execFileSync(here + "../.venv/bin/python", [here + "dump_reports.py", here + "../data"],
  { maxBuffer: 1 << 28 }).toString());
const canonical = v => JSON.stringify(v, (k, x) => x && typeof x === "object" && !Array.isArray(x)
  ? Object.fromEntries(Object.entries(x).sort()) : x);
let bad = 0;
for (const t of window.TRIALS) {
  const rec = A.Record.load(t.logs, t.keys);
  const sigs = await A.verify(rec);
  const js = A.plain(A.report(rec)), p = py[t.name];
  const diff = Object.keys(p).filter(k => canonical(js[k]) !== canonical(p[k]));
  if (sigs.length || diff.length) bad++;
  console.log(`${t.name}: ${rec.entries().length} entries, ` +
    (sigs.length ? `${sigs.length} bad signatures, ` : "signatures ok, ") +
    (diff.length ? `differs in ${diff.join(", ")}` : "report same"));
  for (const k of diff) console.log("   js:", canonical(js[k]).slice(0, 300), "\n   py:", canonical(p[k]).slice(0, 300));
}

// A person writes in JS; the Python record loads the log, checks hashes and signatures,
// and gives the same report.
{
  const t = window.TRIALS.find(t => t.name === "yates-tangible-object");
  const agents = Object.fromEntries(Object.entries(t.logs).filter(([n]) => n.startsWith("g")));
  const keys = Object.fromEntries(Object.entries(t.keys).filter(([n]) => n in agents));
  const rec = A.Record.load(agents, { ...keys });
  const me = "V (visitor)", key = await A.newKey();
  A.register(rec, me, "person", key.pub);
  const w = d => A.append(rec, me, d, key);
  await w({ id: "h1", act: "holder", body: "The dissent holds P1.", object: "g1 (for A):p1",
            value: "Kagan, J., dissenting", rests: ["g1 (for A):p1", "g1 (for A):l3"] });
  await w({ id: "n1", act: "holder", body: "I can't say which I meant.", object: me, value: "nescio",
            rests: ["g1 (for A):p1", "g1 (for A):p2"] });
  await w({ id: "d1", act: "decide", body: "I take P2.", object: me, value: "g1 (for A):p2",
            rests: ["g1 (for A):p2"], answers: [{ ref: "n1" }] });
  await w({ id: "vd1", act: "verdict", body: "2, real disagreement: övrigt “ok”.", object: "g1 (for A):q1",
            value: "4", rests: ["g1 (for A):vd1"], between: ["g1 (for A):p1", "g1 (for A):p2"] });
  let refused = "";
  try { await w({ id: "gr1", act: "grant", body: "x", rests: ["g1 (for A):q1"] }); } catch (x) { refused = x.rule; }
  const dir = mkdtempSync(tmpdir() + "/playground-");
  for (const [n, es] of rec.logs) writeFileSync(`${dir}/${n}.jsonl`, es.map(A.pyline).join("\n") + "\n");
  writeFileSync(`${dir}/keys.json`, JSON.stringify(rec.keys));
  const one = JSON.parse(execFileSync(here + "../.venv/bin/python", [here + "dump_reports.py", dir, "--one"]).toString());
  const js = A.plain(A.report(rec));
  const diff = Object.keys(one).filter(k => canonical(js[k]) !== canonical(one[k]));
  if (diff.length || refused !== "grant") bad++;
  console.log(`written in JS, read in Python: ${rec.logs.get(me).length} entries, ` +
    (diff.length ? `differs in ${diff.join(", ")}` : "loaded, signatures ok, report same") +
    `; grant without a recover refused: ${refused === "grant"}`);
}
process.exit(bad ? 1 : 0);
