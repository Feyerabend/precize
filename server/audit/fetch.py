"""The agent checks (stage 4). The server keeps a ledger of what each agent run fetched
through its `read` tool. Three checks follow from it:

- **verbatim:** an agent's entry whose sources were fetched (a quote or look, or any
  other act that gives sources) must give every
  passage it puts in quotation marks word for word from the fetched text, either as
  fetched or with LaTeX markup taken out (`plain`). Otherwise it is refused.
- **commit-first:** an agent's look that answers its own commit must not cite a passage
  the run fetched before writing the commit. Otherwise it is refused.
- **unfetched:** an agent's entry citing a source the run did not fetch through
  the server is not refused. The server cannot see what was read elsewhere, so it reports
  the entry under `unfetched`.

The ledger lives at `<audit>/.fetched/<log>.jsonl`. It is the server's, not the agent's,
and it is not part of the record.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .record import Entry, Record, Refused

SOURCE = re.compile(r"^(?P<path>[^,§]+?)(?:\s*§[^,]*)?,\s*lines?\s+(?P<a>\d+)"
                    r"(?:\s*[-–]\s*(?P<b>\d+))?\s*$")
QUOTED = re.compile(r'"([^"]+)"|“([^”]+)”')


def parse(source: str):
    m = SOURCE.match(source.strip())
    if not m:
        return None
    a = int(m["a"])
    return m["path"].strip(), a, int(m["b"] or a)


def _ledger(folder: Path, log: str) -> Path:
    return Path(folder) / ".fetched" / f"{log}.jsonl"


def note(folder: Path, log: str, path: str, a: int, b: int, text: str, at: int) -> str:
    """Record a fetch. `at` is the number of entries in the run's log at the time."""
    p = _ledger(folder, log)
    p.parent.mkdir(parents=True, exist_ok=True)
    source = f"{path}, lines {a}-{b}"
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"source": source, "path": path, "a": a, "b": b, "at": at,
                            "text": text}, ensure_ascii=False) + "\n")
    return source


def fetches(folder: Path, log: str) -> list[dict]:
    p = _ledger(folder, log)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def _covering(fs: list[dict], source: str) -> list[dict]:
    p = parse(source)
    if not p:
        return []
    path, a, b = p
    one = [f for f in fs if f["path"] == path and f["a"] <= a and b <= f["b"]]
    if one:
        return one
    # lines read in two or more fetches that join (1-400, then 401-748) are read too
    parts = sorted((f for f in fs if f["path"] == path and f["a"] <= b and a <= f["b"]),
                   key=lambda f: f["a"])
    upto, used = a - 1, []
    for f in parts:
        if f["a"] > upto + 1:
            break
        if f["b"] > upto:
            used.append(f)
            upto = f["b"]
        if upto >= b:
            return used
    return []


CMD_ARG = re.compile(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}")


def plain(s: str) -> str:
    """LaTeX source with the markup taken out: comments dropped, `\\cmd{x}` read as x
    (innermost first), bare commands and braces removed. Line breaks are kept, so
    line numbers still hold for text inside one line."""
    s = re.sub(r"(?<!\\)%.*", "", s)
    s = re.sub(r"\\(?:ref|pageref|eqref|label|cite|index)\*?\{[^{}]*\}", "", s)
    s = s.replace("\\\\", " ").replace("\\,", " ").replace("~", " ")
    prev = None
    while prev != s:
        prev, s = s, CMD_ARG.sub(r"\1", s)
    s = re.sub(r"\\[A-Za-z]+\*?", "", s)
    return s.replace("{", "").replace("}", "")


def _norm(s: str) -> str:
    s = s.replace("``", '"').replace("''", '"')
    return " ".join(s.split())


def unquoted(body: str, texts: tuple[str, ...]) -> str | None:
    """The first quoted passage in body that is not in any of texts, or None.

    A quote may hold the source's own quotation marks ("there is no "widow""), so a
    straight mark does not always close the quote it seems to. From each opening mark
    the longest span to a later mark that is in the text is taken; only if no span is,
    the quote is refused, as the shortest span (finding 100). Curly quotes pair as
    before."""
    found = lambda s: any(s in t for t in texts)
    for m in re.finditer(r"“([^”]+)”", body):
        if not found(_norm(m.group(1))):
            return _norm(m.group(1))
    marks = [i for i, ch in enumerate(body) if ch == '"']
    i = 0
    while i + 1 < len(marks):
        for j in range(len(marks) - 1 if (len(marks) - 1 - i) % 2 else len(marks) - 2, i, -2):
            if found(_norm(body[marks[i] + 1:marks[j]])):
                i = j + 1
                break
        else:
            seg = _norm(body[marks[i] + 1:marks[i + 1]])
            if seg and not found(seg):
                return seg
            i += 2
    return None


def check(folder: Path, rec: Record, e: Entry) -> None:
    """Run at write time, after the entry's refs are qualified."""
    if e.kind != "agent" or not e.sources:
        return
    fs = fetches(folder, e.log)
    covered = {s: _covering(fs, s) for s in e.sources}
    if e.sources and all(covered.values()):
        raw = " ".join(f["text"] for c in covered.values() for f in c)
        texts = (_norm(raw), _norm(plain(raw)))   # as fetched, or with the markup out
        seg = unquoted(e.body, texts)
        if seg is not None:
            raise Refused("verbatim", f"{e.ref} quotes {seg!r}, not in the fetched text")
    if e.act == "look":
        own = [x.ref for x in rec.logs.get(e.log, []) if x.ref != e.ref]
        for ans in e.answers:
            if ans.ref in own and rec.get(ans.ref).act == "commit":
                i = own.index(ans.ref)
                for s, c in covered.items():
                    if c and min(f["at"] for f in c) <= i:
                        raise Refused("commit-first",
                                      f"{e.ref} cites {s}, fetched before commit {ans.ref}")


CARD = "manual/body/08-the-procedure-on-one-page.tex"   # the card the server serves


def read_first(folder: Path, rec: Record) -> dict[str, list[str]]:
    """Agent commits written after their author fetched more than the quoted lines
    (finding 106): commit -> what was fetched before it. The server refuses a look that
    meets a commit with what was fetched before it, but a commit no look meets is pending
    either way, and only the fetch log shows it came last. Lines that a quote written
    before the commit cites do not count: a sentence must be read to be quoted. Nor does
    the procedure card, which a run reads as its instructions, not as evidence."""
    out = {}
    for log, es in rec.logs.items():
        fs = fetches(folder, log)
        for i, e in enumerate(es):
            if e.act != "commit" or e.kind != "agent":
                continue
            quoted = [parse(src) for q in es[:i] if q.act == "quote" for src in q.sources]
            read = [f["source"] for f in fs if f["at"] <= i and f["path"] != CARD and not any(
                q and q[0] == f["path"] and q[1] <= f["a"] and f["b"] <= q[2] for q in quoted)]
            if read:
                out[e.ref] = sorted(set(read))
    return out


def unfetched(folder: Path, rec: Record) -> dict[str, list[str]]:
    out = {}
    for e in rec.entries():
        if e.kind == "agent" and e.sources:
            fs = fetches(folder, e.log)
            miss = [s for s in e.sources if not _covering(fs, s)
                    and not rec.names_entry(e.log, s)]   # an entry is not a source (107)
            if miss:
                out[e.ref] = miss
    return out
