/* The playground page: replay a trial's agent logs, let a visitor write person entries
   (signed in the browser), and compute the report. All record logic is in audit.js. */
(function () {
  "use strict";
  const A = window.Audit, TRIALS = (window.TRIALS || []).slice();
  /* A run from the live page (../live/), handed over in this tab's sessionStorage. */
  let LIVE = null;
  try { LIVE = JSON.parse(sessionStorage.getItem("live-run") || "null"); } catch (x) { LIVE = null; }
  if (LIVE && LIVE.logs) TRIALS.unshift(LIVE); else LIVE = null;
  const $ = s => document.querySelector(s);
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k === "html") n.innerHTML = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
    }
    for (const c of kids.flat(Infinity)) if (c != null && c !== false && c !== "") n.append(c instanceof Node ? c : document.createTextNode(c));
    return n;
  };
  const short = (s, n = 110) => { s = (s || "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1) + "…" : s; };

  const ACT_HELP = {
    quote: "Quotes the sentence under audit, T₀, from its source.",
    mark: "Marks the word in the quote that the sentence turns on.",
    vary: "Runs the sentence through each reading of the word: true under all, false under all, or it varies.",
    precize: "States one reading of the marked word, sharply enough to tell it from the others.",
    holder: "Says who holds a reading. A person's act: an agent may not say what people mean.",
    grid: "Sets the readings against cases, to see where they come apart.",
    property: "Names what the readings aim at: the property a rule should track.",
    recover: "Recovers a norm the sentence relies on, for a person to accept or not.",
    grant: "A person accepts a recovered norm as one they rely on. A person's act.",
    check: "Checks the sentence against a norm a person has granted.",
    commit: "Says in advance what the run already knows or expects, before it looks.",
    look: "Looks in a source and reports what it says.",
    verdict: "Says what kind of disagreement this is, by the card. From an agent it is only a proposal.",
    withdraw: "Takes back an earlier entry in the same log. What rests on it falls.",
    settle: "A person settles an open pair by answering both sides.",
    decide: "A person who said nescio picks the reading they go by.",
    close: "Closes the log, with a note on where the run stopped and what it left.",
    ask: "Asks a question that someone else in the record may answer.",
    show: "Points another author at something.",
  };
  const VERDICTS = [
    ["1a", "1a pseudo-disagreement: the two take the word differently and do not really disagree"],
    ["1b", "1b pseudo-agreement: they seem to agree but mean different things"],
    ["2", "2 real disagreement: they mean the same and differ on what is so"],
    ["3", "3 equivocation: the word shifts its reading inside one argument"],
    ["4", "4 rule–property divergence: the rule as written misses what it aims at"],
    ["5", "5 pseudo-alternatives: the options offered are not really alternatives"],
    ["none", "none: no verdict on what has been said so far"],
  ];
  const RULES = {
    unique: "That id is already taken in your log.",
    cite: "An entry may only name entries that are on the record.",
    value: "This act needs both a value (what you claim) and an object (what it is about).",
    nescio: "Nescio, “I do not know”, is about you, and it rests on two or more readings you are in doubt between.",
    decide: "A decide answers one nescio, picks one of the readings that nescio was in doubt between, and rests on it.",
    between: "Only a verdict names readings in dispute, and it names two or more readings. You cannot give a second, different verdict on the same readings without first withdrawing the first.",
    settle: "A settle answers both sides of an open pair.",
    grant: "A grant must rest on a norm someone recovered, or name a procedure.",
    "own-only": "You can withdraw only entries in your own log.",
    close: "Your log is closed. Nothing more can be written to it.",
    withdraw: "A withdrawal names the entry it takes back.",
    key: "Your entries must be signed with the key registered for your log.",
    kind: "One log, one kind of author.",
    person: "This act needs a person as author.",
    sources: "Sources name texts; entries are named in what an entry rests on.",
  };
  const FLAGS = {
    awaiting_grant: ["Norms recovered, not yet granted", "An agent recovered a norm the sentence relies on. Only a person can accept it."],
    unread_marks: ["Marked words with no reading", "A word was marked but no reading of it was spelled out."],
    marks_differ: ["The runs marked different words", "In the same quote, the authors marked different words."],
    marks_nested: ["One marked phrase holds another", "One author's marked words contain another author's."],
    same_object: ["Claims by different authors on the same thing", "They may agree; where they differ, the pair is listed as open above."],
    pending_commits: ["Commitments nothing has met", "A run said in advance what it expected; no later entry says whether it held."],
    met_unanswered: ["Commitments met, not taken up", "A later entry met the commitment, and its author has not answered."],
    single_source: ["Looks that rest on one document", ""],
    second_hand: ["Looks read second-hand", ""],
    stops: ["Where the procedure stops", ""],
    constitutive: ["Rules that make what they name", "What rests on a constitutive rule:"],
    loose_objects: ["Claims whose object names no entry", ""],
    drift: ["Readings narrowed after looking", "A reading changed after the run looked things up."],
    open_asks: ["Questions no one has answered", ""],
    answers_to_compare: ["Answers to compare by hand", ""],
    grant_withdrawals: ["Grants withdrawn", ""],
    evidence_unread: ["Evidence for a withdrawal not in this record", ""],
    rests_unread: ["Entries resting on what is not here", "They rest on entries this record does not hold, so they do not stand here."],
    unverified: ["Person acts in unsigned logs", "No key is registered for these logs, so nothing shows who wrote them."],
    unsigned_logs: ["Logs without a key", ""],
    logs_not_read: ["Logs cited but not loaded", ""],
    entries_not_read: ["Entries cited but not loaded", ""],
    forks: ["Forks in a log", ""],
    entries_as_sources: ["Entries named as sources", ""],
  };

  const S = { trial: null, seq: [], shown: 0, me: null, key: null, mine: {}, act: "reader", withPersons: false };

  // -------------------------------------------------------------- helpers on a trial
  const kindOf = (t, log) => (t.keys[log] && t.keys[log].kind) || ((t.logs[log] || [])[0] || {}).kind || "agent";
  const agentLogs = t => Object.keys(t.logs).filter(l => kindOf(t, l) === "agent");
  const personLogs = t => Object.keys(t.logs).filter(l => kindOf(t, l) === "person");
  /* Person logs the agents cite: without them the agents' own entries would not stand. */
  function neededPersons(t) {
    const ps = new Set(personLogs(t)), out = new Set();
    for (const l of agentLogs(t)) for (const d of t.logs[l]) for (const c of A.cites(A.entry(d))) {
      const log = c.split(":")[0]; if (ps.has(log)) out.add(log);
    }
    return out;
  }
  /* Show order: the agent runs side by side, a step each; a person entry when no agent
     entry can go first; never an entry before what it cites. */
  function sequence(t) {
    const q = {}, done = new Set(), all = new Set(), out = [];
    for (const [l, es] of Object.entries(t.logs)) { q[l] = es.map(A.entry); for (const e of q[l]) all.add(A.ref(e)); }
    const ready = e => A.cites(e).every(c => done.has(c) || !all.has(c));
    const ag = agentLogs(t), ps = personLogs(t);
    while (out.length < all.size) {
      let moved = false;
      for (const l of ag) if (q[l].length && ready(q[l][0])) { const e = q[l].shift(); out.push(e); done.add(A.ref(e)); moved = true; }
      if (moved) continue;
      for (const l of ps) if (q[l].length && ready(q[l][0])) { const e = q[l].shift(); out.push(e); done.add(A.ref(e)); moved = true; break; }
      if (!moved) { for (const l of [...ag, ...ps]) while (q[l].length) out.push(q[l].shift()); }
    }
    return out;
  }
  function baseLogs(t, withPersons) {
    const keep = new Set([...agentLogs(t), ...neededPersons(t), ...(withPersons ? personLogs(t) : [])]);
    const logs = {}, keys = {};
    for (const l of keep) logs[l] = t.logs[l];
    for (const [l, k] of Object.entries(t.keys)) if (keep.has(l)) keys[l] = k;
    return { logs, keys };
  }
  function buildRecord(withMe = true) {
    const t = S.trial, { logs, keys } = baseLogs(t, S.withPersons);
    const mine = S.mine[t.name] || [];
    if (withMe && S.me && mine.length) logs[S.me] = mine;
    if (withMe && S.me && S.key) keys[S.me] = { kind: "person", key: S.key.pub };
    return A.Record.load(logs, keys);
  }

  // -------------------------------------------------------------- navigation
  function go(view) {
    if (view !== "start" && view !== "choose" && !S.trial) view = "choose";
    document.querySelectorAll(".view").forEach(v => v.classList.toggle("on", v.id === view));
    document.querySelectorAll("#steps button").forEach(b => b.classList.toggle("on", b.dataset.go === view));
    if (view === "watch") renderWatch();
    if (view === "turn") renderTurn();
    if (view === "report") renderReport();
    window.scrollTo(0, 0);
  }
  document.addEventListener("click", ev => {
    const b = ev.target.closest("[data-go]"); if (b) { ev.preventDefault(); go(b.dataset.go); }
  });
  $("#help-btn").addEventListener("click", () => {
    const h = $("#help"); h.hidden = !h.hidden; $("#help-btn").setAttribute("aria-expanded", String(!h.hidden));
  });
  $("#card").textContent = window.CARD || "";
  function updateNav() {
    document.querySelectorAll("#steps button").forEach(b => {
      b.disabled = !S.trial && !["start", "choose"].includes(b.dataset.go);
    });
  }

  // -------------------------------------------------------------- choose
  function renderCases() {
    const box = $("#cases"); box.replaceChildren();
    for (const t of TRIALS) {
      const ag = agentLogs(t).length, ps = personLogs(t).length;
      const n = Object.values(t.logs).reduce((s, es) => s + es.length, 0);
      box.append(el("button", { class: "case", onclick: () => pick(t) },
        el("span", { class: "t", text: t.about.trial || t.name }),
        el("span", { class: "s", text: "“" + short(t.about.sentence, 220) + "”" }),
        el("span", { class: "a", text: short(t.about.about, 240) }),
        el("span", { class: "tags", text: `${n} entries · ${ag} agent run${ag === 1 ? "" : "s"}` +
          (ps ? ` · ${ps} person${ps === 1 ? "" : "s"} wrote too` : "") })));
    }
  }
  function pick(t) {
    S.trial = t; S.seq = sequence(t); S.shown = 0; S.act = "reader";
    updateNav(); go("watch");
  }
  function caseHead(box) {
    const a = S.trial.about;
    box.replaceChildren(...[   // a case need not have every part (a live run has no outcome)
      el("div", { class: "t", text: (a.trial || S.trial.name) }),
      el("blockquote", { text: "“" + a.sentence + "”" }),
      el("details", {}, el("summary", { text: "What the case is about" }),
        a.source && el("p", {}, el("b", { text: "Source. " }), a.source),
        a.about && el("p", { text: a.about }),
        a.setup && el("p", {}, el("b", { text: "How the trial was run. " }), a.setup)),
      a.outcome && el("details", {}, el("summary", { text: "What happened in the trial (spoiler)" }),
        el("p", { text: a.outcome }), a.taught && el("p", { class: "muted", text: a.taught }))].filter(Boolean));
  }

  // -------------------------------------------------------------- entries
  const domId = r => "e-" + A.sha256hex(r).slice(0, 16);
  function chip(r, known) {
    const ok = known(r);
    return el("span", { class: "chip" + (ok ? "" : " missing"), title: ok ? "" : "not shown yet",
      text: r, onclick: () => flash(r) });
  }
  function flash(r) {
    const n = document.getElementById(domId(r));
    if (!n) return;
    n.scrollIntoView({ behavior: "smooth", block: "center" });
    n.classList.add("flash"); setTimeout(() => n.classList.remove("flash"), 1200);
  }
  function entryCard(e, { known = () => true, long = false, isNew = false, tag = "" } = {}) {
    const meta = [];
    const add = (label, refs) => { if (refs.length) meta.push(el("div", {}, label + " ", refs.map(r => chip(r, known)))); };
    add("rests on", e.rests);
    if (e.narrows) add("narrows", [e.narrows]);
    if (e.about) add("about", [e.about]);
    add("answers", e.answers.map(a => a.ref));
    add("between", e.between);
    if (e.withdraws) add("withdraws", [e.withdraws]);
    if (e.sources.length) meta.push(el("div", { text: "sources: " + e.sources.join("; ") }));
    if (e.reason) meta.push(el("div", { text: "reason: " + e.reason }));
    const body = long ? e.body : short(e.body, 300);
    return el("div", { class: "entry" + (e.kind === "person" ? " person" : "") + (isNew ? " new" : ""), id: domId(A.ref(e)) },
      el("div", { class: "head" },
        el("span", { class: "act", text: e.act }),
        el("span", { class: "ref", text: A.ref(e) }),
        e.value != null && el("span", { class: "val", text: short(String(e.value), 90) }),
        tag && el("span", { class: "muted", text: tag })),
      el("div", { class: "what", text: (A.isNescio(e) ? "Nescio: the author cannot tell which reading they go by." : ACT_HELP[e.act] || "") }),
      e.object && el("div", { class: "meta" }, "object ", known(e.object.split("|")[0].trim()) ? chip(e.object.split("|")[0].trim(), known) : e.object),
      body && el("div", { class: "body", text: body }),
      meta.length ? el("div", { class: "meta" }, meta) : null);
  }

  // -------------------------------------------------------------- watch
  function renderWatch() {
    caseHead($("#watch-head"));
    const t = S.trial, shown = S.seq.slice(0, S.shown), seen = new Set(shown.map(A.ref));
    const long = $("#long").checked, last = shown.length ? A.ref(shown[shown.length - 1]) : null;
    const cols = $("#columns"); cols.replaceChildren();
    const logs = [...agentLogs(t), ...personLogs(t)];
    for (const l of logs) {
      const es = shown.filter(e => e.log === l);
      const person = kindOf(t, l) === "person";
      cols.append(el("div", { class: "col" },
        el("h3", {}, l + " ", el("small", { text: person ? "a person in the trial" : "an agent run" })),
        es.length ? es.map(e => entryCard(e, { known: r => seen.has(r), long, isNew: A.ref(e) === last }))
                  : el("p", { class: "muted", text: "Nothing yet." })));
    }
    $("#step-label").textContent = `${S.shown} of ${S.seq.length} entries`;
    $("#prev").disabled = S.shown === 0;
    $("#next").disabled = $("#all").disabled = S.shown === S.seq.length;
    const agentsDone = S.seq.every((e, i) => i < S.shown || kindOf(t, e.log) === "person");
    const line = $("#line"); line.hidden = !agentsDone;
    if (agentsDone) renderLine(line);
    if (last) { const n = document.getElementById(domId(last)); if (n && S.shown > 1) n.scrollIntoView({ block: "nearest" }); }
  }
  $("#next").addEventListener("click", () => { S.shown = Math.min(S.seq.length, S.shown + 1); renderWatch(); });
  $("#prev").addEventListener("click", () => { S.shown = Math.max(0, S.shown - 1); renderWatch(); });
  $("#all").addEventListener("click", () => { S.shown = S.seq.length; renderWatch(); });
  $("#long").addEventListener("change", renderWatch);

  function renderLine(box) {
    const t = S.trial, { logs, keys } = baseLogs(t, false);
    for (const l of personLogs(t)) delete logs[l];
    const rec = A.Record.load(logs, keys), R = A.report(rec);
    const items = [];
    const verdicts = [...R.proposed].map(r => rec.get(r));
    if (verdicts.length) items.push(el("li", {}, "Proposed verdicts: ",
      verdicts.map((v, i) => [i ? "; " : "", el("b", { text: v.value }), ` (${A.ref(v)})`])));
    if (R.open_between_agents.length) items.push(el("li", {}, `${R.open_between_agents.length} open pair${R.open_between_agents.length === 1 ? "" : "s"} between the runs, which no person has taken up: `,
      R.open_between_agents.map(([a, b, why], i) => [i ? "; " : "", `${a} / ${b} (${short(why, 80)})`])));
    const ag = Object.keys(R.awaiting_grant);
    if (ag.length) items.push(el("li", { text: `Norms recovered and waiting for a person to grant them: ${ag.join(", ")}.` }));
    const nr = rec.entries().filter(e => e.act === "precize").length;
    items.push(el("li", { text: `${nr} readings spelled out. Nobody has said who holds them: that is a person's act.` }));
    const closes = rec.entries().filter(e => e.act === "close");
    const pre = personLogs(t).length ? el("p", { class: "muted", text: "In the trial, persons then wrote too; their entries are shown in green above. In your turn you write in their place, and can bring them in at the report." }) : null;
    box.replaceChildren(
      el("h3", { text: "Here the agents stopped" }),
      el("p", { text: "The runs went as far as the card lets an agent go. What is left is for a person." }),
      el("ul", {}, items),
      closes.length ? el("details", {}, el("summary", { text: "What each run said when it closed" }),
        closes.map(c => el("p", {}, el("b", { text: c.log + ": " }), c.body))) : null,
      pre,
      el("p", {}, el("button", { class: "primary", "data-go": "turn", text: "Take your turn" })));
  }

  // -------------------------------------------------------------- your turn
  $("#me-key").addEventListener("click", async () => {
    const name = $("#me-name").value.trim();
    if (!name || name.includes(":")) { $("#me-status").textContent = "A name, without a colon."; return; }
    if (TRIALS.some(t => name in t.logs || name in t.keys)) { $("#me-status").textContent = "That name is taken by an author in the trials."; return; }
    try { S.key = await A.newKey(); }
    catch (x) { $("#me-status").textContent = "This browser cannot make an Ed25519 key (it needs a recent Chrome, Safari or Firefox)."; return; }
    S.me = name; $("#me-name").disabled = true; $("#me-key").disabled = true;
    renderTurn();
  });

  const ACTS = [
    ["reader", "The reading I go by"], ["nescio", "I cannot tell (nescio)"], ["decide", "Decide"],
    ["holder", "Who holds a reading"], ["verdict", "My verdict"], ["settle", "Settle an open pair"],
    ["grant", "Grant a norm"], ["withdraw", "Withdraw"],
  ];
  const ACT_INTRO = {
    reader: "Say which reading of the marked word you go by. The entry is about you: its object is your log, its value the reading.",
    nescio: "Say that you cannot tell which reading you go by. Pick the readings you are in doubt between, two or more. You can decide later.",
    decide: "Answer a nescio by picking one of the readings it was in doubt between.",
    holder: "Say who holds a reading: a court, an author, a school of thought. The agents may name candidates; only a person can say it.",
    verdict: "Give your own verdict on the quote. An agent's verdict is a proposal; yours stands unless withdrawn. You may name the readings in dispute.",
    settle: "Two claims by different authors differ on the same thing. Settle the pair by answering both sides, saying how you see it.",
    grant: "Accept a norm an agent recovered as one you rely on. The run may then check the sentence against it.",
    withdraw: "Take back one of your entries. Whatever rests on it falls, and the report shows the chain.",
  };
  function readings(rec, R) {
    return rec.entries().filter(e => e.act === "precize" && !R.withdrawn.has(A.ref(e)) && !(A.ref(e) in R.fell));
  }
  const readingLabel = e => `${A.ref(e)}: ${short(e.value && e.value.length > 10 ? e.value : e.body, 120)}`;
  function select(name, options, { multiple = false, size } = {}) {
    return el("select", { name, multiple, size }, options.map(([v, label]) => el("option", { value: v, text: label })));
  }
  function nextId(rec, prefix) {
    const own = new Set((rec.logs.get(S.me) || []).map(e => e.id));
    let i = 1; while (own.has(prefix + i)) i++; return prefix + i;
  }

  function renderTurn() {
    caseHead($("#turn-head"));
    $("#me-status").textContent = S.me ? `Your key is made. Entries in “${S.me}” are signed with it.` : "";
    $("#acts").hidden = !S.me;
    if (!S.me) return;
    let rec, R;
    try { rec = buildRecord(); R = A.report(rec); }
    catch (x) { $("#act-form").replaceChildren(el("p", { class: "refusal", text: "The record did not load: " + x.message })); return; }
    const tabs = $("#act-tabs"); tabs.replaceChildren();
    for (const [k, label] of ACTS)
      tabs.append(el("button", { class: S.act === k ? "on" : "", text: label, onclick: () => { S.act = k; $("#refusal").hidden = true; renderTurn(); } }));
    renderForm(rec, R);
    renderMine(rec);
  }

  function renderForm(rec, R) {
    const f = $("#act-form"), act = S.act;
    const rs = readings(rec, R);
    const parts = [el("p", { class: "explain", text: ACT_INTRO[act] })];
    const body = ph => el("label", {}, "In your words", el("textarea", { name: "body", placeholder: ph }));
    const none = msg => { parts.push(el("p", { class: "muted", text: msg })); f.replaceChildren(...parts); };
    const quotes = rec.entries().filter(e => e.act === "quote");
    const nescios = Object.keys(R.nescio).map(r => rec.get(r));
    if (act === "reader") {
      if (!rs.length) return none("No readings in this record.");
      parts.push(el("label", {}, "The reading", select("reading", rs.map(e => [A.ref(e), readingLabel(e)]))),
        body("Why this reading, as you read the sentence."));
    } else if (act === "nescio") {
      if (rs.length < 2) return none("Fewer than two readings in this record.");
      parts.push(el("label", {}, "The readings you are in doubt between (hold ⌘ or Ctrl for more than one)",
        select("readings", rs.map(e => [A.ref(e), readingLabel(e)]), { multiple: true, size: Math.min(8, rs.length) })),
        body("What keeps you from choosing."));
    } else if (act === "decide") {
      if (!nescios.length) return none("No nescio waits for a decision. Write one first, under “I cannot tell”.");
      parts.push(el("label", {}, "The nescio", select("nescio", nescios.map(n => [A.ref(n), `${A.ref(n)}: in doubt between ${rec.readingsOf(n).join(", ")}`]))),
        el("label", {}, "The reading chosen", select("reading", rs.map(e => [A.ref(e), readingLabel(e)]))),
        body("What decided it."));
    } else if (act === "holder") {
      if (!rs.length) return none("No readings in this record.");
      parts.push(el("label", {}, "The reading", select("reading", rs.map(e => [A.ref(e), readingLabel(e)]))),
        el("label", {}, "Who holds it", el("input", { name: "who", placeholder: "e.g. the plurality, or the Riksdag in the bill" })),
        body("Where you find that they hold it."));
    } else if (act === "verdict") {
      if (!quotes.length) return none("No quote in this record.");
      const live = rec.entries().filter(e => !R.withdrawn.has(A.ref(e)) && !KEEP.has(e.act) && e.act !== "withdraw");
      parts.push(el("div", { class: "row" },
          el("label", {}, "The quote", select("quote", quotes.map(q => [A.ref(q), `${A.ref(q)}: ${short(q.body, 70)}`]))),
          el("label", {}, "Verdict", select("value", VERDICTS))),
        el("label", {}, "Rests on (the entries your verdict relies on)",
          select("rests", live.map(e => [A.ref(e), `${A.ref(e)} ${e.act}: ${short(e.value || e.body, 80)}`]), { multiple: true, size: 8 })),
        el("label", {}, "Readings in dispute (optional; two or more)",
          select("between", rs.map(e => [A.ref(e), readingLabel(e)]), { multiple: true, size: Math.min(6, rs.length) })),
        body("Your verdict, on what has been said so far."));
    } else if (act === "settle") {
      if (!R.open.length) return none("No pair is open in this record.");
      parts.push(el("label", {}, "The open pair", select("pair", R.open.map(([a, b, why], i) => [String(i), `${a} / ${b}: ${short(why, 90)}`]))),
        body("How you settle it, and why."));
    } else if (act === "grant") {
      const recs = rec.entries().filter(e => e.act === "recover" && !R.withdrawn.has(A.ref(e)));
      if (!recs.length) return none("No norm was recovered in this record, so there is nothing to grant. (A grant with nothing under it is refused.)");
      parts.push(el("label", {}, "The norm", select("recover", recs.map(e => [A.ref(e), `${A.ref(e)}: ${short(e.body, 120)}`]))),
        body("That you rely on this norm when you say the sentence."));
    } else if (act === "withdraw") {
      const own = (rec.logs.get(S.me) || []).filter(e => e.act !== "withdraw" && !R.withdrawn.has(A.ref(e)));
      if (!own.length) return none("You have no entry to withdraw.");
      parts.push(el("label", {}, "Your entry", select("target", own.map(e => [A.ref(e), `${A.ref(e)} ${e.act}: ${short(e.value || e.body, 80)}`]))),
        el("label", {}, "Reason", el("input", { name: "reason", placeholder: "why you take it back" })));
    }
    parts.push(el("p", {}, el("button", { class: "primary", type: "submit", text: "Sign and add to my log" })));
    f.replaceChildren(...parts);
  }
  const KEEP = new Set(["close", "ask", "show"]);

  $("#act-form").addEventListener("submit", async ev => {
    ev.preventDefault();
    const f = ev.target, get = n => f.elements[n] && f.elements[n].value, many = n => f.elements[n] ? [...f.elements[n].selectedOptions].map(o => o.value) : [];
    const rec = buildRecord(), R = A.report(rec), me = S.me;
    const body = (get("body") || "").trim();
    let d;
    switch (S.act) {
      case "reader": d = { id: nextId(rec, "h"), act: "holder", object: me, value: get("reading"), rests: [get("reading")],
        body: body || `${me} goes by ${get("reading")}.` }; break;
      case "nescio": d = { id: nextId(rec, "n"), act: "holder", object: me, value: A.NESCIO, rests: many("readings"),
        body: body || `${me} cannot tell which reading they go by.` }; break;
      case "decide": d = { id: nextId(rec, "d"), act: "decide", object: rec.get(get("nescio")).object, value: get("reading"),
        answers: [{ ref: get("nescio") }], rests: [get("reading")], body: body || `${me} decides for ${get("reading")}.` }; break;
      case "holder": d = { id: nextId(rec, "h"), act: "holder", object: get("reading"), value: (get("who") || "").trim() || null,
        rests: [get("reading")], body: body || `${get("reading")} is held by ${get("who")}.` }; break;
      case "verdict": {
        const v = get("value"), between = many("between");
        d = { id: nextId(rec, "vd"), act: "verdict", object: get("quote"), value: v, rests: many("rests"), between,
          body: body || `${me}: verdict ${v}, on what has been said so far.` }; break;
      }
      case "settle": { const [a, b] = R.open[Number(get("pair"))];
        d = { id: nextId(rec, "s"), act: "settle", answers: [{ ref: a }, { ref: b }], body: body || `${me} settles ${a} / ${b}.` }; break; }
      case "grant": d = { id: nextId(rec, "a"), act: "grant", rests: [get("recover")], body: body || `${me} grants ${get("recover")}.` }; break;
      case "withdraw": d = { id: nextId(rec, "w"), act: "withdraw", withdraws: get("target"), reason: (get("reason") || "").trim() || null,
        body: body || `${me} withdraws ${get("target")}.` }; break;
    }
    d.author = me;
    const box = $("#refusal");
    try {
      const e = await A.append(rec, me, d, S.key);
      (S.mine[S.trial.name] = S.mine[S.trial.name] || []).push(A.toJson(e));
      box.hidden = true;
      renderTurn();
      flash(A.ref(e));
    } catch (x) {
      if (!(x instanceof A.Refused)) throw x;
      box.hidden = false;
      box.replaceChildren(el("b", { text: "The record refuses this entry." }),
        el("div", { text: RULES[x.rule] || "" }), el("div", { class: "muted", text: `Rule “${x.rule}”: ${x.message.replace(/^[^:]+: /, "")}` }));
    }
  });

  function renderMine(rec) {
    const box = $("#mine"), mine = (rec.logs.get(S.me) || []);
    box.replaceChildren(...(mine.length ? mine.map(e => entryCard(e, { known: r => rec.byRef.has(r), long: true }))
      : [el("p", { class: "muted", text: "None yet." })]));
  }

  // -------------------------------------------------------------- report
  $("#with-persons").addEventListener("change", ev => { S.withPersons = ev.target.checked; renderReport(); });

  function renderReport() {
    caseHead($("#report-head"));
    const t = S.trial, out = $("#report-body");
    $("#with-persons").parentElement.hidden = !personLogs(t).filter(l => !neededPersons(t).has(l)).length;
    $("#dl-log").disabled = $("#dl-keys").disabled = !(S.me && (S.mine[t.name] || []).length);
    let rec, R;
    try { rec = buildRecord(); R = A.report(rec); }
    catch (x) { out.replaceChildren(el("p", { class: "refusal", text: "The record did not load: " + x.message })); return; }
    const by = r => rec.get(r);
    const desc = r => { const e = by(r); return e ? `${e.act}${e.value != null ? " " + short(String(e.value), 60) : ""}` : "not in this record"; };
    const refLi = r => el("li", {}, el("code", { text: r }), " ", el("span", { class: "muted", text: desc(r) }));
    const sec = (title, explain, ...kids) => el("section", {}, el("h3", { html: title }), explain && el("p", { class: "explain", text: explain }), ...kids);
    const parts = [];
    const logs = [...rec.logs.keys()];
    parts.push(el("section", {}, el("h3", { text: "This record" }),
      el("p", { class: "explain", text: "Logs: " + logs.map(l => `${l} (${(rec.logs.get(l) || []).length})`).join(", ") + "." }),
      el("div", { class: "stats" },
        el("div", {}, el("b", { text: rec.entries().length }), "entries"),
        el("div", {}, el("b", { text: R.stands.size }), "stand"),
        el("div", {}, el("b", { text: R.open.length }), "open pairs"),
        el("div", {}, el("b", { text: R.proposed.size }), "proposed verdicts"),
        el("div", {}, el("b", { text: R.verdicts_stand.size }), "verdicts by a person"),
        el("div", {}, el("b", { text: R.withdrawn.size + Object.keys(R.fell).length }), "withdrawn or fell"))));

    const between = new Set(R.open_between_agents.map(x => x.join("\u0000")));
    parts.push(sec("Open", "Two claims by different authors on the same thing with different values, or one answering the other in dispute. Open until a person settles them.",
      R.open.length ? el("ul", {}, R.open.map(([a, b, why]) => el("li", {}, el("code", { text: a }), " / ", el("code", { text: b }), ": " + why,
        between.has([a, b, why].join("\u0000")) ? el("span", { class: "warn", text: " (between agents only: no person has taken it up)" }) : null)))
        : el("p", { class: "ok", text: "Nothing is open." })));

    const vrow = r => { const e = by(r); return el("tr", {}, el("td", {}, el("code", { text: r })), el("td", {}, el("b", { text: e.value })), el("td", { text: short(e.body, 160) })); };
    parts.push(sec("Verdicts", "An agent's verdict is a proposal. A person's verdict stands unless it is withdrawn or what it rests on falls.",
      el("h4", { text: "Proposed by agents" }),
      R.proposed.size ? el("table", {}, [...R.proposed].sort().map(vrow)) : el("p", { class: "muted", text: "None." }),
      el("h4", { text: "Given by a person" }),
      R.verdicts_stand.size ? el("table", {}, [...R.verdicts_stand].sort().map(vrow)) : el("p", { class: "muted", text: "None yet." })));

    const held = rec.entries().filter(e => e.act === "holder" && R.stands.has(A.ref(e)));
    const decided = Object.entries(R.decided), nescio = Object.entries(R.nescio);
    parts.push(sec("Who holds what", "Holder entries that stand, nescio still waiting, and what was decided.",
      held.length ? el("ul", {}, held.map(e => el("li", {}, el("code", { text: A.ref(e) }), " ",
        A.isNescio(e) ? `${e.author}: nescio` : rec.byRef.has(e.object) ? `${e.object} is held by ${e.value}` : `${e.object} goes by ${e.value}`))) : el("p", { class: "muted", text: "No holder entry stands." }),
      nescio.length ? el("p", {}, "Nescio, not yet decided: ", nescio.map(([r, rs], i) => [i ? "; " : "", el("code", { text: r }), ` between ${rs.join(", ")}`])) : null,
      decided.length ? el("p", {}, "Decided: ", decided.map(([r, v], i) => [i ? "; " : "", el("code", { text: r }), ` for ${v}`])) : null));

    const fell = Object.entries(R.fell);
    if (R.withdrawn.size || fell.length)
      parts.push(sec("Withdrawn, and what fell", "An entry falls when something it rests on is withdrawn. The chain runs to the withdrawn entry.",
        el("ul", {}, [...R.withdrawn].sort().map(r => el("li", {}, el("code", { text: r }), " withdrawn")),
          fell.map(([r, c]) => el("li", {}, el("code", { text: r }), " fell: rests on " + c.join(" → "))))));

    const flags = [];
    for (const [k, [title, explain]] of Object.entries(FLAGS)) {
      const v = R[k];
      const items = v instanceof Set ? [...v].sort().map(refLi)
        : Array.isArray(v) ? v.map(x => el("li", { text: JSON.stringify(x) }))
        : Object.entries(v).map(([r, x]) => el("li", {}, el("code", { text: short(r, 140) }), ": " + (Array.isArray(x) ? x.map(y => Array.isArray(y) ? y.join(" ⊃ ") : y).join(", ") : x)));
      if (items.length) flags.push(el("div", {}, el("h4", { text: title }), explain && el("p", { class: "explain", text: explain }), el("ul", {}, items)));
    }
    if (flags.length) parts.push(sec("Other things the report notes", "", ...flags));

    const sig = el("p", { class: "muted", text: "Checking signatures…" });
    parts.push(sec("Signatures", "Every entry of a log with a registered key must carry that key's signature over its hash.", sig));
    parts.push(el("p", { class: "note", text: "The server's report also lists sources an entry cites that were never fetched, and commitments written after reading. The playground has no fetched texts, so those are not shown." }));
    out.replaceChildren(el("div", { class: "rep" }, parts));
    A.verify(rec).then(bad => {
      const signed = [...rec.signed], unsigned = logs.filter(l => !rec.signed.has(l));
      sig.className = bad.length ? "warn" : "ok";
      sig.textContent = (bad.length ? `Bad signatures: ${bad.join(", ")}.` : `All ${rec.entries().filter(e => rec.signed.has(e.log)).length} signed entries check out.`) +
        (signed.length ? ` Signed logs: ${signed.join(", ")}.` : "") + (unsigned.length ? ` Logs without a key: ${unsigned.join(", ")}.` : "");
    });
  }

  function download(name, text, type) {
    const a = el("a", { href: URL.createObjectURL(new Blob([text], { type })), download: name });
    document.body.append(a); a.click(); a.remove();
  }
  $("#dl-log").addEventListener("click", () => {
    const rows = (S.mine[S.trial.name] || []).map(d => A.pyline(A.entry(d))).join("\n") + "\n";
    download(`${S.me}.jsonl`, rows, "application/x-ndjson");
  });
  $("#dl-keys").addEventListener("click", () => {
    download("keys.json", JSON.stringify({ [S.me]: { kind: "person", key: S.key.pub } }, null, 1) + "\n", "application/json");
  });
  $("#print").addEventListener("click", () => {
    const pa = $("#print-area"); pa.replaceChildren();
    const rec = buildRecord(), mine = rec.logs.get(S.me) || [];
    pa.append(el("h2", { text: "Who saw what: report" }),
      el("p", { class: "muted", text: `${S.trial.about.trial || S.trial.name} · computed ${new Date().toISOString().slice(0, 10)} in the playground` + (S.me ? ` · person: ${S.me}` : "") }),
      $("#report-head").cloneNode(true), $("#report-body").cloneNode(true));
    pa.querySelectorAll("details").forEach(d => d.open = true);
    if (mine.length) pa.append(el("h3", { text: "Your entries" }), mine.map(e => entryCard(e, { long: true })),
      S.key && el("p", { class: "muted", text: `Signed with Ed25519 key ${S.key.pub}.` }));
    window.print();
  });

  /* A run file downloaded from the live page, loaded again as a case. */
  $("#load-run").addEventListener("change", async ev => {
    const f = ev.target.files[0]; ev.target.value = "";
    if (!f) return;
    let t;
    try { t = JSON.parse(await f.text()); A.Record.load(t.logs, t.keys); }
    catch (x) { $("#load-status").textContent = "That file is not a run from the live page: " + x.message; return; }
    t.name = t.name || f.name; t.about = t.about || { trial: f.name, sentence: "" };
    const i = TRIALS.findIndex(x => x.name === t.name); if (i >= 0) TRIALS.splice(i, 1);
    TRIALS.unshift(t); $("#load-status").textContent = "";
    renderCases(); pick(t);
  });

  renderCases(); updateNav();
  if (LIVE && location.hash === "#live") pick(LIVE);
})();
