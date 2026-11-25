"""The reports, computed from the record and never written into it."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .fetch import QUOTED, _norm
from .record import CONSTITUTIVE, Record, is_nescio

OPPOSABLE = {"verdict", "vary", "holder", "decide"}
COMPARED = OPPOSABLE


def many_held(rec: Record, e) -> bool:
    """A holder whose object is a reading (a mark or precize) names one of its holders.
    A reading has many, so two such names are both true and do not oppose (finding 55);
    dispute one with answers. A holder whose object is the holder ("D", value "P1") says
    which reading that holder goes by, and still opposes another value."""
    if e.act != "holder" or not e.object:
        return False
    x = rec.by_ref.get(e.object.partition("|")[0].strip())
    return x is not None and x.act in ("mark", "precize")
KEEPING = {"close", "ask", "show"}  # acts that keep the record and claim nothing


def document(source: str) -> str:
    """The document a source names: the text before the passage ("doc, p. 3",
    "doc §6.1, lines 81-88"). Two passages of one document are one source."""
    return re.split(r"\s*(?:,|§|\blines?\b|\bpp?\.)", source, maxsplit=1)[0].strip() or source


def quoted_words(body: str) -> str | None:
    """The first passage a quote puts in quotation marks, normalised: case, whitespace and
    closing punctuation do not count."""
    m = QUOTED.search(body)
    return _norm(m.group(1) or m.group(2)).lower().rstrip(" .,;:!?") if m else None


def marked_words(e) -> str:
    """The words a mark marks: its value, or else the first passage its body quotes. A
    value that quotes its words and their context ('"or" in "the widow, widower, or
    children"') marks the first passage it quotes (finding 111)."""
    w = (e.value and (quoted_words(e.value) or e.value)) or quoted_words(e.body or "") or ""
    return _norm(w).lower().strip(" \"'“”‘’.,;:")


def contains(longer: str, shorter: str) -> bool:
    """Whether the words `shorter` stand in `longer` as whole words."""
    return bool(shorter) and f" {shorter} " in f" {longer} "


def quote_words(body: str) -> str | None:
    """The words a quote quotes: the longest passage in quotation marks, normalised. A
    quote may also put a note in quotation marks ("without the amendment note 'Lag
    (2026:1096).'"), before or after the sentence; all are verbatim, and the sentence is
    the longest (finding 65)."""
    ws = [_norm(m.group(1) or m.group(2)).lower().rstrip(" .,;:!?")
          for m in QUOTED.finditer(body or "")]
    return max(ws, key=len) if ws else None


def canon(rec: Record, obj: str) -> str:
    """An object with its quote replaced by the words quoted. Two authors who quote the
    same words in their own logs are speaking of one object (finding 26)."""
    base, sep, qual = obj.partition("|")
    e = rec.by_ref.get(base.strip())
    if e is not None and e.act == "quote":
        w = quote_words(e.body)
        if w:
            base = f'"{w}"'
    return base.strip() + sep + qual.strip()


def varied_mark(rec: Record, e) -> str | None:
    """The words of the mark a vary names in `narrows`, or None (finding 75). Two varies
    of one sentence that name marks of different words are about different terms."""
    if e.act != "vary" or not e.narrows or e.narrows not in rec.by_ref:
        return None
    return marked_words(rec.get(e.narrows)) or None


def held_marks(rec: Record, e) -> set[str]:
    """The marks a holder entry about a holder speaks of: the marks its reading narrows,
    or, for a nescio, the marks of the readings in doubt. Empty when not known. A
    holder can go by one reading of "need" and be in doubt about "a person"; the two
    do not oppose (found in the trial "need a person", 2026-11-20)."""
    if e.act != "holder" or many_held(rec, e):
        return set()
    refs = rec.readings_of(e) if is_nescio(e) else [(e.value or "").partition("|")[0].strip()]
    return {x.narrows for r in refs if (x := rec.by_ref.get(r)) is not None
            and x.act == "precize" and x.narrows}


def disputed_words(rec: Record, e) -> frozenset[str]:
    """The marked words of the readings a verdict is between (finding 98). Empty when the
    verdict names none."""
    return frozenset(marked_words(rec.get(m)) for m in rec.marks_between(e))


def same_term(rec: Record, a, b) -> bool:
    da, db = disputed_words(rec, a), disputed_words(rec, b)
    if da and db and da != db:  # two disagreements on one sentence, not one
        return False
    ma, mb = varied_mark(rec, a), varied_mark(rec, b)
    if not (ma is None or mb is None or ma == mb):
        return False
    ha, hb = held_marks(rec, a), held_marks(rec, b)
    return not (ha and hb) or bool(ha & hb)


NONE = re.compile(r"\s*(none|no verdict|no case)\b", re.I)
FRAME = re.compile(r"\bframe\s*(1a|1b|\d+)", re.I)   # 1a before \d+, or 1a is read as 1 (finding 91)


def same_value(a: str | None, b: str | None) -> bool:
    """A verdict numbered by the card is its number: "4" and "4 rule-property divergence"
    are one verdict. "none", "none of the five fits" and "no case: frame printed" are one
    value, none (finding 39). Other values are compared without case or outer whitespace."""
    num = lambda v: (m.group(1) if (m := re.match(r"\s*(\d+)\b", v or "")) else None)
    if NONE.match(a or "") and NONE.match(b or ""):
        # but two frames given are compared: "none, frame 3" is not "none, frame 4" (47)
        fa, fb = FRAME.search(a or ""), FRAME.search(b or "")
        return not (fa and fb) or fa.group(1) == fb.group(1)
    if num(a) and num(b):
        return num(a) == num(b)
    return (a or "").strip().lower() == (b or "").strip().lower()


@dataclass
class Report:
    withdrawn: set[str] = field(default_factory=set)
    fell: dict[str, list[str]] = field(default_factory=dict)   # ref -> chain down to a withdrawal
    open: list[tuple[str, str, str]] = field(default_factory=list)  # (a, b, why)
    on_open: dict[str, list[str]] = field(default_factory=dict)  # ref -> open sides it rests on
    open_between_agents: list[tuple[str, str, str]] = field(default_factory=list)  # no person took it up
    pending_commits: set[str] = field(default_factory=set)
    met_unanswered: set[str] = field(default_factory=set)
    single_source: set[str] = field(default_factory=set)  # one document, however many passages
    second_hand: dict[str, str] = field(default_factory=dict)  # look -> the document quoting
    stops: dict[str, str] = field(default_factory=dict)  # vary -> what the card says to do
    constitutive: dict[str, list[str]] = field(default_factory=dict)  # property -> rests on it
    loose_objects: set[str] = field(default_factory=set)  # verdict/vary/holder, object names no entry
    same_object: dict[str, list[str]] = field(default_factory=dict)  # "act object" -> entries, 2+ authors
    awaiting_grant: dict[str, list[str]] = field(default_factory=dict)  # recover -> rests on it
    proposed: set[str] = field(default_factory=set)
    stands: set[str] = field(default_factory=set)        # every entry not withdrawn, fallen
    verdicts_stand: set[str] = field(default_factory=set)
    drift: dict[str, list[str]] = field(default_factory=dict)  # precize -> looks after
    open_asks: set[str] = field(default_factory=set)  # asks no other author has answered
    answers_to_compare: dict[str, list[str]] = field(default_factory=dict)  # ask -> answers by 2+ authors, not all with a value
    unread_marks: set[str] = field(default_factory=set)  # marks no precize reads (finding 69)
    nescio: dict[str, list[str]] = field(default_factory=dict)  # nescio -> readings in doubt, none decided
    decided: dict[str, str] = field(default_factory=dict)  # decide -> the reading chosen, not found
    marks_differ: dict[str, list[str]] = field(default_factory=dict)  # object -> marks of 2+ authors, different words
    marks_nested: dict[str, list[tuple[str, str]]] = field(default_factory=dict)  # object -> (longer, shorter) marks of one term
    grant_withdrawals: dict[str, str] = field(default_factory=dict)  # withdraw -> why
    evidence_unread: dict[str, list[str]] = field(default_factory=dict)  # withdraw -> cites not read
    rests_unread: dict[str, list[str]] = field(default_factory=dict)  # ref -> unread support
    unsigned_logs: set[str] = field(default_factory=set)
    unverified: set[str] = field(default_factory=set)  # person-only acts in unsigned logs
    # what was read
    heads: dict[str, list[str]] = field(default_factory=dict)  # log -> tips read
    logs_not_read: set[str] = field(default_factory=set)
    entries_not_read: set[str] = field(default_factory=set)   # cited, in a log that was read
    forks: list[tuple[str, str, list[str]]] = field(default_factory=list)
    entries_as_sources: dict[str, list[str]] = field(default_factory=dict)  # ref -> entries named as sources (finding 107)
    # from the fetch log, when the record was loaded from a folder (store.load)
    unfetched: dict[str, list[str]] = field(default_factory=dict)  # agent entry -> sources not fetched through read
    committed_after_reading: dict[str, list[str]] = field(default_factory=dict)  # agent commit -> fetched before it (finding 106)


def _rests_closure(rec: Record, ref: str) -> set[str]:
    out, stack = set(), list(rec.get(ref).rests)
    while stack:
        r = stack.pop()
        if r in out:
            continue
        out.add(r)  # an unread entry is kept, but cannot be followed further
        if r in rec.by_ref:
            stack.extend(rec.get(r).rests)
    return out


def report(rec: Record) -> Report:
    R = Report()
    es = list(rec.entries())

    # 1. withdrawn: only by the author's own log (checked at write time)
    for e in es:
        if e.act == "withdraw" and e.withdraws:
            R.withdrawn.add(e.withdraws)

    # 2. fell: closure over rests from the withdrawn, with the chain
    def chain(ref, seen=()):
        for r in rec.get(ref).rests:
            if r in R.withdrawn:
                return [r]
            if r in rec.by_ref and r not in seen:
                c = chain(r, seen + (ref,))
                if c:
                    return [r] + c
        return None

    for e in es:
        if e.ref in R.withdrawn or e.act == "withdraw":
            continue
        c = chain(e.ref)
        if c:
            R.fell[e.ref] = c
    gone = R.withdrawn | set(R.fell)

    # 3. what was read, and what rests on what was not
    for log in rec.logs:
        R.heads[log] = rec.tips(log)
    R.forks = rec.forks()
    R.unsigned_logs = set(rec.logs) - rec.signed
    R.unverified = {e.ref for e in es if e.log in R.unsigned_logs and
                    (e.act in {"holder", "grant", "settle", "decide"} or
                     e.act == "verdict" and e.kind == "person")}
    for e in es:
        for c in e.cites():
            if c not in rec.by_ref:
                log = c.split(":", 1)[0]
                (R.entries_not_read if log in rec.logs else R.logs_not_read).add(
                    c if log in rec.logs else log)
    for e in es:
        if e.ref in gone or e.act == "withdraw":
            continue
        missing = sorted(r for r in ({*e.rests} | _rests_closure(rec, e.ref))
                         if r not in rec.by_ref)
        if missing:
            R.rests_unread[e.ref] = missing

    # 4. open: opposite claims by different authors, not removed, not settled
    live = [e for e in es if e.ref not in gone]
    settled = set()
    for e in live:
        if e.act == "settle":
            refs = [a.ref for a in e.answers]
            settled |= {frozenset((x, y)) for x in refs for y in refs if x != y}

    def on_branches(a, b):  # same author, neither in the other's past: a fork
        return a.ref not in rec.past(b.ref) and b.ref not in rec.past(a.ref)

    def accepts(a, b):  # an entry that rests on another does not oppose it
        return b.ref in _rests_closure(rec, a.ref) or a.ref in _rests_closure(rec, b.ref)

    pairs = {}
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if accepts(a, b) or (a.author == b.author and not on_branches(a, b)):
                continue
            if (a.act in OPPOSABLE and a.act == b.act and a.object and b.object and
                    not many_held(rec, a) and
                    canon(rec, a.object) == canon(rec, b.object) and
                    same_term(rec, a, b) and
                    not same_value(a.value, b.value)):
                pairs[frozenset((a.ref, b.ref))] = (
                    a.ref, b.ref, f"{a.object}: {a.value} / {b.value}")
    for b in live:
        for ans in b.answers:
            a = rec.by_ref.get(ans.ref)
            if not a or a.ref in gone or (a.author == b.author and not on_branches(a, b)):
                continue
            if a.absent and a.absent.get("in") == "world" and b.act == "look":
                pairs[frozenset((a.ref, b.ref))] = (a.ref, b.ref, f"fills absence: {a.absent.get('what')}")
            elif ans.disputes:
                pairs[frozenset((a.ref, b.ref))] = (a.ref, b.ref, "disputes")
    # answers to one ask by different authors are compared by value (finding 54)
    for q in (e for e in live if e.act == "ask"):
        ans = [x for x in live if x.author != q.author and q.ref in {a.ref for a in x.answers}]
        if len({x.author for x in ans}) < 2:
            continue
        if any(x.value is None for x in ans):
            R.answers_to_compare[q.ref] = sorted(x.ref for x in ans)
            continue
        for i, a in enumerate(ans):
            for b in ans[i + 1:]:
                if a.author != b.author and not accepts(a, b) and not same_value(a.value, b.value):
                    pairs.setdefault(frozenset((a.ref, b.ref)), (
                        a.ref, b.ref, f"answers {q.ref}: {a.value} / {b.value}"))
    R.open = [v for k, v in pairs.items() if k not in settled]
    taken = {c for e in live if e.kind == "person"
             for c in _rests_closure(rec, e.ref) | {a.ref for a in e.answers}}
    R.open_between_agents = [(a, b, w) for a, b, w in R.open
                             if rec.get(a).kind == rec.get(b).kind == "agent"
                             and a not in taken and b not in taken]
    by_obj: dict[str, list] = {}
    for e in live:
        if e.act in COMPARED and e.object:
            by_obj.setdefault(f"{e.act} {canon(rec, e.object)}", []).append(e)
    # varies of one sentence are split by the mark they name; a vary naming none is
    # compared with all of them, as in the logs from before finding 75
    for o in [o for o in by_obj if o.startswith("vary ")]:
        xs = by_obj.pop(o)
        named = {varied_mark(rec, x) for x in xs} - {None}
        if not named:
            by_obj[o] = xs
        for m in named:
            by_obj[f'{o} / "{m}"'] = [x for x in xs if varied_mark(rec, x) in (m, None)]
    R.same_object = {o: sorted(x.ref for x in xs) for o, xs in by_obj.items()
                     if len({x.author for x in xs}) > 1}
    sides = {x for a, b, _ in R.open for x in (a, b)}
    for e in live:
        hit = sorted((_rests_closure(rec, e.ref) | {e.ref}) & sides)
        if hit:
            R.on_open[e.ref] = hit

    # 5. pending
    for e in live:
        if e.act == "commit":
            meeting = [x for x in live if any(a.ref == e.ref and a.meets for a in x.answers)]
            if not meeting:
                R.pending_commits.add(e.ref)
            else:
                answered = any(
                    y.author == e.author and (m.ref in y.rests or any(a.ref == m.ref for a in y.answers))
                    for m in meeting for y in live)
                if not answered:
                    R.met_unanswered.add(e.ref)
        if e.act == "look":
            if len({document(s) for s in e.sources}) == 1:
                R.single_source.add(e.ref)
            if e.via:
                R.second_hand[e.ref] = e.via
        if e.act == "vary" and e.value == "true under all":
            R.stops[e.ref] = "vagueness is idle: stop, look elsewhere"
        if e.act == "vary" and e.value == "false under all":
            R.stops[e.ref] = "false on every reading: stop, report it in that form"
        if e.act == "property" and e.value == CONSTITUTIVE:
            R.constitutive[e.ref] = sorted(
                x.ref for x in live if e.ref in _rests_closure(rec, x.ref))
        # a nescio, a decide, or a holder entry whose value is a reading ("D" goes by P1)
        # names the holder, by rule, not an entry
        if e.act in COMPARED and e.object and e.object.partition("|")[0] not in rec.by_ref \
                and not (is_nescio(e) or e.act == "decide" or
                         e.act == "holder" and rec._reading(e.value)):
            R.loose_objects.add(e.ref)
        if e.act == "recover":
            granted = any(x.act == "grant" and e.ref in x.rests for x in live)
            if not granted:
                R.awaiting_grant[e.ref] = sorted(
                    x.ref for x in live if e.ref in _rests_closure(rec, x.ref))

    # 6, 7. proposed and stands
    for e in live:
        if e.act == "withdraw" or e.act in KEEPING or e.ref in R.rests_unread:
            continue
        R.stands.add(e.ref)
        if e.act == "verdict":
            (R.proposed if e.kind == "agent" else R.verdicts_stand).add(e.ref)

    # marks of one object by two or more authors on different words (finding 48)
    by_obj: dict[str, list] = {}
    for e in live:
        if e.act == "mark":
            for r in e.rests:
                if r in rec.by_ref and rec.get(r).act == "quote":
                    by_obj.setdefault(canon(rec, r), []).append(e)
    # compared author by author: a sentence may have several marks, as a word and a
    # connective; two authors who mark the same set of words do not differ (finding 64)
    # A mark whose words hold another author's mark of the same object, at word bounds, is
    # the same term at two lengths ("349 ledamöter" and "ledamöter", findings 74 and 92):
    # reported as nested, both marks kept, so the longer span's point is not hidden.
    for obj, ms in by_obj.items():
        words = {m.ref: marked_words(m) for m in ms}
        own = {a: {words[m.ref] for m in ms if m.author == a} for a in {m.author for m in ms}}
        term = {}
        for m in ms:
            inside = [n for n in ms if n.author != m.author and words[n.ref] not in own[m.author]
                      and contains(words[m.ref], words[n.ref])]
            term[m.ref] = min((words[n.ref] for n in inside), key=len, default=words[m.ref])
            for n in inside:
                R.marks_nested.setdefault(obj, []).append((m.ref, n.ref))
        sets: dict[str, set] = {}
        for m in ms:
            sets.setdefault(m.author, set()).add(term[m.ref])
        if len(sets) > 1 and len({frozenset(v) for v in sets.values()}) > 1:
            R.marks_differ[obj] = sorted(m.ref for m in ms)
        if obj in R.marks_nested:
            R.marks_nested[obj].sort()

    # a mark whose readings are written only in its own body has nothing a holder, vary or
    # verdict can name (finding 69). Read: some precize narrows it, or, in logs from before
    # `narrows`, rests on it without naming a target.
    for e in live:
        if e.act == "mark" and not any(
                x.act == "precize" and (x.narrows == e.ref or (not x.narrows and e.ref in x.rests))
                for x in live):
            R.unread_marks.add(e.ref)

    # nescio and decide (Naess): a reading chosen is told apart from a reading found
    for e in live:
        if e.act == "decide":
            R.decided[e.ref] = e.value
    for e in live:
        if is_nescio(e) and not any(
                x.act == "decide" and e.ref in {a.ref for a in x.answers} for x in live):
            R.nescio[e.ref] = rec.readings_of(e)

    # an ask is open until an entry by another author answers it (finding 45)
    for e in live:
        if e.act == "ask" and not any(
                x.author != e.author and e.ref in {a.ref for a in x.answers} for x in live):
            R.open_asks.add(e.ref)

    # 8. flags
    for e in live:
        # a first reading of a marked term does not drift (finding 42): written after
        # the looks, it is informed by them, not revised. A precization narrowed after a
        # look bore on it still drifts. A reading that narrows a look writes down a claim
        # the look found; it drifts only if a later look cites that look (finding 63),
        # not because another look merely came before it in the log.
        if e.act == "precize" and e.narrows and e.narrows in rec.by_ref \
                and rec.get(e.narrows).act != "mark":
            after = rec.past(e.ref) - rec.past(e.narrows) - {e.narrows}
            looks = sorted(r for r in after if rec.get(r).act == "look"
                           and (rec.get(e.narrows).act != "look"
                                or e.narrows in rec.get(r).cites()))
            if looks:
                R.drift[e.ref] = looks
    for e in es:
        if e.act == "withdraw" and e.withdraws and rec.get(e.withdraws).act == "grant":
            checks = [x.ref for x in es if x.act == "check" and e.withdraws in x.rests]
            under = [c for c in checks if c in rec.past(e.ref)]
            R.grant_withdrawals[e.ref] = "under the check" if under else "on evidence"
            unread = [a.ref for a in e.answers if a.ref not in rec.by_ref]
            if unread:
                R.evidence_unread[e.ref] = unread
    for e in rec.entries():
        named = [x for x in e.sources if rec.names_entry(e.log, x)]
        if named:
            R.entries_as_sources[e.ref] = named
    if rec.folder is not None:
        from . import fetch
        R.unfetched = fetch.unfetched(rec.folder, rec)
        R.committed_after_reading = fetch.read_first(rec.folder, rec)
    return R
