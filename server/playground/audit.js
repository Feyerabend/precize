/* The record and its reports, ported from audit/record.py and audit/reports.py so the
   playground can run in a browser with no server. Same entries, same hashes, same
   signatures: a log written here loads in the Python server, and the other way round.
   check.mjs compares this report with the Python one on every audit in data/.

   What is not ported: the fetch ledger (unfetched sources, commits written after
   reading), since the playground has no fetched texts; and look and quote, which need a
   source the page cannot fetch. */
(function (root) {
  "use strict";

  // ---------------------------------------------------------------- sha-256 (sync)
  const K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]);

  function sha256hex(str) {
    const msg = new TextEncoder().encode(str);
    const l = msg.length, n = ((l + 9 + 63) >> 6) << 6;
    const b = new Uint8Array(n);
    b.set(msg); b[l] = 0x80;
    const dv = new DataView(b.buffer);
    dv.setUint32(n - 8, Math.floor(l / 0x20000000)); dv.setUint32(n - 4, (l << 3) >>> 0);
    const H = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                               0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
    const W = new Uint32Array(64);
    const rot = (x, k) => (x >>> k) | (x << (32 - k));
    for (let o = 0; o < n; o += 64) {
      for (let i = 0; i < 16; i++) W[i] = dv.getUint32(o + 4 * i);
      for (let i = 16; i < 64; i++) {
        const s0 = rot(W[i - 15], 7) ^ rot(W[i - 15], 18) ^ (W[i - 15] >>> 3);
        const s1 = rot(W[i - 2], 17) ^ rot(W[i - 2], 19) ^ (W[i - 2] >>> 10);
        W[i] = (W[i - 16] + s0 + W[i - 7] + s1) >>> 0;
      }
      let [a, bb, c, d, e, f, g, h] = H;
      for (let i = 0; i < 64; i++) {
        const t1 = (h + (rot(e, 6) ^ rot(e, 11) ^ rot(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + W[i]) >>> 0;
        const t2 = ((rot(a, 2) ^ rot(a, 13) ^ rot(a, 22)) + ((a & bb) ^ (a & c) ^ (bb & c))) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = bb; bb = a; a = (t1 + t2) >>> 0;
      }
      H[0] += a; H[1] += bb; H[2] += c; H[3] += d; H[4] += e; H[5] += f; H[6] += g; H[7] += h;
    }
    return Array.from(H, x => x.toString(16).padStart(8, "0")).join("");
  }

  // json.dumps(d, sort_keys=True, ensure_ascii=False), as Python writes it
  // json.dumps(v, ensure_ascii=False), with sort_keys when `sort`, as Python writes it
  function pyjson(v, sort = true) {
    if (v === null || v === undefined) return "null";
    if (v === true) return "true";
    if (v === false) return "false";
    if (typeof v === "number") return String(v);
    if (typeof v === "string") return JSON.stringify(v);
    if (Array.isArray(v)) return "[" + v.map(x => pyjson(x, sort)).join(", ") + "]";
    const ks = sort ? Object.keys(v).sort() : Object.keys(v);
    return "{" + ks.map(k => JSON.stringify(k) + ": " + pyjson(v[k], sort)).join(", ") + "}";
  }

  // ---------------------------------------------------------------- entries
  const ACTS = new Set(["quote", "mark", "vary", "precize", "holder", "grid", "property", "recover",
    "grant", "check", "commit", "look", "verdict", "withdraw", "settle", "decide", "close", "ask", "show"]);
  const PERSON_ONLY = new Set(["holder", "grant", "settle", "decide"]);
  const NEEDS_SOURCE = new Set(["quote", "look"]);
  const NEEDS_VALUE = new Set(["verdict", "vary", "holder", "decide"]);
  const VARY_OUTCOMES = new Set(["true under all", "false under all", "varies"]);
  const CONSTITUTIVE = "none (constitutive)";
  const NESCIO = "nescio";
  const FIELDS = ["id", "act", "body", "author", "kind", "value", "object", "absent", "sources",
    "rests", "answers", "about", "narrows", "withdraws", "reason", "procedure", "via", "between",
    "log", "prev", "rest_hashes", "hash", "sig"];

  class Refused extends Error {
    constructor(rule, msg) { super(rule + ": " + msg); this.rule = rule; }
  }

  function entry(d) {
    const e = {
      id: "", act: "", body: "", author: null, kind: "person", value: null, object: null,
      absent: null, sources: [], rests: [], answers: [], about: null, narrows: null,
      withdraws: null, reason: null, procedure: null, via: null, between: [], log: "",
      prev: null, rest_hashes: [], hash: "", sig: null };
    for (const k of Object.keys(d)) e[k] = d[k];
    e.answers = (e.answers || []).map(a => ({ ref: a.ref, disputes: !!a.disputes,
      meets: a.meets === undefined ? null : a.meets, hash: a.hash === undefined ? null : a.hash }));
    e.sources = e.sources || []; e.rests = e.rests || []; e.between = e.between || [];
    return e;
  }
  const ref = e => e.log + ":" + e.id;
  function cites(e) {
    const out = [...e.rests, ...e.answers.map(a => a.ref), ...e.between];
    for (const r of [e.about, e.narrows, e.withdraws]) if (r) out.push(r);
    return out;
  }
  function toJson(e) {
    const o = {};
    for (const k of FIELDS) o[k] = k === "answers"
      ? e.answers.map(a => ({ ref: a.ref, disputes: a.disputes, meets: a.meets, hash: a.hash })) : e[k];
    return o;
  }
  /* One line of a log file, as store.append writes it: fields in the dataclass's order. */
  const pyline = e => pyjson(toJson(e), false);
  function digest(e) {
    const d = toJson(e);
    delete d.hash; delete d.sig;
    if (d.via === null || d.via === undefined) delete d.via;
    if (!d.between || !d.between.length) delete d.between;
    return sha256hex(pyjson(d));
  }
  const isNescio = e => e.act === "holder" && (e.value || "").trim().toLowerCase() === NESCIO;
  const partition = (s, sep) => { const i = s.indexOf(sep);
    return i < 0 ? [s, "", ""] : [s.slice(0, i), sep, s.slice(i + sep.length)]; };
  const sorted = xs => [...xs].sort();

  class Record {
    constructor(checks = true) {
      this.checks = checks; this.logs = new Map(); this.byRef = new Map(); this.byHash = new Map();
      this.signed = new Set(); this.keys = {}; this._past = new Map();
    }
    entries() { const out = []; for (const es of this.logs.values()) out.push(...es); return out; }
    get(r) { return this.byRef.get(r); }
    _put(e) {
      if (!this.logs.has(e.log)) this.logs.set(e.log, []);
      this.logs.get(e.log).push(e); this.byRef.set(ref(e), e); this.byHash.set(e.hash, e);
      this._past = new Map();
    }
    static qualify(log, r) { return r.includes(":") ? r : log + ":" + r; }
    _object(log, obj) {
      if (!obj) return obj;
      const [head, sep, rest] = partition(obj, "|");
      const q = Record.qualify(log, head.trim());
      return this.byRef.has(q) ? q + sep + rest.trim() : obj;
    }
    namesEntry(log, s) { return this.byRef.has(s) || this.byRef.has(Record.qualify(log, s)); }

    add(log, e, after = null) {
      e = entry(e);
      const Q = r => Record.qualify(log, r);
      e.log = log; e.author = e.author || log;
      e.rests = e.rests.map(Q);
      for (const a of e.answers) a.ref = Q(a.ref);
      e.about = e.about && Q(e.about); e.narrows = e.narrows && Q(e.narrows);
      e.withdraws = e.withdraws && Q(e.withdraws);
      e.between = e.between.map(Q);
      e.object = this._object(log, e.object);
      if (this.byRef.has(ref(e))) throw new Refused("unique", `${ref(e)} already exists`);
      if (this.checks) this._check(log, e);
      const own = this.logs.get(log) || [];
      e.prev = after ? this.byRef.get(Q(after)).hash : (own.length ? own[own.length - 1].hash : null);
      e.rest_hashes = e.rests.map(r => this.byRef.has(r) ? this.byRef.get(r).hash : "");
      for (const a of e.answers) a.hash = this.byRef.has(a.ref) ? this.byRef.get(a.ref).hash : null;
      e.hash = digest(e);
      this._put(e);
      return e;
    }

    _check(log, e) {
      const R = (rule, msg) => { throw new Refused(rule, msg); };
      const by = this.byRef, eref = ref(e);
      if (!ACTS.has(e.act)) R("act", `unknown act ${e.act}`);
      const own = this.logs.get(log) || [];
      if (own.length && own[own.length - 1].act === "close") R("close", `log ${log} is closed`);
      const named = e.sources.filter(x => this.namesEntry(log, x));
      if (named.length) R("sources", `${eref}: sources cite texts, and ${named[0]} is an entry; name entries in rests (finding 107)`);
      for (const r of cites(e)) if (!by.has(r)) R("cite", `${eref} cites ${r}, which is not on the record`);
      if (NEEDS_SOURCE.has(e.act) && !e.sources.length) R("source", `${e.act} ${eref} has no source passage`);
      if (own.length && own[0].kind !== e.kind) R("kind", `log ${log} is a ${own[0].kind}'s, not an ${e.kind}'s`);
      if (PERSON_ONLY.has(e.act) && e.kind !== "person") R("person", `${e.act} needs a person as author`);
      if (NEEDS_VALUE.has(e.act) && (e.value == null || e.object == null)) R("value", `${e.act} ${eref} needs a value and an object`);
      if (e.act === "vary" && !VARY_OUTCOMES.has(e.value)) R("vary", `vary ${eref}: value must be one of ${sorted(VARY_OUTCOMES)}`);
      if (e.act === "mark" && !e.rests.some(r => this._restsOnAct(r, "quote"))) R("quote-first", `mark ${eref} rests on no quote`);
      if (e.act === "check") {
        const grants = e.rests.filter(r => by.get(r).act === "grant");
        if (!grants.length) R("grant-first", `check ${eref} rests on no grant`);
        for (const g of grants) if (this.withdrawnBy(g).length) R("grant-first", `check ${eref} rests on withdrawn ${g}`);
      }
      if (e.act === "grant" && !(e.procedure || e.rests.some(r => by.get(r).act === "recover")))
        R("grant", `grant ${eref} cites no recover and names no procedure`);
      if (e.act === "commit" && !e.about) R("commit", `commit ${eref} is about nothing`);
      if (e.act === "precize" && e.narrows && !["mark", "precize", "look"].includes(by.get(e.narrows).act))
        R("narrows", `${eref} narrows ${e.narrows}, not a mark, precize or look`);
      if (e.act === "vary" && e.narrows && by.get(e.narrows).act !== "mark")
        R("narrows", `${eref} narrows ${e.narrows}: a vary names a mark`);
      if (e.act === "withdraw") {
        if (!e.withdraws) R("withdraw", `${eref} withdraws nothing`);
        if (by.get(e.withdraws).log !== log) R("own-only", `${eref} withdraws ${e.withdraws}, not in log ${log}`);
      }
      if (e.value == null && e.answers.some(a => by.get(a.ref).act === "ask"))
        R("value", `${eref} answers an ask and needs a value: the answer`);
      if (e.between.length) {
        if (e.act !== "verdict") R("between", `${eref}: only a verdict names readings in dispute`);
        if (e.between.length < 2 || e.between.some(r => by.get(r).act !== "precize"))
          R("between", `${eref}: between names two or more precizes`);
        const marks = this.marksBetween(e);
        const head = o => partition(o || "", "|")[0];
        for (const x of own)
          if (x.act === "verdict" && x.between.length && !this.withdrawnBy(ref(x)).length &&
              head(x.object) === head(this._object(log, e.object)) &&
              setEq(this.marksBetween(x), marks) && x.value !== e.value)
            R("between", `${eref}: ${ref(x)} already gives ${x.value} on the same marks; withdraw it first`);
      }
      if (e.act === "settle" && e.answers.length < 2) R("settle", `settle ${eref} must answer both sides`);
      if (isNescio(e)) {
        if (this._reading(e.object)) R("nescio", `${eref}: a nescio's object is the holder, not a reading`);
        if (this.readingsOf(e).length < 2) R("nescio", `${eref} rests on fewer than two readings in doubt`);
      }
      if (e.act === "decide") {
        const ns = e.answers.map(a => by.get(a.ref)).filter(isNescio);
        if (ns.length !== 1) R("decide", `decide ${eref} must answer one nescio`);
        const chosen = Record.qualify(log, e.value);
        if (!this.readingsOf(ns[0]).includes(chosen)) R("decide", `decide ${eref}: ${e.value} is not a reading ${ref(ns[0])} is in doubt about`);
        if (!e.rests.includes(chosen)) R("decide", `decide ${eref} must rest on the reading chosen`);
        if (this._object(log, e.object) !== ns[0].object) R("decide", `decide ${eref}: object must be the nescio's holder, ${ns[0].object}`);
        e.value = chosen;
      }
    }

    markOf(r) {
      const seen = new Set();
      while (this.byRef.has(r) && !seen.has(r)) {
        seen.add(r);
        const x = this.byRef.get(r);
        if (x.act === "mark") return r;
        if (x.act !== "precize" || !x.narrows) return null;
        r = x.narrows;
      }
      return null;
    }
    marksBetween(e) { const s = new Set(); for (const r of e.between) { const m = this.markOf(r); if (m) s.add(m); } return s; }
    _reading(obj) {
      const x = obj && this.byRef.get(partition(obj, "|")[0].trim());
      return !!x && (x.act === "mark" || x.act === "precize");
    }
    readingsOf(n) {
      const out = [];
      for (const r of n.rests) {
        const x = this.byRef.get(r);
        if (!x) continue;
        if (x.act === "precize") out.push(r);
        else if (x.act === "mark") for (const p of this.entries()) if (p.act === "precize" && p.narrows === r) out.push(ref(p));
      }
      return [...new Set(out)];
    }
    _restsOnAct(r0, act) {
      const seen = new Set(), stack = [r0];
      while (stack.length) {
        const r = stack.pop();
        if (seen.has(r) || !this.byRef.has(r)) continue;
        seen.add(r);
        const x = this.byRef.get(r);
        if (x.act === act) return true;
        stack.push(...x.rests);
      }
      return false;
    }
    withdrawnBy(r) { return this.entries().filter(x => x.act === "withdraw" && x.withdraws === r); }
    past(r) {
      if (this._past.has(r)) return this._past.get(r);
      const e = this.byRef.get(r), out = new Set();
      const prev = this.byHash.get(e.prev);
      const direct = (prev ? [ref(prev)] : []).concat(cites(e).filter(c => this.byRef.has(c)));
      for (const d of direct) { out.add(d); for (const x of this.past(d)) out.add(x); }
      this._past.set(r, out);
      return out;
    }
    forks() {
      const out = [];
      for (const [log, es] of this.logs) {
        const succ = new Map();
        for (const e of es) if (e.prev) { if (!succ.has(e.prev)) succ.set(e.prev, []); succ.get(e.prev).push(ref(e)); }
        for (const [h, refs] of succ) if (refs.length > 1)
          out.push([log, this.byHash.has(h) ? ref(this.byHash.get(h)) : h, sorted(refs)]);
      }
      return out;
    }
    tips(log) {
      const es = this.logs.get(log) || [], prevs = new Set(es.map(e => e.prev));
      return es.filter(e => !prevs.has(e.hash)).map(ref);
    }

    /* Load logs as {name: [rows]}, in the order Python reads files: by file name. Hashes
       are checked here; signatures are checked by verify(), which is async. */
    static load(logs, keys = {}) {
      const rec = new Record(false);
      rec.keys = keys;
      const rows = new Map();
      const names = Object.keys(logs).sort((a, b) => cmp(a + ".jsonl", b + ".jsonl"));
      for (const n of names) for (const d of logs[n]) {
        const e = entry(d);
        if (digest(e) !== e.hash) throw new Refused("hash", `${ref(e)} does not match its hash`);
        const k = keys[e.log];
        if (k && e.kind !== k.kind) throw new Refused("sig", `${ref(e)} is not of the kind registered for ${e.log}`);
        if (!rows.has(e.hash)) rows.set(e.hash, e);
      }
      const refs = new Set([...rows.values()].map(ref)), hashes = new Set(rows.keys());
      let pending = [...rows.values()];
      while (pending.length) {
        const nxt = [];
        for (const e of pending) {
          const ready = cites(e).every(c => rec.byRef.has(c) || !refs.has(c)) &&
            (e.prev === null || rec.byHash.has(e.prev) || !hashes.has(e.prev));
          if (!ready) { nxt.push(e); continue; }
          if (rec.byRef.has(ref(e))) throw new Refused("fork", `two different entries named ${ref(e)}`);
          rec._put(e);
        }
        if (nxt.length === pending.length) throw new Refused("chain", `cannot place ${nxt.map(ref)}`);
        pending = nxt;
      }
      rec.signed = new Set([...rec.logs.keys()].filter(l => l in keys));
      return rec;
    }
  }
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  const setEq = (a, b) => a.size === b.size && [...a].every(x => b.has(x));

  // ---------------------------------------------------------------- signatures
  const hexToBytes = h => new Uint8Array(h.match(/../g).map(x => parseInt(x, 16)));
  const bytesToHex = b => Array.from(new Uint8Array(b), x => x.toString(16).padStart(2, "0")).join("");
  const subtle = () => (root.crypto || globalThis.crypto).subtle;

  async function verifySig(pub, h, sig) {
    if (!sig) return false;
    try {
      const k = await subtle().importKey("raw", hexToBytes(pub), { name: "Ed25519" }, false, ["verify"]);
      return await subtle().verify({ name: "Ed25519" }, k, hexToBytes(sig), hexToBytes(h));
    } catch (x) { return false; }
  }
  /* Every entry of a registered log must carry its key's signature (Record.load in
     record.py). Returns the refs that fail. */
  async function verify(rec) {
    const bad = [];
    for (const e of rec.entries()) {
      const k = rec.keys[e.log];
      if (k && !(await verifySig(k.key, e.hash, e.sig))) bad.push(ref(e));
    }
    return bad;
  }
  async function newKey() {
    const kp = await subtle().generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const pub = bytesToHex(await subtle().exportKey("raw", kp.publicKey));
    return { pair: kp, pub };
  }
  async function sign(key, h) {
    return bytesToHex(await subtle().sign({ name: "Ed25519" }, key.pair.privateKey, hexToBytes(h)));
  }
  /* Check, hash, sign and append: store.append, for a person writing in the page. */
  async function append(rec, log, d, key) {
    const reg = rec.keys[log];
    if (!reg || reg.key !== key.pub) throw new Refused("key", `no key registered for ${log} matches the signer`);
    d = Object.assign({}, d, { kind: "person" });
    const checks = rec.checks; rec.checks = true;
    let e;
    try { e = rec.add(log, d); } finally { rec.checks = checks; }
    e.sig = await sign(key, e.hash);
    rec.signed.add(log);
    return e;
  }
  function register(rec, log, kind, pub) {
    if (rec.keys[log]) {
      if (rec.keys[log].kind === kind && rec.keys[log].key === pub) return;
      throw new Refused("key", `log ${log} already has a key; a key change is not built`);
    }
    rec.keys[log] = { kind, key: pub };
  }

  // ---------------------------------------------------------------- reports
  const OPPOSABLE = new Set(["verdict", "vary", "holder", "decide"]);
  const COMPARED = OPPOSABLE;
  const KEEPING = new Set(["close", "ask", "show"]);
  const QUOTED = () => /"([^"]+)"|“([^”]+)”/g;
  const norm = s => s.replace(/``/g, '"').replace(/''/g, '"').split(/\s+/).filter(Boolean).join(" ");
  const rstrip = (s, cs) => { let i = s.length; while (i > 0 && cs.includes(s[i - 1])) i--; return s.slice(0, i); };
  const strip = (s, cs) => { let i = 0; while (i < s.length && cs.includes(s[i])) i++; return rstrip(s.slice(i), cs); };

  function manyHeld(rec, e) {
    if (e.act !== "holder" || !e.object) return false;
    const x = rec.byRef.get(partition(e.object, "|")[0].trim());
    return !!x && (x.act === "mark" || x.act === "precize");
  }
  function documentOf(s) {
    const i = s.search(/\s*(?:,|§|\blines?\b|\bpp?\.)/);
    return (i < 0 ? s : s.slice(0, i)).trim() || s;
  }
  function quotedWords(body) {
    const m = QUOTED().exec(body);
    return m ? rstrip(norm(m[1] || m[2]).toLowerCase(), " .,;:!?") : null;
  }
  function markedWords(e) {
    const w = (e.value && (quotedWords(e.value) || e.value)) || quotedWords(e.body || "") || "";
    return strip(norm(w).toLowerCase(), " \"'“”‘’.,;:");
  }
  const contains = (longer, shorter) => !!shorter && (" " + longer + " ").includes(" " + shorter + " ");
  function quoteWords(body) {
    const ws = [];
    const re = QUOTED(); let m;
    while ((m = re.exec(body || ""))) ws.push(rstrip(norm(m[1] || m[2]).toLowerCase(), " .,;:!?"));
    if (!ws.length) return null;
    return ws.reduce((a, b) => (b.length > a.length ? b : a));
  }
  function canon(rec, obj) {
    let [base, sep, qual] = partition(obj, "|");
    const e = rec.byRef.get(base.trim());
    if (e && e.act === "quote") { const w = quoteWords(e.body); if (w) base = `"${w}"`; }
    return base.trim() + sep + qual.trim();
  }
  function variedMark(rec, e) {
    if (e.act !== "vary" || !e.narrows || !rec.byRef.has(e.narrows)) return null;
    return markedWords(rec.get(e.narrows)) || null;
  }
  function heldMarks(rec, e) {
    if (e.act !== "holder" || manyHeld(rec, e)) return new Set();
    const refs = isNescio(e) ? rec.readingsOf(e) : [partition(e.value || "", "|")[0].trim()];
    const out = new Set();
    for (const r of refs) { const x = rec.byRef.get(r); if (x && x.act === "precize" && x.narrows) out.add(x.narrows); }
    return out;
  }
  function disputedWords(rec, e) { return new Set([...rec.marksBetween(e)].map(m => markedWords(rec.get(m)))); }
  function sameTerm(rec, a, b) {
    const da = disputedWords(rec, a), db = disputedWords(rec, b);
    if (da.size && db.size && !setEq(da, db)) return false;
    const ma = variedMark(rec, a), mb = variedMark(rec, b);
    if (!(ma === null || mb === null || ma === mb)) return false;
    const ha = heldMarks(rec, a), hb = heldMarks(rec, b);
    return !(ha.size && hb.size) || [...ha].some(x => hb.has(x));
  }
  const NONE = /^\s*(none|no verdict|no case)\b/i;
  const FRAME = /\bframe\s*(1a|1b|\d+)/i;
  function sameValue(a, b) {
    const num = v => { const m = /^\s*(\d+)\b/.exec(v || ""); return m ? m[1] : null; };
    if (NONE.test(a || "") && NONE.test(b || "")) {
      const fa = FRAME.exec(a || ""), fb = FRAME.exec(b || "");
      return !(fa && fb) || fa[1] === fb[1];
    }
    if (num(a) && num(b)) return num(a) === num(b);
    return (a || "").trim().toLowerCase() === (b || "").trim().toLowerCase();
  }
  function restsClosure(rec, r0) {
    const out = new Set(), stack = [...rec.get(r0).rests];
    while (stack.length) {
      const r = stack.pop();
      if (out.has(r)) continue;
      out.add(r);
      if (rec.byRef.has(r)) stack.push(...rec.get(r).rests);
    }
    return out;
  }

  function report(rec) {
    const R = {
      withdrawn: new Set(), fell: {}, open: [], on_open: {}, open_between_agents: [],
      pending_commits: new Set(), met_unanswered: new Set(), single_source: new Set(),
      second_hand: {}, stops: {}, constitutive: {}, loose_objects: new Set(), same_object: {},
      awaiting_grant: {}, proposed: new Set(), stands: new Set(), verdicts_stand: new Set(),
      drift: {}, open_asks: new Set(), answers_to_compare: {}, unread_marks: new Set(),
      nescio: {}, decided: {}, marks_differ: {}, marks_nested: {}, grant_withdrawals: {},
      evidence_unread: {}, rests_unread: {}, unsigned_logs: new Set(), unverified: new Set(),
      heads: {}, logs_not_read: new Set(), entries_not_read: new Set(), forks: [],
      entries_as_sources: {} };
    const es = rec.entries();
    const by = rec.byRef;
    const closure = new Map();
    const C = r => { if (!closure.has(r)) closure.set(r, restsClosure(rec, r)); return closure.get(r); };

    for (const e of es) if (e.act === "withdraw" && e.withdraws) R.withdrawn.add(e.withdraws);

    function chain(r0, seen) {
      for (const r of rec.get(r0).rests) {
        if (R.withdrawn.has(r)) return [r];
        if (by.has(r) && !seen.includes(r)) { const c = chain(r, seen.concat([r0])); if (c) return [r].concat(c); }
      }
      return null;
    }
    for (const e of es) {
      if (R.withdrawn.has(ref(e)) || e.act === "withdraw") continue;
      const c = chain(ref(e), []);
      if (c) R.fell[ref(e)] = c;
    }
    const gone = new Set([...R.withdrawn, ...Object.keys(R.fell)]);

    for (const log of rec.logs.keys()) R.heads[log] = rec.tips(log);
    R.forks = rec.forks();
    R.unsigned_logs = new Set([...rec.logs.keys()].filter(l => !rec.signed.has(l)));
    for (const e of es)
      if (R.unsigned_logs.has(e.log) && (["holder", "grant", "settle", "decide"].includes(e.act) ||
          (e.act === "verdict" && e.kind === "person"))) R.unverified.add(ref(e));
    for (const e of es) for (const c of cites(e)) if (!by.has(c)) {
      const log = c.split(":")[0];
      if (rec.logs.has(log)) R.entries_not_read.add(c); else R.logs_not_read.add(log);
    }
    for (const e of es) {
      if (gone.has(ref(e)) || e.act === "withdraw") continue;
      const missing = sorted(new Set([...e.rests, ...C(ref(e))].filter(r => !by.has(r))));
      if (missing.length) R.rests_unread[ref(e)] = missing;
    }

    const live = es.filter(e => !gone.has(ref(e)));
    const pk = (a, b) => [a, b].sort().join("\u0000");
    const settled = new Set();
    for (const e of live) if (e.act === "settle") {
      const refs = e.answers.map(a => a.ref);
      for (const x of refs) for (const y of refs) if (x !== y) settled.add(pk(x, y));
    }
    const onBranches = (a, b) => !rec.past(ref(b)).has(ref(a)) && !rec.past(ref(a)).has(ref(b));
    const accepts = (a, b) => C(ref(a)).has(ref(b)) || C(ref(b)).has(ref(a));
    const pairs = new Map();
    for (let i = 0; i < live.length; i++) {
      const a = live[i];
      for (const b of live.slice(i + 1)) {
        if (accepts(a, b) || (a.author === b.author && !onBranches(a, b))) continue;
        if (OPPOSABLE.has(a.act) && a.act === b.act && a.object && b.object && !manyHeld(rec, a) &&
            canon(rec, a.object) === canon(rec, b.object) && sameTerm(rec, a, b) && !sameValue(a.value, b.value))
          pairs.set(pk(ref(a), ref(b)), [ref(a), ref(b), `${a.object}: ${a.value} / ${b.value}`]);
      }
    }
    for (const b of live) for (const ans of b.answers) {
      const a = by.get(ans.ref);
      if (!a || gone.has(ref(a)) || (a.author === b.author && !onBranches(a, b))) continue;
      if (a.absent && a.absent.in === "world" && b.act === "look")
        pairs.set(pk(ref(a), ref(b)), [ref(a), ref(b), `fills absence: ${a.absent.what}`]);
      else if (ans.disputes) pairs.set(pk(ref(a), ref(b)), [ref(a), ref(b), "disputes"]);
    }
    for (const q of live.filter(e => e.act === "ask")) {
      const ans = live.filter(x => x.author !== q.author && x.answers.some(a => a.ref === ref(q)));
      if (new Set(ans.map(x => x.author)).size < 2) continue;
      if (ans.some(x => x.value == null)) { R.answers_to_compare[ref(q)] = sorted(ans.map(ref)); continue; }
      for (let i = 0; i < ans.length; i++) for (const b of ans.slice(i + 1)) {
        const a = ans[i];
        if (a.author !== b.author && !accepts(a, b) && !sameValue(a.value, b.value) && !pairs.has(pk(ref(a), ref(b))))
          pairs.set(pk(ref(a), ref(b)), [ref(a), ref(b), `answers ${ref(q)}: ${a.value} / ${b.value}`]);
      }
    }
    R.open = [...pairs].filter(([k]) => !settled.has(k)).map(([, v]) => v);
    const taken = new Set();
    for (const e of live) if (e.kind === "person") {
      for (const c of C(ref(e))) taken.add(c);
      for (const a of e.answers) taken.add(a.ref);
    }
    R.open_between_agents = R.open.filter(([a, b]) => by.get(a).kind === "agent" && by.get(b).kind === "agent" &&
      !taken.has(a) && !taken.has(b));
    let byObj = new Map();
    const push = (m, k, v) => { if (!m.has(k)) m.set(k, []); m.get(k).push(v); };
    for (const e of live) if (COMPARED.has(e.act) && e.object) push(byObj, `${e.act} ${canon(rec, e.object)}`, e);
    for (const o of [...byObj.keys()].filter(o => o.startsWith("vary "))) {
      const xs = byObj.get(o); byObj.delete(o);
      const named = new Set(xs.map(x => variedMark(rec, x)).filter(m => m !== null));
      if (!named.size) byObj.set(o, xs);
      for (const m of named) byObj.set(`${o} / "${m}"`, xs.filter(x => [m, null].includes(variedMark(rec, x))));
    }
    for (const [o, xs] of byObj) if (new Set(xs.map(x => x.author)).size > 1) R.same_object[o] = sorted(xs.map(ref));
    const sides = new Set(R.open.flatMap(([a, b]) => [a, b]));
    for (const e of live) {
      const hit = sorted([...C(ref(e)), ref(e)].filter(x => sides.has(x)));
      const uniq = [...new Set(hit)];
      if (uniq.length) R.on_open[ref(e)] = uniq;
    }

    for (const e of live) {
      if (e.act === "commit") {
        const meeting = live.filter(x => x.answers.some(a => a.ref === ref(e) && a.meets));
        if (!meeting.length) R.pending_commits.add(ref(e));
        else if (!meeting.some(m => live.some(y => y.author === e.author &&
                 (y.rests.includes(ref(m)) || y.answers.some(a => a.ref === ref(m))))))
          R.met_unanswered.add(ref(e));
      }
      if (e.act === "look") {
        if (new Set(e.sources.map(documentOf)).size === 1) R.single_source.add(ref(e));
        if (e.via) R.second_hand[ref(e)] = e.via;
      }
      if (e.act === "vary" && e.value === "true under all") R.stops[ref(e)] = "vagueness is idle: stop, look elsewhere";
      if (e.act === "vary" && e.value === "false under all") R.stops[ref(e)] = "false on every reading: stop, report it in that form";
      if (e.act === "property" && e.value === CONSTITUTIVE)
        R.constitutive[ref(e)] = sorted(live.filter(x => C(ref(x)).has(ref(e))).map(ref));
      if (COMPARED.has(e.act) && e.object && !by.has(partition(e.object, "|")[0]) &&
          !(isNescio(e) || e.act === "decide" || (e.act === "holder" && rec._reading(e.value))))
        R.loose_objects.add(ref(e));
      if (e.act === "recover") {
        const granted = live.some(x => x.act === "grant" && x.rests.includes(ref(e)));
        if (!granted) R.awaiting_grant[ref(e)] = sorted(live.filter(x => C(ref(x)).has(ref(e))).map(ref));
      }
    }

    for (const e of live) {
      if (e.act === "withdraw" || KEEPING.has(e.act) || ref(e) in R.rests_unread) continue;
      R.stands.add(ref(e));
      if (e.act === "verdict") (e.kind === "agent" ? R.proposed : R.verdicts_stand).add(ref(e));
    }

    byObj = new Map();
    for (const e of live) if (e.act === "mark")
      for (const r of e.rests) if (by.has(r) && rec.get(r).act === "quote") push(byObj, canon(rec, r), e);
    for (const [obj, ms] of byObj) {
      const words = new Map(ms.map(m => [ref(m), markedWords(m)]));
      const own = new Map();
      for (const m of ms) { if (!own.has(m.author)) own.set(m.author, new Set()); own.get(m.author).add(words.get(ref(m))); }
      const term = new Map();
      for (const m of ms) {
        const inside = ms.filter(n => n.author !== m.author && !own.get(m.author).has(words.get(ref(n))) &&
          contains(words.get(ref(m)), words.get(ref(n))));
        let t = words.get(ref(m));
        if (inside.length) t = inside.map(n => words.get(ref(n))).reduce((a, b) => (b.length < a.length ? b : a));
        term.set(ref(m), t);
        for (const n of inside) (R.marks_nested[obj] = R.marks_nested[obj] || []).push([ref(m), ref(n)]);
      }
      const sets = new Map();
      for (const m of ms) { if (!sets.has(m.author)) sets.set(m.author, new Set()); sets.get(m.author).add(term.get(ref(m))); }
      const distinct = new Set([...sets.values()].map(s => sorted(s).join("\u0000")));
      if (sets.size > 1 && distinct.size > 1) R.marks_differ[obj] = sorted(ms.map(ref));
      if (R.marks_nested[obj]) R.marks_nested[obj].sort((x, y) => cmp(x[0], y[0]) || cmp(x[1], y[1]));
    }

    for (const e of live)
      if (e.act === "mark" && !live.some(x => x.act === "precize" &&
          (x.narrows === ref(e) || (!x.narrows && x.rests.includes(ref(e)))))) R.unread_marks.add(ref(e));
    for (const e of live) if (e.act === "decide") R.decided[ref(e)] = e.value;
    for (const e of live)
      if (isNescio(e) && !live.some(x => x.act === "decide" && x.answers.some(a => a.ref === ref(e))))
        R.nescio[ref(e)] = rec.readingsOf(e);
    for (const e of live)
      if (e.act === "ask" && !live.some(x => x.author !== e.author && x.answers.some(a => a.ref === ref(e))))
        R.open_asks.add(ref(e));

    for (const e of live) {
      if (e.act === "precize" && e.narrows && by.has(e.narrows) && rec.get(e.narrows).act !== "mark") {
        const pn = rec.past(e.narrows);
        const after = [...rec.past(ref(e))].filter(r => !pn.has(r) && r !== e.narrows);
        const nAct = rec.get(e.narrows).act;
        const looks = sorted(after.filter(r => rec.get(r).act === "look" &&
          (nAct !== "look" || cites(rec.get(r)).includes(e.narrows))));
        if (looks.length) R.drift[ref(e)] = looks;
      }
    }
    for (const e of es) {
      if (e.act === "withdraw" && e.withdraws && rec.get(e.withdraws).act === "grant") {
        const checks = es.filter(x => x.act === "check" && x.rests.includes(e.withdraws)).map(ref);
        const under = checks.filter(c => rec.past(ref(e)).has(c));
        R.grant_withdrawals[ref(e)] = under.length ? "under the check" : "on evidence";
        const unread = e.answers.map(a => a.ref).filter(r => !by.has(r));
        if (unread.length) R.evidence_unread[ref(e)] = unread;
      }
    }
    for (const e of es) {
      const named = e.sources.filter(x => rec.namesEntry(e.log, x));
      if (named.length) R.entries_as_sources[ref(e)] = named;
    }
    return R;
  }

  /* The report as plain JSON, sets sorted: what check.mjs compares with Python. */
  function plain(R) {
    const o = {};
    for (const [k, v] of Object.entries(R)) {
      if (v instanceof Set) o[k] = sorted(v);
      else if (k === "open" || k === "open_between_agents" || k === "forks")
        o[k] = v.map(x => JSON.stringify(x)).sort().map(x => JSON.parse(x));
      else o[k] = v;
    }
    return o;
  }

  const api = { Record, Refused, entry, ref, cites, digest, report, plain, verify, newKey, sign,
    append, register, pyline, isNescio, markedWords, sameValue, canon, toJson, sha256hex, pyjson,
    PERSON_ONLY, NESCIO, CONSTITUTIVE };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Audit = api;
})(typeof window !== "undefined" ? window : globalThis);
