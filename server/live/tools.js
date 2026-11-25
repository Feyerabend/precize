/* The live page's tools: the MCP server's write, read, report and entry over the record in
   the page (../playground/audit.js) and the fetch ledger (ledger.js). No model calls here,
   so check.mjs can run the tools in Node with a scripted agent.

   A run is one audit with one agent log. The tools take the server's arguments, less
   `audit` (there is one). The agent's key is made in the page and signs each entry. */
(function (root) {
  "use strict";
  const A = root.Audit || require("../playground/audit.js");
  const L = root.Ledger || require("./ledger.js");
  const NAME = /^[A-Za-z0-9][A-Za-z0-9 ._()\-]{0,63}$/;   // as server.py: no ':' or '/'

  /* docs: [{path, text}]; the first holds T₀. */
  async function newRun({ docs, line, sentence, person = "V", role = "evidence", lang = "en",
    model = "", card = "" }) {
    const log = `g1 (for ${person})`;
    if (!NAME.test(log)) throw new Error(`the log name ${log} is not allowed; use a shorter name without ':' or '/'`);
    const files = new Map();
    for (const d of docs) files.set(d.path, d.text.replace(/\r\n?/g, "\n"));
    if (card) files.set(L.CARD, card);
    return { log, person, role, lang, model, line, sentence, docs: docs.map(d => d.path), files,
      logs: { [log]: [] }, keys: {}, ledger: [], key: await A.newKey(), refused: [], closed: false };
  }

  const load = run => {
    const logs = {};
    for (const [l, es] of Object.entries(run.logs)) if (es.length) logs[l] = es;
    const rec = A.Record.load(logs, run.keys);
    rec.checks = true;
    return rec;
  };

  // ------------------------------------------------------------------- the tools
  function read(run, { log, path, start = 1, end = null, plain = false }) {
    if (!NAME.test(log || "")) return { refused: "name", message: `bad log name ${JSON.stringify(log)}` };
    if (log !== run.log) return { refused: "name", message: `this run reads and writes one log, ${run.log}; a fetch counts only for the log it is made under` };
    if (!run.files.has(path))
      return { refused: "path", message: `no source ${JSON.stringify(path)}; the documents are ${[...run.files.keys()].join(", ")}` };
    const lines = run.files.get(path).split("\n");
    if (lines.length && lines[lines.length - 1] === "") lines.pop();   // as splitlines()
    start = Math.max(1, parseInt(start, 10) || 1);
    end = Math.min(end ? parseInt(end, 10) : lines.length, lines.length, start + 399);
    const text = lines.slice(start - 1, end).join("\n");
    const source = `${path}, lines ${start}-${end}`;
    run.ledger.push({ log, source, path, a: start, b: end, at: (run.logs[log] || []).length, text });
    return { source, text: plain ? L.plain(text) : text };
  }

  const FIELDS = ["id", "act", "body", "kind", "value", "object", "sources", "rests", "answers",
    "about", "between", "narrows", "withdraws", "reason", "procedure", "via"];

  async function write(run, args) {
    const { log, kind = "person", after = null } = args;
    const refuse = (rule, message) => { run.refused.push({ rule, message, act: args.act, id: args.id }); return { refused: rule, message }; };
    if (!NAME.test(log || "")) return refuse("name", `bad log name ${JSON.stringify(log)}`);
    if (kind !== "agent") return refuse("person", "this page signs only agent logs; a person writes in the playground, with their own key");
    if (log !== run.log) return refuse("name", `this run writes one log, ${run.log}`);
    const d = {};
    for (const k of FIELDS) if (args[k] !== undefined && args[k] !== null) d[k] = args[k];
    d.kind = "agent"; d.body = d.body || "";
    d.answers = (args.answers || []).map(a => ({ ref: a.ref, disputes: !!a.disputes, meets: a.meets === undefined ? null : a.meets }));
    if (args.absent_what) d.absent = { in: args.absent_in || "world", what: args.absent_what, where: args.absent_where || null };
    if (!run.keys[log]) run.keys[log] = { kind: "agent", key: run.key.pub };
    const fresh = !run.logs[log].length;
    let e;
    try {
      const rec = load(run);
      if (d.act === "precize" && !d.narrows)
        throw new A.Refused("narrows", `${log}:${d.id}: a precize names what it narrows (the mark, for first readings)`);
      e = rec.add(log, d, after);
      L.check(A, rec, e, run.ledger.filter(f => f.log === log), A.Refused);
      e.sig = await A.sign(run.key, e.hash);
    } catch (x) {
      if (fresh) delete run.keys[log];
      if (x instanceof A.Refused) return refuse(x.rule, x.message.slice(x.rule.length + 2));
      return refuse("cite", `no such entry: ${x.message}`);
    }
    run.logs[log].push(A.toJson(e));
    if (e.act === "close") run.closed = true;
    const out = { ref: A.ref(e), hash: e.hash };
    if (e.act === "commit") {
      const first = L.readFirst(load(run), ledgers(run))[A.ref(e)];
      if (first) out.note = "written after you fetched " + first.join("; ") + ". It stands, " +
        "but the report lists it under committed_after_reading: a commit is meant to come " +
        "before the reading that could meet it.";
    }
    return out;
  }

  const ledgers = run => {
    const out = {};
    for (const f of run.ledger) (out[f.log] = out[f.log] || []).push(f);
    return out;
  };

  function report(run) {
    const rec = load(run);
    const R = A.plain(A.report(rec));
    R.unfetched = L.unfetched(rec, ledgers(run));
    R.committed_after_reading = L.readFirst(rec, ledgers(run));
    return R;
  }

  function entry(run, { ref }) {
    const rec = load(run);
    const e = rec.get(ref);
    if (!e) return { error: `no entry ${ref}` };
    return { entry: A.toJson(e),
      rested_on_by: rec.entries().filter(x => x.rests.includes(ref)).map(A.ref),
      answered_by: rec.entries().filter(x => x.answers.some(a => a.ref === ref)).map(A.ref) };
  }

  async function call(run, name, input) {
    switch (name) {
      case "write": return write(run, input || {});
      case "read": return read(run, input || {});
      case "report": return report(run);
      case "entry": return entry(run, input || {});
      default: throw new Error(`no tool ${name}`);
    }
  }

  // ------------------------------------------------------------------- what the model gets
  const str = d => ({ type: "string", description: d });
  const refs = d => ({ type: "array", items: { type: "string" }, description: d });
  function toolDefs(S) {
    const page = "\n\n(In this page there is one audit, so the server's `audit` argument is left out.)";
    return [
      { name: "write", description: S.tools.write + page,
        input_schema: { type: "object", required: ["log", "id", "act"], properties: {
          log: str("your log name, as the brief gives it"), id: str("the entry's id, unique in your log"),
          act: { type: "string", enum: ["quote", "mark", "vary", "precize", "holder", "grid", "property", "recover", "grant", "check", "commit", "look", "verdict", "withdraw", "settle", "decide", "close", "ask", "show"] },
          body: str("the entry's text"), kind: str("'agent'"), value: str("the claim's value"),
          object: str("what the claim is about: a ref"), sources: refs("passages read, as `read` returned them"),
          rests: refs("refs the entry rests on"),
          answers: { type: "array", items: { type: "object", required: ["ref"], properties: {
            ref: { type: "string" }, disputes: { type: "boolean" }, meets: { type: "boolean" } } } },
          about: str("a commit's object"), between: refs("for a verdict: the precizes in dispute"),
          narrows: str("a precize's target"), withdraws: str("the entry withdrawn"), reason: str("why"),
          procedure: str("a grant's procedure"), absent_what: str("what is not there"),
          absent_where: str("where it was looked for"), absent_in: str("default 'world'"),
          via: str("the document a second-hand passage quotes"), after: str("chain to this own entry instead of the last") } } },
      { name: "read", description: S.tools.read + page,
        input_schema: { type: "object", required: ["log", "path"], properties: {
          log: str("your log name"), path: str("a document's name"),
          start: { type: "integer", description: "first line, from 1" }, end: { type: "integer", description: "last line (at most start+399)" },
          plain: { type: "boolean", description: "take LaTeX markup out" } } } },
      { name: "report", description: S.tools.report + page.replace("argument is", "and `logs`/`heads` arguments are"),
        input_schema: { type: "object", properties: {} } },
      { name: "entry", description: S.tools.entry + page,
        input_schema: { type: "object", required: ["ref"], properties: { ref: str("LOG:id") } } },
    ];
  }

  function system(run, S) {
    const docs = run.docs.map((p, i) => `- \`${p}\`, ${run.files.get(p).split("\n").length} lines${i === 0 ? " (holds T₀)" : ""}`).join("\n");
    return [
      "This is a browser page that runs the MCP server `audit-record` for one agent run. Its " +
      "tools are the server's (`write`, `read`, `report`, `entry`) with the same rules, " +
      "ported to JavaScript, less the `audit` argument: there is one audit. The card is " +
      "given below instead of as the resource audit://card; it can also be fetched as " +
      `\`${L.CARD}\`. The documents \`read\` can fetch are:\n${docs}\n\n` +
      "The server's instructions follow.\n\n" + S.instructions,
      "The card (the procedure on one page, Appendix A of Saying What You Mean):\n\n" + root_card(run),
    ];
  }
  const root_card = run => run.files.get(L.CARD) || "";

  function brief(run) {
    const p = run.person, T = run.docs[0];
    const lang = run.lang === "sv" ? "Write every entry body in Swedish. Act names, field names and verdict values stay as the server defines them. Quotes stay verbatim.\n\n" : "";
    const steps = run.role === "drafting"
      ? "You are the drafting run. Steps: 1. Quote T₀, fetching only its line. 2. Mark the term(s) the claim turns on; you decide which. 3. Vary and precize the readings (with `narrows`). 4. Name the property, if any. 5. Propose a verdict with your quote as the object."
      : `You are the evidence run. Steps: 1. Quote T₀, fetching only line ${run.line} at first. 2. Mark the term(s) the claim turns on; you decide which. 3. BEFORE fetching more, write your commit: what would change your mind. 4. Fetch through \`read\` what you need; cite the \`source\` it returns; record what is absent. 5. Precize the readings (with \`narrows\`). Look, then propose a verdict with your quote as the object.`;
    return `You are agent run \`${run.log}\` in this audit. Your log name is \`${run.log}\`, with the parentheses: pass it as \`log\` in every \`write\` and \`read\`. First read the instructions, the \`write\` and \`read\` tool descriptions, and the card, all given above.\n\n` +
      `T₀ is in \`${T}\`, line ${run.line}: "${run.sentence}"\n\n` + lang + steps + "\n\n" +
      `Stop at holder, grant, settle and the audit's verdict; those are for person ${p}. End with \`act='close'\`. Write only through the tools. When done, report in a few lines, in English: what you wrote; anything refused, and why; anything unclear in the instructions.`;
  }

  /* The run as a playground case: {name, about, keys, logs}, plus what was fetched. */
  function asTrial(run, extra = {}) {
    return { name: "live-run", live: true,
      about: Object.assign({ trial: "Your live run", sentence: run.sentence,
        source: `${run.docs[0]}, line ${run.line}`,
        about: `A live run on a text the visitor gave: ${run.docs.join(", ")}.` }, extra),
      keys: Object.assign({}, run.keys), logs: JSON.parse(JSON.stringify(run.logs)),
      fetched: run.ledger.map(({ log, source, at }) => ({ log, source, at })) };
  }

  const api = { newRun, call, toolDefs, system, brief, report, asTrial, NAME };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.LiveTools = api;
})(typeof window !== "undefined" ? window : globalThis);
