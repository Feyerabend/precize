/* The fetch ledger and its checks: audit/fetch.py in JavaScript, for the live page.

   The page keeps what the agent run fetched through its `read` tool. Three checks follow
   from it, as in the server:
   - verbatim: an agent entry whose sources were all fetched must give every passage it
     puts in quotation marks word for word from the fetched text (as fetched, or with
     LaTeX markup taken out). Otherwise it is refused.
   - commit-first: an agent look that answers its own commit must not cite a passage the
     run fetched before writing the commit. Otherwise it is refused.
   - unfetched: an agent entry citing a source the run did not fetch is not refused, but
     reported.
   A ledger row is {source, path, a, b, at, text}; `at` is the number of entries in the
   run's log when the fetch was made. */
(function (root) {
  "use strict";
  const SOURCE = /^([^,§]+?)(?:\s*§[^,]*)?,\s*lines?\s+(\d+)(?:\s*[-–]\s*(\d+))?\s*$/;
  const CARD = "card.txt";   // the card, read as instructions and not as evidence

  function parse(source) {
    const m = SOURCE.exec(source.trim());
    if (!m) return null;
    const a = parseInt(m[2], 10);
    return [m[1].trim(), a, m[3] ? parseInt(m[3], 10) : a];
  }

  function covering(fs, source) {
    const p = parse(source);
    if (!p) return [];
    const [path, a, b] = p;
    const one = fs.filter(f => f.path === path && f.a <= a && b <= f.b);
    if (one.length) return one;
    // lines read in two or more fetches that join (1-400, then 401-748) are read too
    const parts = fs.filter(f => f.path === path && f.a <= b && a <= f.b).sort((x, y) => x.a - y.a);
    let upto = a - 1; const used = [];
    for (const f of parts) {
      if (f.a > upto + 1) break;
      if (f.b > upto) { used.push(f); upto = f.b; }
      if (upto >= b) return used;
    }
    return [];
  }

  const CMD_ARG = /\\[A-Za-z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}/g;
  /* LaTeX source with the markup taken out, as fetch.plain. */
  function plain(s) {
    s = s.replace(/(?<!\\)%.*/g, "");
    s = s.replace(/\\(?:ref|pageref|eqref|label|cite|index)\*?\{[^{}]*\}/g, "");
    s = s.split("\\\\").join(" ").split("\\,").join(" ").split("~").join(" ");
    let prev = null;
    while (prev !== s) { prev = s; s = s.replace(CMD_ARG, "$1"); }
    s = s.replace(/\\[A-Za-z]+\*?/g, "");
    return s.replace(/[{}]/g, "");
  }
  const norm = s => s.split("``").join('"').split("''").join('"').split(/\s+/).filter(Boolean).join(" ");

  /* The first quoted passage in body that is in none of texts, or null (fetch.unquoted). */
  function unquoted(body, texts) {
    const found = s => texts.some(t => t.includes(s));
    for (const m of body.matchAll(/“([^”]+)”/g)) if (!found(norm(m[1]))) return norm(m[1]);
    const marks = [];
    for (let k = 0; k < body.length; k++) if (body[k] === '"') marks.push(k);
    let i = 0;
    while (i + 1 < marks.length) {
      let hit = false;
      const start = (marks.length - 1 - i) % 2 ? marks.length - 1 : marks.length - 2;
      for (let j = start; j > i; j -= 2) {
        if (found(norm(body.slice(marks[i] + 1, marks[j])))) { i = j + 1; hit = true; break; }
      }
      if (!hit) {
        const seg = norm(body.slice(marks[i] + 1, marks[i + 1]));
        if (seg && !found(seg)) return seg;
        i += 2;
      }
    }
    return null;
  }

  /* Run at write time on the entry as added (refs qualified), before it is signed.
     fs: the run's ledger; own: the refs of the run's log before this entry. */
  function check(A, rec, e, fs, Refused) {
    if (e.kind !== "agent" || !e.sources.length) return;
    const covered = new Map(e.sources.map(s => [s, covering(fs, s)]));
    if ([...covered.values()].every(c => c.length)) {
      const raw = [...covered.values()].flat().map(f => f.text).join(" ");
      const seg = unquoted(e.body, [norm(raw), norm(plain(raw))]);
      if (seg !== null) throw new Refused("verbatim", `${A.ref(e)} quotes ${JSON.stringify(seg)}, not in the fetched text`);
    }
    if (e.act === "look") {
      const own = (rec.logs.get(e.log) || []).map(A.ref).filter(r => r !== A.ref(e));
      for (const ans of e.answers) {
        if (own.includes(ans.ref) && rec.get(ans.ref).act === "commit") {
          const i = own.indexOf(ans.ref);
          for (const [s, c] of covered)
            if (c.length && Math.min(...c.map(f => f.at)) <= i)
              throw new Refused("commit-first", `${A.ref(e)} cites ${s}, fetched before commit ${ans.ref}`);
        }
      }
    }
  }

  /* Agent commits written after their author fetched more than the quoted lines. */
  function readFirst(rec, ledgers) {
    const out = {};
    for (const [log, es] of rec.logs) {
      const fs = ledgers[log] || [];
      es.forEach((e, i) => {
        if (e.act !== "commit" || e.kind !== "agent") return;
        const quoted = es.slice(0, i).filter(q => q.act === "quote").flatMap(q => q.sources.map(parse));
        const read = fs.filter(f => f.at <= i && f.path !== CARD && !quoted.some(q =>
          q && q[0] === f.path && q[1] <= f.a && f.b <= q[2])).map(f => f.source);
        if (read.length) out[A_ref(e)] = [...new Set(read)].sort();
      });
    }
    return out;
  }
  const A_ref = e => e.log + ":" + e.id;

  function unfetched(rec, ledgers) {
    const out = {};
    for (const e of rec.entries()) {
      if (e.kind === "agent" && e.sources.length) {
        const fs = ledgers[e.log] || [];
        const miss = e.sources.filter(s => !covering(fs, s).length && !rec.namesEntry(e.log, s));
        if (miss.length) out[A_ref(e)] = miss;
      }
    }
    return out;
  }

  const api = { parse, covering, plain, norm, unquoted, check, readFirst, unfetched, CARD };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Ledger = api;
})(typeof window !== "undefined" ? window : globalThis);
