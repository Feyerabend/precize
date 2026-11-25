/* The live page: a Claude model as the agent run, called from the browser with the
   visitor's own key, writing through the tools in tools.js. The loop is written out by
   hand so that each turn can be shown and the run stopped between turns. */
// The SDK is loaded when a run starts, so the page works (and says what failed) without it.
const SDK = "https://cdn.jsdelivr.net/npm/@anthropic-ai/sdk@1.8.0/+esm";
let Anthropic = null;

const A = window.Audit, L = window.Ledger, T = window.LiveTools, SERVER = window.SERVER;
const $ = s => document.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat(Infinity)) if (c != null && c !== false && c !== "") n.append(c instanceof Node ? c : document.createTextNode(c));
  return n;
};
const short = (s, n = 300) => { s = (s || "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1) + "…" : s; };

const FALLBACKS = new Set(["claude-opus-5-5", "claude-sonnet-5-5"]);   // server-side fallbacks
const MAX_TOKENS = 16000;
const P = { run: null, messages: [], stop: false, abort: null, turns: 0, usage: { in: 0, out: 0, cacheRead: 0, cacheWrite: 0 }, models: new Set() };

// ------------------------------------------------------------------ setup
$("#card").textContent = window.CARD || "";
$("#help-btn").addEventListener("click", () => {
  const h = $("#help"); h.hidden = !h.hidden; $("#help-btn").setAttribute("aria-expanded", String(!h.hidden));
});

function addDoc(path = "", text = "") {
  const box = $("#docs"), i = box.children.length;
  const name = el("input", { value: path || (i ? `document-${i + 1}.txt` : "source.txt"), spellcheck: "false", "aria-label": "Document name" });
  const area = el("textarea", { spellcheck: "false", "aria-label": "Document text", placeholder: i ? "Another text the agent may read." : "The text that holds the sentence." });
  area.value = text;
  const n = el("span", { class: "n" });
  const count = () => { n.textContent = `${area.value ? area.value.replace(/\n$/, "").split("\n").length : 0} lines`; fillSentence(); renderBrief(); };
  area.addEventListener("input", count); name.addEventListener("input", renderBrief);
  const rm = el("button", { class: "ghost", text: "Remove", onclick: () => { d.remove(); renderBrief(); } });
  const d = el("div", { class: "doc" }, el("div", { class: "doc-head" }, el("b", { text: i ? "Document" : "Document with T₀" }), name, n, i ? rm : null), area);
  box.append(d); count();
}
const docs = () => [...document.querySelectorAll("#docs .doc")].map(d => ({ path: d.querySelector("input").value.trim(), text: d.querySelector("textarea").value }));

let autoSentence = true;
function fillSentence() {
  const d = docs()[0]; if (!d || !autoSentence) return;
  const line = d.text.split(/\r?\n/)[(parseInt($("#line").value, 10) || 1) - 1] || "";
  $("#sentence").value = line.trim();
}
$("#line").addEventListener("input", () => { autoSentence = true; fillSentence(); renderBrief(); });
$("#sentence").addEventListener("input", () => { autoSentence = false; renderBrief(); });
for (const id of ["#person", "#role", "#lang"]) $(id).addEventListener("input", renderBrief);
$("#add-doc").addEventListener("click", () => addDoc());
$("#file").addEventListener("change", async ev => {
  for (const f of ev.target.files) {
    const text = await f.text();
    const first = document.querySelector("#docs .doc textarea");
    if (first && !first.value.trim()) { first.value = text; document.querySelector("#docs .doc input").value = f.name; first.dispatchEvent(new Event("input")); }
    else addDoc(f.name, text);
  }
  ev.target.value = "";
});
$("#example").addEventListener("click", async () => {
  try {
    const get = async p => (await fetch(p)).text();
    const [rules, minutes] = await Promise.all([get("examples/allotment-rules.txt"), get("examples/committee-minutes.txt")]);
    $("#docs").replaceChildren(); addDoc("allotment-rules.txt", rules); addDoc("committee-minutes.txt", minutes);
    $("#line").value = rules.split("\n").findIndex(l => l.startsWith("3.1 ")) + 1; autoSentence = true; fillSentence();
    $("#sentence").value = $("#sentence").value.replace(/^3\.1\s+/, ""); autoSentence = false; renderBrief();
  } catch (x) { showError("The example did not load: " + x.message); }
});

function renderBrief() {
  const d = docs();
  $("#brief").textContent = d.length && d[0].path
    ? T.brief({ log: `g1 (for ${$("#person").value.trim() || "V"})`, person: $("#person").value.trim() || "V", role: $("#role").value, lang: $("#lang").value,
        line: parseInt($("#line").value, 10) || 1, sentence: $("#sentence").value.trim(), docs: d.map(x => x.path) })
    : "";
}
function showError(msg) { const b = $("#setup-error"); b.textContent = msg; b.hidden = !msg; }
addDoc();

// ------------------------------------------------------------------ the run
$("#start").addEventListener("click", start);
$("#stop").addEventListener("click", () => { P.stop = true; if (P.abort) P.abort.abort(); status("Stopping…"); });

async function start() {
  showError("");
  const key = $("#key").value.trim(), d = docs(), person = $("#person").value.trim() || "V";
  const line = parseInt($("#line").value, 10) || 1, sentence = $("#sentence").value.trim();
  if (!key) return showError("Paste your Anthropic API key first.");
  if (!d.length || !d[0].text.trim()) return showError("Give the text that holds the sentence.");
  const names = d.map(x => x.path);
  if (names.some(p => !p || /[,§]/.test(p)) || new Set(names).size !== names.length)
    return showError("Each document needs its own name, without commas or §.");
  if (!sentence) return showError("Give the sentence under audit, T₀.");
  if (line > d[0].text.split(/\r?\n/).length) return showError(`The first document has no line ${line}.`);
  if (!Anthropic) {
    status("Loading the Anthropic SDK…");
    try { Anthropic = (await import(SDK)).default; }
    catch (x) { status(""); return showError("Could not load the Anthropic SDK from cdn.jsdelivr.net (" + x.message + "). Check the connection, or a blocker that stops that site, and start again."); }
    status("");
  }
  let run;
  try { run = await T.newRun({ docs: d, line, sentence, person, role: $("#role").value, lang: $("#lang").value, model: $("#model").value, card: window.CARD }); }
  catch (x) { return showError(x.message.includes("Ed25519") || x.name === "NotSupportedError" ? "This browser cannot make an Ed25519 key (it needs a recent Chrome, Safari or Firefox)." : x.message); }

  Object.assign(P, { run, messages: [{ role: "user", content: T.brief(run) }], stop: false, turns: 0,
    usage: { in: 0, out: 0, cacheRead: 0, cacheWrite: 0 }, models: new Set() });
  const client = new Anthropic({ apiKey: key, dangerouslyAllowBrowser: true });
  for (const i of document.querySelectorAll("#setup input, #setup select, #setup textarea, #setup button")) i.disabled = true;
  $("#stop").disabled = false;
  $("#run").hidden = false; $("#done").hidden = true; $("#trace").replaceChildren(); $("#log-name").textContent = run.log;
  renderEntries(); renderStats();
  $("#run").scrollIntoView({ behavior: "smooth" });
  try { await loop(client); }
  catch (x) { step("sys", explainError(x)); }
  finally {
    $("#stop").disabled = true; P.abort = null;
    for (const i of document.querySelectorAll("#setup button")) i.disabled = false;
    $("#stop").disabled = true;
    for (const i of document.querySelectorAll("#setup input, #setup select, #setup textarea")) i.disabled = false;
    finish();
  }
}

function explainError(x) {
  if (x && x.name === "AbortError" || (x && /abort/i.test(x.message || ""))) return "Stopped.";
  const s = x && x.status;
  if (s === 401) return "The API refused the key (401). Check that it is an Anthropic API key with credit.";
  if (s === 429) return "Rate limited (429). Wait a little and start again, or lower the effort.";
  if (s === 529 || s === 503) return `The API is overloaded (${s}). Try again in a while.`;
  if (s === 400) return "The API refused the request (400): " + ((x.error && x.error.error && x.error.error.message) || x.message);
  return "The run stopped on an error: " + (x && x.message || String(x));
}

const system = () => T.system(P.run, SERVER).map((text, i, all) =>
  i === all.length - 1 ? { type: "text", text, cache_control: { type: "ephemeral" } } : { type: "text", text });

/* One cache breakpoint at the end of the conversation, moved forward every turn. */
function markCache(messages) {
  for (const m of messages) if (Array.isArray(m.content)) for (const b of m.content) delete b.cache_control;
  const last = messages[messages.length - 1];
  if (typeof last.content === "string") last.content = [{ type: "text", text: last.content }];
  last.content[last.content.length - 1].cache_control = { type: "ephemeral" };
}

async function loop(client) {
  const model = P.run.model, max = Math.max(1, parseInt($("#max-turns").value, 10) || 40);
  const tools = T.toolDefs(SERVER), sys = system();
  while (!P.stop) {
    if (P.turns >= max) { step("sys", `The turn limit (${max}) is reached. The run stops without its close entry.`); break; }
    markCache(P.messages);
    const params = { model, max_tokens: MAX_TOKENS, system: sys, tools, messages: P.messages };
    if (!model.includes("haiku")) params.output_config = { effort: $("#effort").value };
    if (FALLBACKS.has(model)) { params.betas = ["server-side-fallback-2026-07-01"]; params.fallbacks = "default"; }
    P.abort = new AbortController();
    status(`Turn ${P.turns + 1}: waiting for ${model}…`);
    const r = await client.beta.messages.create(params, { signal: P.abort.signal });
    P.turns++; P.models.add(r.model);
    const u = r.usage || {};
    P.usage.in += u.input_tokens || 0; P.usage.out += u.output_tokens || 0;
    P.usage.cacheRead += u.cache_read_input_tokens || 0; P.usage.cacheWrite += u.cache_creation_input_tokens || 0;
    renderStats();
    P.messages.push({ role: "assistant", content: r.content });
    for (const b of r.content) if (b.type === "text" && b.text.trim()) step("say", b.text);
    if (r.stop_reason === "refusal") { step("sys", "The model declined to go on (stop reason: refusal)."); break; }
    if (r.stop_reason === "pause_turn") continue;
    const uses = r.content.filter(b => b.type === "tool_use");
    const results = [];
    for (const b of uses) {
      let out, isError = false;
      try { out = await T.call(P.run, b.name, b.input); }
      catch (x) { out = { error: x.message }; isError = true; }
      showTool(b, out, isError);
      results.push({ type: "tool_result", tool_use_id: b.id, content: JSON.stringify(out), ...(isError ? { is_error: true } : {}) });
    }
    renderEntries();
    if (results.length) { P.messages.push({ role: "user", content: results }); continue; }
    if (r.stop_reason === "max_tokens") { P.messages.push({ role: "user", content: "Your reply was cut off at the output limit. Go on from where you stopped." }); continue; }
    break;   // end_turn with no tool call: the agent is done
  }
  status(P.run.closed ? "The run is closed." : "The run has stopped.");
}

// ------------------------------------------------------------------ showing it
function status(s) { $("#status").textContent = s; }
function step(kind, text) {
  const t = $("#trace");
  t.append(el("div", { class: "step " + kind, text }));
  t.lastChild.scrollIntoView({ block: "nearest" });
}
function showTool(b, out, isError) {
  const i = b.input || {};
  let head;
  if (b.name === "write") head = [el("code", { text: `write ${i.act || "?"} ${i.id || ""}` }), i.value ? ` ${short(String(i.value), 60)}` : ""];
  else if (b.name === "read") head = [el("code", { text: `read ${i.path || ""}, lines ${i.start || 1}-${i.end || ""}` })];
  else if (b.name === "entry") head = [el("code", { text: `entry ${i.ref || ""}` })];
  else head = [el("code", { text: b.name })];
  const refused = out && out.refused;
  const outText = refused ? `${out.refused}: ${out.message}` : b.name === "read" ? `${out.source || ""}\n${short(out.text, 400)}`
    : b.name === "report" ? reportBrief(out) : JSON.stringify(out);
  $("#trace").append(el("div", { class: "step tool" + (refused || isError ? " refused" : "") },
    refused ? el("b", { text: "Refused. " }) : null, head, el("div", { class: "out", text: outText })));
  $("#trace").lastChild.scrollIntoView({ block: "nearest" });
}
function reportBrief(R) {
  const n = x => Array.isArray(x) ? x.length : x && typeof x === "object" ? Object.keys(x).length : 0;
  return Object.entries(R).filter(([, v]) => n(v)).map(([k, v]) => `${k}: ${n(v)}`).join(", ") || "(empty)";
}
function renderStats() {
  const s = $("#stats"), u = P.usage;
  const box = (label, v) => el("div", {}, el("b", { text: String(v) }), label);
  s.replaceChildren(box("turns", P.turns), box("entries", P.run ? P.run.logs[P.run.log].length : 0),
    box("refused", P.run ? P.run.refused.length : 0), box("input tokens", u.in), box("cache read", u.cacheRead),
    box("cache written", u.cacheWrite), box("output tokens", u.out),
    P.models.size ? box("answered by", [...P.models].join(", ")) : null);
}
function renderEntries() {
  const es = P.run.logs[P.run.log].map(A.entry);
  $("#entries").replaceChildren(...(es.length ? es.map(card) : [el("p", { class: "muted", text: "No entries yet." })]));
  renderStats();
}
function card(e) {
  const meta = [];
  const add = (label, rs) => { if (rs.length) meta.push(el("div", {}, label + " ", rs.map(r => el("span", { class: "chip", text: r })))); };
  add("rests on", e.rests); if (e.narrows) add("narrows", [e.narrows]); if (e.about) add("about", [e.about]);
  add("answers", e.answers.map(a => a.ref)); add("between", e.between); if (e.withdraws) add("withdraws", [e.withdraws]);
  if (e.sources.length) meta.push(el("div", { text: "sources: " + e.sources.join("; ") }));
  if (e.via) meta.push(el("div", { text: "via: " + e.via }));
  return el("div", { class: "entry new" },
    el("div", { class: "head" }, el("span", { class: "act", text: e.act }), el("span", { class: "ref", text: A.ref(e) }),
      e.value != null && el("span", { class: "val", text: short(String(e.value), 90) })),
    e.object && el("div", { class: "meta", text: "object " + e.object }),
    e.body && el("div", { class: "body", text: short(e.body, 600) }),
    meta.length ? el("div", { class: "meta" }, meta) : null);
}

function finish() {
  if (!P.run || !P.run.logs[P.run.log].length) return;
  const R = T.report(P.run), items = [];
  const li = (...k) => items.push(el("li", {}, ...k));
  li(`${P.run.logs[P.run.log].length} entries in ${P.turns} turns; ${P.run.refused.length} writes refused` +
    (P.run.refused.length ? ` (${[...new Set(P.run.refused.map(x => x.rule))].join(", ")})` : "") + ".");
  if (R.proposed.length) li("Proposed verdicts: ", R.proposed.map(r => {
    const e = P.run.logs[P.run.log].find(x => `${x.log}:${x.id}` === r); return `${e ? e.value : "?"} (${r})`; }).join("; "));
  if (Object.keys(R.awaiting_grant).length) li("Norms waiting for a person's grant: ", Object.keys(R.awaiting_grant).join(", "));
  if (R.open_asks.length) li("Questions for a person: ", R.open_asks.join(", "));
  if (Object.keys(R.unfetched).length) li("Sources cited but not fetched: ", Object.entries(R.unfetched).map(([k, v]) => `${k} (${v.join("; ")})`).join(", "));
  if (Object.keys(R.committed_after_reading).length) li("Commitments written after reading more than T₀: ", Object.keys(R.committed_after_reading).join(", "));
  if (!P.run.closed) li("The log has no close entry: the run was stopped, or ended without closing.");
  $("#summary").replaceChildren(el("ul", {}, items));
  $("#done").hidden = false;
}

function trial() {
  return T.asTrial(P.run, { setup: `Run in the live page by ${[...P.models].join(", ") || P.run.model}, ` +
    `effort ${$("#effort").value}, as the ${P.run.role} run, in ${P.turns} turns.`,
    outcome: (P.messages.filter(m => m.role === "assistant").flatMap(m => m.content).filter(b => b.type === "text").map(b => b.text).pop() || "") });
}
function download(name, text, type) {
  const a = el("a", { href: URL.createObjectURL(new Blob([text], { type })), download: name });
  document.body.append(a); a.click(); a.remove();
}
$("#to-playground").addEventListener("click", () => {
  try { sessionStorage.setItem("live-run", JSON.stringify(trial())); }
  catch (x) { showError("This browser would not hand the run over (" + x.message + "). Download the run and load it in the playground."); return; }
  location.href = "../playground/#live";
});
$("#dl-run").addEventListener("click", () => download("live-run.json", JSON.stringify(trial(), null, 1) + "\n", "application/json"));
$("#dl-transcript").addEventListener("click", () => download("live-transcript.json",
  JSON.stringify({ model: P.run.model, models: [...P.models], usage: P.usage, system: T.system(P.run, SERVER), messages: P.messages }, null, 1) + "\n", "application/json"));
