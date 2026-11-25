// Run the live page's tools with a scripted agent, no model: what is refused must be
// refused for the server's reasons, and the log it writes must load in Python with the
// same report, unfetched and committed_after_reading included.
//   node live/check.mjs
import { createRequire } from "module";
import { execFileSync } from "child_process";
import { readFileSync, writeFileSync, mkdtempSync, mkdirSync } from "fs";
import { tmpdir } from "os";
const require = createRequire(import.meta.url);
const here = new URL(".", import.meta.url).pathname;
globalThis.window = {};
new Function(readFileSync(here + "prompt.js", "utf8"))();
const T = require("./tools.js"), L = require("./ledger.js");
const PY = process.env.PY || here + "../.venv/bin/python";   // or PY=/path/to/python
const canonical = v => JSON.stringify(v, (k, x) => x && typeof x === "object" && !Array.isArray(x)
  ? Object.fromEntries(Object.entries(x).sort()) : x);
let bad = 0;
const ok = (cond, what) => { if (!cond) bad++; console.log(`${cond ? "ok  " : "FAIL"} ${what}`); };

const rules = readFileSync(here + "examples/allotment-rules.txt", "utf8");
const minutes = readFileSync(here + "examples/committee-minutes.txt", "utf8");
const line = rules.split("\n").findIndex(l => l.startsWith("3.1 ")) + 1;
const sentence = "Members shall not keep animals or poultry on their plot unless the committee agrees.";
const run = await T.newRun({ docs: [{ path: "allotment-rules.txt", text: rules }, { path: "committee-minutes.txt", text: minutes }],
  line, sentence, card: window.CARD });
const log = run.log, call = (n, i) => T.call(run, n, i);
const W = d => call("write", Object.assign({ log, kind: "agent" }, d));

ok(T.toolDefs(window.SERVER).length === 4 && T.system(run, window.SERVER)[0].includes(window.SERVER.stop), "tools and system prompt carry the server's texts");
ok(T.brief(run).includes(`line ${line}: "${sentence}"`), "the brief names T₀ and its line");

const r1 = call("read", { log, path: "allotment-rules.txt", start: line, end: line });
const src = (await r1).source;
ok(src === `allotment-rules.txt, lines ${line}-${line}`, "read returns the source to cite");
ok((await call("read", { log: "g1", path: "allotment-rules.txt", start: line, end: line })).refused === "name" && run.ledger.length === 1, "a read under another log is refused and not recorded");
ok(T.brief(run).includes(`Your log name is \`${log}\``), "the brief gives the log name");
ok((await W({ id: "q0", act: "quote", body: `T₀: "Members shall keep animals"`, sources: [src] })).refused === "verbatim", "a quote not in the fetched text is refused (verbatim)");
ok(!(await W({ id: "q1", act: "quote", body: `T₀: "${sentence}"`, sources: [src] })).refused, "the quote is written");
ok((await W({ id: "x1", act: "quote", body: "x", kind: "person", sources: [src] })).refused === "person", "kind person is refused");
ok((await call("write", { log: "g2 (for V)", kind: "agent", id: "q1", act: "quote", body: "x", sources: [src] })).refused === "name", "another log is refused");
ok(!(await W({ id: "m1", act: "mark", body: `"or ... unless": does "unless" reach "poultry"?`, value: "or poultry ... unless", object: "q1", rests: ["q1"] })).refused, "the mark is written");
ok((await W({ id: "h1", act: "holder", body: "Plot 9 holds P2.", value: "Plot 9", object: "m1", rests: ["m1"] })).refused === "person", "a holder from an agent is refused (person)");
ok((await W({ id: "p0", act: "precize", body: "both", rests: ["m1"] })).refused === "narrows", "a precize without narrows is refused");
await call("read", { log, path: "committee-minutes.txt", start: 1, end: 10 });   // read before the commit
const c = await W({ id: "c1", act: "commit", about: "m1", body: "A committee minute that treats poultry as needing leave would show P1." });
ok(!!c.note && c.note.includes("committee-minutes.txt, lines 1-10"), "a commit after reading more stands with a note");
const early = "committee-minutes.txt, lines 1-10";
ok((await W({ id: "l0", act: "look", body: "Rabbits need no leave.", sources: [early], answers: [{ ref: "c1", meets: false }] })).refused === "commit-first", "a look citing what was read before the commit is refused (commit-first)");
const late = (await call("read", { log, path: "committee-minutes.txt", start: 10, end: 19 })).source;
ok(!(await W({ id: "l1", act: "look", body: `The chair: the committee "may agree to poultry as to any other animal".`, sources: [late], answers: [{ ref: "c1", meets: true }] })).refused, "a look on what was read after the commit is written");
ok(!(await W({ id: "l2", act: "look", body: "The 1998 complaint.", sources: ["Society archive, box 3"] })).refused, "an unfetched source is written");
ok(!(await W({ id: "p1", act: "precize", body: "unless reaches both: animals and poultry with leave", narrows: "m1", rests: ["m1"] })).refused &&
   !(await W({ id: "p2", act: "precize", body: "unless reaches animals only: poultry never", narrows: "m1", rests: ["m1"] })).refused, "two readings are written");
ok(!(await W({ id: "vd1", act: "verdict", body: "1a between P1 and P2", value: "1a", object: "q1", between: ["p1", "p2"], rests: ["p1", "p2", "l1"] })).refused, "a verdict is proposed");
ok((await W({ id: "z", act: "show", body: "x", rests: ["nope"] })).refused === "cite", "a cite of nothing is refused");
ok(!(await W({ id: "cl", act: "close", body: "Stopped at holder and the audit's verdict." })).refused && run.closed, "the log is closed");
ok((await W({ id: "after", act: "show", body: "x" })).refused === "close", "nothing is written after close");
const e = await call("entry", { ref: `${log}:m1` }); if (!(e.rested_on_by || []).length) console.log("   entry:", JSON.stringify(e).slice(0, 300));
ok(e.rested_on_by.join() === `${log}:p1,${log}:p2`, "entry lists what rests on it (p1, p2; the refused ones are not there)");

// Python reads the log and the ledger, and gives the same report.
const dir = mkdtempSync(tmpdir() + "/live-");
writeFileSync(`${dir}/${log}.jsonl`, run.logs[log].map(d => require("../playground/audit.js").pyline(require("../playground/audit.js").entry(d))).join("\n") + "\n");
writeFileSync(`${dir}/keys.json`, JSON.stringify(run.keys));
mkdirSync(`${dir}/.fetched`);
writeFileSync(`${dir}/.fetched/${log}.jsonl`, run.ledger.map(({ source, path, a, b, at, text }) =>
  JSON.stringify({ source, path, a, b, at, text })).join("\n") + "\n");
const py = JSON.parse(execFileSync(PY, ["-c", `
import json, sys
from dataclasses import asdict
sys.path.insert(0, ${JSON.stringify(here + "..")})
from audit import store, fetch, report
d = sys.argv[1]
rec = store.load(d)
def j(x):
    if isinstance(x, (set, frozenset)): return sorted(j(i) for i in x)
    if isinstance(x, dict): return {k: j(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [j(i) for i in x]
    return x
out = j(asdict(report(rec)))
out["unfetched"] = fetch.unfetched(d, rec)
out["committed_after_reading"] = fetch.read_first(d, rec)
print(json.dumps(out))
`, dir]).toString());
const js = T.report(run);
const diff = Object.keys(py).filter(k => canonical(js[k]) !== canonical(py[k]));
ok(!diff.length, "Python loads the log (hashes, signatures) and gives the same report" + (diff.length ? `; differs in ${diff.join(", ")}` : ""));
for (const k of diff) console.log("   js:", canonical(js[k]).slice(0, 300), "\n   py:", canonical(py[k]).slice(0, 300));
ok(Object.keys(js.unfetched).join() === `${log}:l2` && Object.keys(js.committed_after_reading).join() === `${log}:c1`, "unfetched and committed_after_reading are reported");

// plain() and unquoted() against fetch.py on a few strings
const cases = [
  ["\\emph{a} b\\footnote{c \\textit{d}} % x", 'a "b" c'],
  ["he said ``no'' and \\cite{k} left~now", 'he said "no" and left now'],
  ['there is no "widow" here', 'a "there is no "widow" here" b'],
  ["one two", 'a “one two” b “three”'],
];
const pyp = JSON.parse(execFileSync(PY, ["-c", `
import json, sys
sys.path.insert(0, ${JSON.stringify(here + "..")})
from audit import fetch
cs = json.loads(sys.argv[1])
print(json.dumps([[fetch.plain(t), fetch.unquoted(b, (fetch._norm(t), fetch._norm(fetch.plain(t))))] for t, b in cs]))
`, JSON.stringify(cases)]).toString());
const jsp = cases.map(([t, b]) => [L.plain(t), L.unquoted(b, [L.norm(t), L.norm(L.plain(t))])]);
ok(canonical(jsp) === canonical(pyp), "plain() and unquoted() agree with fetch.py");
if (canonical(jsp) !== canonical(pyp)) console.log("   js:", canonical(jsp), "\n   py:", canonical(pyp));

console.log(bad ? `${bad} failed` : "all checks pass");
process.exit(bad ? 1 : 0);
