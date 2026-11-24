"""Entries, logs and the checks made when an entry is written.

A record is a set of logs, one per author. Each log only adds. Each entry carries the
hash of its author's previous entry, and every cite carries the hash of what it cites.
Nothing here computes a report; that is reports.py.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ACTS = {
    # auditing
    "quote", "mark", "vary", "precize", "holder", "grid", "property", "recover",
    "grant", "check", "commit", "look", "verdict", "withdraw", "settle", "decide",
    # keeping the record
    "close", "ask", "show",
}
PERSON_ONLY = {"holder", "grant", "settle", "decide"}  # an agent's verdict is allowed, as proposed
NEEDS_SOURCE = {"quote", "look"}              # rules 1 and 4
NEEDS_VALUE = {"verdict", "vary", "holder", "decide"}  # value fields, so disagreement can be seen
VARY_OUTCOMES = {"true under all", "false under all", "varies"}  # the card, step 1b
CONSTITUTIVE = "none (constitutive)"  # a property's value when there is no property (step 5)
NESCIO = "nescio"  # a holder's answer "I don't know which reading I meant" (Naess)


def is_nescio(e) -> bool:
    return e.act == "holder" and (e.value or "").strip().lower() == NESCIO


class Refused(Exception):
    """An entry the record will not accept. `rule` names the rule broken."""

    def __init__(self, rule: str, msg: str):
        super().__init__(f"{rule}: {msg}")
        self.rule = rule


@dataclass
class Answer:
    """A cite that is in the entry's past but does not carry the cascade."""
    ref: str
    disputes: bool = False  # the answering entry says the answered one is wrong
    meets: bool | None = None  # for a look answering a commit: does it meet it?
    hash: str | None = None


@dataclass
class Entry:
    id: str
    act: str
    body: str = ""
    author: str | None = None  # defaults to the log
    kind: str = "person"       # person | agent
    value: str | None = None
    object: str | None = None
    absent: dict | None = None  # {"in": "world", "what": ..., "where": ...}
    sources: list[str] = field(default_factory=list)
    rests: list[str] = field(default_factory=list)   # "LOG:id"; carries the cascade
    answers: list[Answer] = field(default_factory=list)
    about: str | None = None     # commit: the entry it commits about
    narrows: str | None = None   # precize: the entry it narrows; vary: its mark
    withdraws: str | None = None  # withdraw: the entry withdrawn (own log only)
    reason: str | None = None    # withdraw: e.g. "not mine"
    procedure: str | None = None  # grant of a procedure of the record, not a recover
    via: str | None = None       # look: the document its passage quotes (second hand)
    between: list[str] = field(default_factory=list)  # verdict: the readings in dispute
    # filled by the record
    log: str = ""
    prev: str | None = None
    rest_hashes: list[str] = field(default_factory=list)
    hash: str = ""
    sig: str | None = None  # the log key's signature over the hash (stage 4)

    @property
    def ref(self) -> str:
        return f"{self.log}:{self.id}"

    def cites(self) -> list[str]:
        out = list(self.rests) + [a.ref for a in self.answers] + list(self.between)
        for r in (self.about, self.narrows, self.withdraws):
            if r:
                out.append(r)
        return out

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(d: dict) -> "Entry":
        d = dict(d)
        d["answers"] = [Answer(**a) for a in d.get("answers", [])]
        d.setdefault("via", None)
        d.setdefault("sig", None)
        d.setdefault("between", [])
        return Entry(**d)


def _digest(e: Entry) -> str:
    d = e.to_json()
    d.pop("hash")
    d.pop("sig", None)  # a signature is over the hash, not part of it
    if d.get("via") is None:  # added after stage 3; absent keeps older hashes valid
        d.pop("via", None)
    if not d.get("between"):  # added with finding 98; absent keeps older hashes valid
        d.pop("between", None)
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Record:
    """All logs of one audit, as read. `checks=False` replays a history as it happened,
    for histories written before the rules existed; refusals are then not raised."""

    def __init__(self, checks: bool = True):
        self.checks = checks
        self.logs: dict[str, list[Entry]] = {}
        self.by_ref: dict[str, Entry] = {}
        self.by_hash: dict[str, Entry] = {}
        self.signed: set[str] = set()  # logs whose every entry was verified on load
        self.folder: Path | None = None  # set by store.load: where the fetch log is

    # --- writing -------------------------------------------------------------
    def add(self, log: str, e: Entry, after: str | None = None) -> Entry:
        """Append e to log. `after` names the entry to chain to instead of the log's
        last one: that is how a restarted run, or an author showing two versions, forks."""
        e.log = log
        e.author = e.author or log
        e.rests = [self._qualify(log, r) for r in e.rests]
        for a in e.answers:
            a.ref = self._qualify(log, a.ref)
        e.about = e.about and self._qualify(log, e.about)
        e.narrows = e.narrows and self._qualify(log, e.narrows)
        e.withdraws = e.withdraws and self._qualify(log, e.withdraws)
        e.between = [self._qualify(log, r) for r in e.between]
        e.object = self._object(log, e.object)
        if e.ref in self.by_ref:
            raise Refused("unique", f"{e.ref} already exists")
        if self.checks:
            self._check(log, e)
        # chain and cite hashes
        own = self.logs.get(log, [])
        if after:
            e.prev = self.by_ref[self._qualify(log, after)].hash
        else:
            e.prev = own[-1].hash if own else None
        e.rest_hashes = [self.by_ref[r].hash if r in self.by_ref else "" for r in e.rests]
        for a in e.answers:
            a.hash = self.by_ref[a.ref].hash if a.ref in self.by_ref else None
        e.hash = _digest(e)
        self._put(e)
        return e

    def _put(self, e: Entry) -> None:
        self.logs.setdefault(e.log, []).append(e)
        self.by_ref[e.ref] = e
        self.by_hash[e.hash] = e

    def _object(self, log: str, obj: str | None) -> str | None:
        """An object may name an entry, as "ref" or "ref|reading" (e.g. "q1|P2"). Then
        it is qualified, so that two authors naming the same quote match. The second
        trial: two verdicts on T0 written as free text did not match, and hid a dispute."""
        if not obj:
            return obj
        head, sep, rest = obj.partition("|")
        q = self._qualify(log, head.strip())
        return q + sep + rest.strip() if q in self.by_ref else obj

    @staticmethod
    def _qualify(log: str, r: str) -> str:
        return r if ":" in r else f"{log}:{r}"

    def names_entry(self, log: str, source: str) -> bool:
        """Whether a source names an entry of the record, bare or qualified."""
        return source in self.by_ref or self._qualify(log, source) in self.by_ref

    def _check(self, log: str, e: Entry) -> None:
        if e.act not in ACTS:
            raise Refused("act", f"unknown act {e.act!r}")
        own = self.logs.get(log, [])
        if own and own[-1].act == "close":
            raise Refused("close", f"log {log} is closed")
        named = [x for x in e.sources if self.names_entry(log, x)]
        if named:
            raise Refused("sources", f"{log}:{e.id}: sources cite texts, and {named[0]} is "
                          "an entry; name entries in rests (finding 107)")
        for r in e.cites():
            if r not in self.by_ref:
                raise Refused("cite", f"{e.ref} cites {r}, which is not on the record")
        if e.act in NEEDS_SOURCE and not e.sources:
            raise Refused("source", f"{e.act} {e.ref} has no source passage")
        # One log, one kind of author. The second trial: an agent entry went into a
        # person's log, since kind was taken from each entry as given.
        if own and own[0].kind != e.kind:
            raise Refused("kind", f"log {log} is a {own[0].kind}'s, not an {e.kind}'s")
        if e.act in PERSON_ONLY and e.kind != "person":
            raise Refused("person", f"{e.act} needs a person as author")
        if e.act in NEEDS_VALUE and (e.value is None or e.object is None):
            raise Refused("value", f"{e.act} {e.ref} needs a value and an object")
        if e.act == "vary" and e.value not in VARY_OUTCOMES:
            raise Refused("vary", f"vary {e.ref}: value must be one of {sorted(VARY_OUTCOMES)}")
        if e.act == "mark" and not any(self._rests_on_act(r, "quote") for r in e.rests):
            raise Refused("quote-first", f"mark {e.ref} rests on no quote")
        if e.act == "check":
            grants = [r for r in e.rests if self.by_ref[r].act == "grant"]
            if not grants:
                raise Refused("grant-first", f"check {e.ref} rests on no grant")
            for g in grants:
                if self.withdrawn_by(g):
                    raise Refused("grant-first", f"check {e.ref} rests on withdrawn {g}")
        if e.act == "grant" and not (e.procedure or any(
                self.by_ref[r].act == "recover" for r in e.rests)):
            raise Refused("grant", f"grant {e.ref} cites no recover and names no procedure")
        if e.act == "commit" and not e.about:
            raise Refused("commit", f"commit {e.ref} is about nothing")
        # A precize narrows the term marked, an earlier reading, or a claim found (the
        # Elm case of the third test). The live trial: an agent read `narrows` as the mark.
        if e.act == "precize" and e.narrows and self.by_ref[e.narrows].act not in (
                "mark", "precize", "look"):
            raise Refused("narrows", f"{e.ref} narrows {e.narrows}, not a mark, precize or look")
        # A vary may name the mark it varies, when a sentence has several (finding 75).
        if e.act == "vary" and e.narrows and self.by_ref[e.narrows].act != "mark":
            raise Refused("narrows", f"{e.ref} narrows {e.narrows}: a vary names a mark")
        if e.act == "withdraw":
            if not e.withdraws:
                raise Refused("withdraw", f"{e.ref} withdraws nothing")
            if self.by_ref[e.withdraws].log != log:
                raise Refused("own-only", f"{e.ref} withdraws {e.withdraws}, not in log {log}")
        # An answer to an ask carries the answer as a value, so that two can be compared
        # (finding 54: two persons answered one ask oppositely, and nothing showed it).
        if e.value is None and any(self.by_ref[a.ref].act == "ask" for a in e.answers):
            raise Refused("value", f"{e.ref} answers an ask and needs a value: the answer")
        # A sentence may hold more than one disagreement (finding 98: widow against son,
        # and the Court against the concurrence on "children"). A verdict says which by
        # naming the readings it is between; one author gives one value per set of marks.
        if e.between:
            if e.act != "verdict":
                raise Refused("between", f"{e.ref}: only a verdict names readings in dispute")
            if len(e.between) < 2 or any(self.by_ref[r].act != "precize" for r in e.between):
                raise Refused("between", f"{e.ref}: between names two or more precizes")
            marks = self.marks_between(e)
            for x in self.logs.get(log, []):
                if (x.act == "verdict" and x.between and not self.withdrawn_by(x.ref)
                        and (x.object or "").partition("|")[0] ==
                        (self._object(log, e.object) or "").partition("|")[0]
                        and self.marks_between(x) == marks and x.value != e.value):
                    raise Refused("between", f"{e.ref}: {x.ref} already gives {x.value} on "
                                  "the same marks; withdraw it first")
        if e.act == "settle" and len(e.answers) < 2:
            raise Refused("settle", f"settle {e.ref} must answer both sides")
        # Nescio and decide (Naess 1999): past a point a holder cannot say which reading
        # they meant, and "one must decide what to mean". A nescio is a holder entry whose
        # object is the holder and whose rests are the readings in doubt; a decide answers
        # it, rests on the reading chosen, and names that reading as its value, so that a
        # reading chosen can be told from a reading found.
        if is_nescio(e):
            if self._reading(e.object):
                raise Refused("nescio", f"{e.ref}: a nescio's object is the holder, not a reading")
            if len(self.readings_of(e)) < 2:
                raise Refused("nescio", f"{e.ref} rests on fewer than two readings in doubt")
        if e.act == "decide":
            ns = [self.by_ref[a.ref] for a in e.answers if is_nescio(self.by_ref[a.ref])]
            if len(ns) != 1:
                raise Refused("decide", f"decide {e.ref} must answer one nescio")
            chosen = self._qualify(log, e.value)
            if chosen not in self.readings_of(ns[0]):
                raise Refused("decide", f"decide {e.ref}: {e.value} is not a reading "
                              f"{ns[0].ref} is in doubt about")
            if chosen not in e.rests:
                raise Refused("decide", f"decide {e.ref} must rest on the reading chosen")
            if self._object(log, e.object) != ns[0].object:
                raise Refused("decide", f"decide {e.ref}: object must be the nescio's "
                              f"holder, {ns[0].object}")
            e.value = chosen

    def mark_of(self, ref: str) -> str | None:
        """The mark a reading narrows, through earlier readings; None if it narrows a look
        or nothing."""
        seen = set()
        while ref in self.by_ref and ref not in seen:
            seen.add(ref)
            x = self.by_ref[ref]
            if x.act == "mark":
                return ref
            if x.act != "precize" or not x.narrows:
                return None
            ref = x.narrows
        return None

    def marks_between(self, e: Entry) -> frozenset[str]:
        """The marks of the readings a verdict is between."""
        return frozenset(m for r in e.between if (m := self.mark_of(r)))

    def _reading(self, obj: str | None) -> bool:
        x = obj and self.by_ref.get(obj.partition("|")[0].strip())
        return bool(x) and x.act in ("mark", "precize")

    def readings_of(self, nescio: Entry) -> list[str]:
        """The readings a nescio is in doubt between: the precizes it rests on, or, for a
        mark it rests on, the precizes that narrow that mark."""
        out = []
        for r in nescio.rests:
            x = self.by_ref.get(r)
            if x is None:
                continue
            if x.act == "precize":
                out.append(r)
            elif x.act == "mark":
                out += [p.ref for p in self.entries() if p.act == "precize" and p.narrows == r]
        return list(dict.fromkeys(out))

    def _rests_on_act(self, ref: str, act: str) -> bool:
        seen, stack = set(), [ref]
        while stack:
            r = stack.pop()
            if r in seen or r not in self.by_ref:
                continue
            seen.add(r)
            x = self.by_ref[r]
            if x.act == act:
                return True
            stack.extend(x.rests)
        return False

    def withdrawn_by(self, ref: str) -> list[Entry]:
        return [x for x in self.entries() if x.act == "withdraw" and x.withdraws == ref]

    # --- reading -------------------------------------------------------------
    def entries(self):
        for log in self.logs.values():
            yield from log

    def get(self, ref: str) -> Entry:
        return self.by_ref[ref]

    def past(self, ref: str) -> set[str]:
        """The causal past: the author's own earlier entries, what the entry cites,
        and their pasts. Does not include the entry itself."""
        cache = getattr(self, "_past", None)
        if cache is None or cache[0] != len(self.by_ref):
            cache = (len(self.by_ref), {})
            self._past = cache
        memo = cache[1]
        if ref in memo:
            return memo[ref]
        e = self.by_ref[ref]
        out: set[str] = set()
        prev = self.by_hash.get(e.prev)
        direct = ([prev.ref] if prev else []) + [c for c in e.cites() if c in self.by_ref]
        for d in direct:
            out.add(d)
            out |= self.past(d)
        memo[ref] = out
        return out

    # --- forks ---------------------------------------------------------------
    def forks(self) -> list[tuple[str, str, list[str]]]:
        """(log, predecessor, successors) for every entry with two successors in its own
        log. The proof is the two signed headers: same author, same predecessor."""
        out = []
        for log, es in self.logs.items():
            succ: dict[str, list[str]] = {}
            for e in es:
                if e.prev:
                    succ.setdefault(e.prev, []).append(e.ref)
            for h, refs in succ.items():
                if len(refs) > 1:
                    out.append((log, self.by_hash[h].ref if h in self.by_hash else h, sorted(refs)))
        return out

    def tips(self, log: str) -> list[str]:
        es = self.logs.get(log, [])
        prevs = {e.prev for e in es}
        return [e.ref for e in es if e.hash not in prevs]

    # --- storage: one JSON Lines file per log ----------------------------------
    def save(self, folder: str | Path, heads: dict[str, str] | None = None,
             logs: list[str] | None = None) -> None:
        """Write each log to <folder>/<log>.jsonl. `heads` writes a log only up to the
        given entry (its past in that log, and itself): a prefix, or one branch of a fork."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        heads = heads or {}
        for log, es in self.logs.items():
            if logs is not None and log not in logs:
                continue
            if log in heads:
                h = self._qualify(log, heads[log])
                keep = self.past(h) | {h}
                es = [e for e in es if e.ref in keep]
            with open(folder / f"{log}.jsonl", "w", encoding="utf-8") as f:
                for e in es:
                    f.write(json.dumps(e.to_json(), ensure_ascii=False) + "\n")

    @staticmethod
    def load(*folders: str | Path, keys: dict | None = None) -> "Record":
        """Read the logs in one or more folders and merge them. Copies of the same log
        are merged by hash, so two copies that branch from one entry are read as the
        union. Each hash is verified. A cite into a log or entry not read is allowed:
        the reports say what was not read. Entries are not re-checked against the write
        rules; they were checked when written.

        `keys` is the audit's registry (log -> kind and public key). An entry in a
        registered log must carry a valid signature and the registered kind, or the load
        is refused. Logs with no key are read, and reported as unsigned."""
        from .sign import verify
        rec = Record(checks=False)
        rows: dict[str, Entry] = {}
        for folder in folders:
            for p in sorted(Path(folder).glob("*.jsonl")):
                for line in p.read_text(encoding="utf-8").splitlines():
                    e = Entry.from_json(json.loads(line))
                    if _digest(e) != e.hash:
                        raise Refused("hash", f"{e.ref} does not match its hash")
                    k = (keys or {}).get(e.log)
                    if k and (e.kind != k["kind"] or not verify(k["key"], e.hash, e.sig)):
                        raise Refused("sig", f"{e.ref} is not signed by the key of {e.log}")
                    rows.setdefault(e.hash, e)
        refs = {e.ref for e in rows.values()}
        hashes = set(rows)
        pending = list(rows.values())
        while pending:  # add in an order that respects the chain and the cites
            nxt = []
            for e in pending:
                ready = all(c in rec.by_ref or c not in refs for c in e.cites()) and (
                    e.prev is None or e.prev in rec.by_hash or e.prev not in hashes)
                if not ready:
                    nxt.append(e)
                    continue
                if e.ref in rec.by_ref:  # same id, different hash: a fork by rewriting
                    raise Refused("fork", f"two different entries named {e.ref}")
                rec._put(e)
            if len(nxt) == len(pending):
                raise Refused("chain", f"cannot place {[e.ref for e in nxt]}")
            pending = nxt
        rec.signed = {log for log in rec.logs if log in (keys or {})}
        return rec
