"""An MCP server for the audit record: a thin wrapper over the `audit` library.

Each audit is a folder under AUDIT_DATA (default ./data), with one JSON Lines file per
log. Writes are checked by the library's rules and appended. Reports are computed on
every call and never stored.

Run:  .venv/bin/python server.py      (stdio)
"""
from __future__ import annotations

import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from audit import Answer, Entry, Record, Refused, fetch, render, report, store
from audit.sign import load_key, new_key, pub_hex, read_keys, register, save_key, unregister

HERE = Path(__file__).parent
ROOT = Path(os.environ.get("AUDIT_SOURCES", HERE.parent))  # what `read` may fetch
DATA = Path(os.environ.get("AUDIT_DATA", HERE / "data"))
OUT = Path(os.environ.get("AUDIT_OUT", HERE / "out"))  # rendered reports, not the record
CARD = Path(os.environ.get("AUDIT_CARD", HERE / "card.txt"))  # the procedure, plain text
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()\-]{0,63}$")  # no ':' or '/'

STOP = (
    "Write as your own author, under the log name your brief gives you (none is given "
    "here), kind='agent'. Fetch the text you cite "
    "with `read` and cite the source it returns; put quoted words in quotation marks, "
    "word for word. You may quote, mark, "
    "vary, precize, propose properties, recover norms, look, and propose a verdict. "
    "Stop and hand over to a person at: naming a holder, granting, settling, deciding "
    "what to mean, and the audit's verdict. Never cite a passage you have not read; a look needs its passage. "
    "Give a verdict's object as the quote's ref, your log name, a colon and the quote's "
    "id. "
    "If someone has already quoted the same words, the report takes both quotes as one "
    "object (same_object). "
    "The term you mark may be a logical word or a phrase whose attachment is in doubt; "
    "mark it and precize its readings as for a word, listing every reading and assuming no "
    "default, so that holders, vary and verdicts reach it. Logical words include 'and'/'och' "
    "(both; either or both; the whole taken together; each part or the whole), 'or'/'eller' "
    "(either or both; one but not both; a choice of either; in order, the first and the "
    "next only failing it or after it), 'if'/'om' (P is enough for Q, "
    "which may also come otherwise; P is the only way to Q, i.e. only if, the conditions "
    "listed are all there are; P brings Q about, a consequence and not only a conditional), "
    "'unless'/'om inte', 'only'/'bara', 'not'/'inte' (what it applies to), 'all', 'any', "
    "'every' (each one, or as a rule), and 'shall'/'ska', 'may'/'får' (duty, permission, "
    "or what will happen). A sentence may have several marks. "
    "In a grid, a position is one cell. A party that argues in the alternative, each "
    "argument enough on its own, holds a region: place it in every cell where it wins, "
    "with its arguments in the order it gives them, and say it is a region. The diagonal "
    "test is for parties with one cell; with a region in play, say it does not apply. "
    "Write each reading as its own precize, with `narrows` the mark; readings listed only in "
    "the mark's body cannot be held, varied or reached by a verdict. A precize names what it "
    "narrows in `narrows`: the mark, for first readings. With several marks, write one "
    "vary per mark, object the quote and `narrows` the mark. Where "
    "the card asks who reads a term a given way (step 3), name the candidate in the "
    "precize's body and leave the holder act to a person; a reading without a holder "
    "stays a candidate. "
    "Write a commit before you fetch what would meet it: fetch only the lines of T₀ "
    "for the quote, write the mark and the commit, then fetch further. A passage fetched before the commit stays "
    "seen; fetching it again does not help. A passage your source prints from another "
    "document (an inquiry's summary in an annex, a consultation response the source "
    "reports) is second hand: set `via` to that document. "
    "When you are done, write "
    "act='close' in your log.")

# The stopping rules are in the instructions as well as the prompts: in the live trial the
# client could not fetch prompts, and the agent found them by reading this file.
mcp = MCPServer(
    "audit-record",
    instructions=(
        "An append-only audit record after 'Saying What You Mean'. Each author writes "
        "only in their own log. holder, grant, settle and decide need a person, and a person "
        "writes with their own key outside this server; an agent's verdict "
        "is reported as proposed. Reports are computed, never written: ask `report`, whose "
        "`awaiting_grant` lists what a person must grant before the audit can go on. "
        "Read the card (resource audit://card) before auditing. " + STOP),
)


def _folder(audit: str) -> Path:
    if not NAME.match(audit):
        raise ValueError(f"bad audit name {audit!r}")
    return DATA / audit


def _load(audit: str, logs: list[str] | None = None,
          heads: dict[str, str] | None = None) -> Record:
    return store.load(_folder(audit), logs, heads)


def _agent_key(audit: str, log: str):
    """The server's key for an agent log, made and registered on the log's first entry."""
    f = _folder(audit)
    path = f / ".keys" / f"{log}.pem"
    reg = read_keys(f).get(log)
    if reg:
        if reg["kind"] != "agent" or not path.exists():
            raise Refused("person", f"log {log} is a person's; a person writes with "
                          "`python -m audit.person`, outside this server")
        return load_key(path)
    if (f / f"{log}.jsonl").exists():
        raise Refused("sig", f"log {log} was written unsigned; start a new log")
    k = new_key()
    save_key(k, path)
    register(f, log, "agent", pub_hex(k))
    return k


def _jsonable(x: Any) -> Any:
    if isinstance(x, (set, frozenset)):
        return sorted(_jsonable(i) for i in x)
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(i) for i in x]
    return x


# --- writing ------------------------------------------------------------------
@mcp.tool()
def write(audit: str, log: str, id: str, act: str, body: str = "",
          kind: str = "person", value: str | None = None, object: str | None = None,
          sources: list[str] | None = None, rests: list[str] | None = None,
          answers: list[dict] | None = None, about: str | None = None,
          between: list[str] | None = None,
          narrows: str | None = None, withdraws: str | None = None,
          reason: str | None = None, procedure: str | None = None,
          absent_what: str | None = None, absent_where: str | None = None,
          absent_in: str = "world", via: str | None = None,
          after: str | None = None) -> dict:
    """Write one entry to the author's own log in an audit.

    act: quote, mark, vary, precize, holder, grid, property, recover, grant, check,
      commit, look, verdict, withdraw, settle, decide, close, ask, show.
    Cites are "LOG:id", or "id" within the same log.
      rests: what the entry rests on; it falls if any of these is withdrawn or falls.
      answers: [{"ref": ..., "disputes": bool, "meets": bool}] - in the entry's past, but
        no cascade. `disputes` says the answered entry is wrong; `meets` says whether a
        look meets a commit.
    between: for a verdict, the readings (your precizes) the disagreement is between. A
      sentence may hold more than one disagreement, e.g. two parties on one mark and two
      holders on another; write one verdict for each, on the same quote, each naming its
      readings, and do not qualify the object to tell them apart ("q1|P2" means "under
      reading P2"). Verdicts are compared only with verdicts between readings of the same
      marked words. One author gives one value per set of marks (finding 98).
    grid: the cells of two marks' readings, listed before who is in them; a party arguing
      in the alternative holds a region (every cell where it wins, its arguments in
      order), not a cell, and the diagonal test does not apply to it (finding 97).
    verdict: value is the card's number (1a, 1b, 2, 3, 4, 5), or "none" when none of the
      five fits or there is no case (the card, 7); add a frame after it if you have one
      ("none, frame 4"). All values beginning "none" are one value, unless both give a
      frame and the frames differ.
    ask: a question for a person (e.g. which way a sentence attaches). Give the entry it
      is about in rests; it is reported in open_asks until another author answers it.
      When the question is about structure (a logical word such as "and"/"och", "or",
      "if"/"om", "only", "not", or what a phrase attaches to), list every reading, not two:
      "and" may be both, either or both ("and/or"), or the whole taken together; "or"
      may also be an order (the first, and the next only failing it or after it); "if" may
      be enough, the only way (only if), or a consequence. Assume no default. If the
      readings make the sentence's truth vary, mark the word or phrase and precize them
      instead: an ask has no holders and no verdict (findings 64, 68).
      An entry that answers an ask gives the answer, briefly, as its value ("(b)"), so that
      two authors' answers can be compared; differing answers are open.
    holder: value "nescio" (a person only) says the holder does not know which reading
      they meant (Naess): object = the holder, rests = the readings in doubt (two or more
      precizes, or the mark whose precizes they are). Reported under nescio until decided.
    decide: a person decides what to mean, past a nescio. answers = the nescio, object =
      its holder, value = the reading chosen, which it also rests on. Reported under
      decided: a reading chosen, not found in a source.
    vary: value is one of "true under all", "false under all", "varies" (the card, 1b).
    property: object = the mark of the term; value = the property, as a question about
      one case; rests = the precizations it is the property of. If there is none,
      value="none (constitutive)" (the card, 5): no rule-property divergence there.
    commit: about = what it commits about; body = what would change your mind. A look
      meets a commit (meets=true) when it gives what any one clause of the commit names.
      A commit written after you fetched more than the quoted lines stands, with a note,
      and the report lists it under committed_after_reading.
    value/object: needed for verdict, vary and holder, so that disagreement can be seen.
      Make the object a ref: the quote for a verdict or vary ("q1", or "q1|P2" under a
      reading), the mark for a holder. Free text is kept but reported as loose_objects,
      since two authors' free texts rarely match.
    sources: needed for quote and look (rules 1 and 4): the passage you read, not the
      document, as `read` returned it (e.g. "manual/body/06-four-audits.tex, lines
      450-560") or "document, passage" (e.g. "IRS Notice 2014-21, p. 2"). Two passages of
      one document count as one source.
    via: when the passage you read quotes or reports another document (second hand), the
      document it quotes, e.g. "Hugging Face, technical timeline, 27 July 2026" for the
      manual's passage quoting it. Not the document you read: that is in sources.
      This includes another body's text printed inside your source: an inquiry's summary in
      a bill's annex, a consultation response the bill reports, a committee's account of
      the bill. Name the document whose words they are, even when `read` returned only
      your source. Reported as second_hand.
    absent_what/where: for an entry resting on something not being there (in the world).
    about: a commit's object, the entry it commits about; no `rests` needed.
    narrows: a precize's target: the mark of the term (first readings), an earlier
      precize, or a look (a claim found). An agent's precize must give it. A vary may
      give the mark whose readings it varies, when the sentence has several marks; its
      object stays the quote.
    withdraws: the entry a withdraw takes back, own log only. A withdraw of a grant
      that answers the check it saw is reported "under the check"; without that cite,
      "on evidence". The report sees only what is cited.
    after: chain to this earlier own entry instead of the last one (makes a fork).
    An agent (kind='agent', its own log, named as its brief says) stops and hands over at
    holder, grant, settle, decide and the audit's verdict, and ends with act='close'.
    Returns the new ref and hash, or the rule that refused it.
    """
    if not NAME.match(log):
        return {"refused": "name", "message": f"bad log name {log!r}"}
    if kind != "agent":
        return {"refused": "person", "message": "this server signs only agent logs; a "
                "person writes with `python -m audit.person`, with their own key"}
    e = Entry(id=id, act=act, body=body, kind=kind, value=value, object=object,
              sources=sources or [], rests=rests or [],
              answers=[Answer(a["ref"], bool(a.get("disputes", False)), a.get("meets"))
                       for a in (answers or [])],
              about=about, between=between or [], narrows=narrows, withdraws=withdraws, reason=reason,
              procedure=procedure, via=via,
              absent={"in": absent_in, "what": absent_what, "where": absent_where}
              if absent_what else None)
    f = _folder(audit)
    new = log not in read_keys(f)
    try:
        store.append(f, log, e, _agent_key(audit, log), after=after)
    except (Refused, KeyError) as x:
        if new and not (f / f"{log}.jsonl").exists():
            unregister(f, log)
            (f / ".keys" / f"{log}.pem").unlink(missing_ok=True)
        if isinstance(x, Refused):
            return {"refused": x.rule, "message": str(x)}
        return {"refused": "cite", "message": f"no such entry {x}"}
    out = {"ref": e.ref, "hash": e.hash}
    if act == "commit":
        first = fetch.read_first(f, _load(audit)).get(e.ref)
        if first:
            out["note"] = ("written after you fetched " + "; ".join(first) + ". It stands, "
                           "but the report lists it under committed_after_reading: a commit "
                           "is meant to come before the reading that could meet it.")
    return out


@mcp.tool()
def read(audit: str, log: str, path: str, start: int = 1, end: int | None = None,
         plain: bool = False) -> dict:
    """Fetch lines start..end (at most 400) of a source file, for the agent run writing
    `log`. The server keeps what each run fetched. Cite the returned `source`: an entry whose
    sources were fetched must give quoted words verbatim, and a look meeting a
    commit must cite what was fetched after the commit. Quotes are checked only against
    the lines the entry's own `sources` cite, so cite the lines a quote comes from (a
    footnote too). A quote may keep the source's own quotation marks inside it. Sources
    not fetched here are
    reported as `unfetched`, since the server cannot see them.
    plain: return LaTeX source with the markup taken out. Quoted words are checked
    against the text both as it is and with the markup out, so quote either."""
    if not NAME.match(log):
        return {"refused": "name", "message": f"bad log name {log!r}"}
    p = (ROOT / path).resolve()
    if ROOT.resolve() not in p.parents or not p.is_file():
        return {"refused": "path", "message": f"no source {path!r} under the sources root"}
    lines = p.read_text(encoding="utf-8").splitlines()
    end = min(end or len(lines), len(lines), start + 399)
    text = "\n".join(lines[start - 1:end])
    rec = _load(audit)
    src = fetch.note(_folder(audit), log, path, start, end, text,
                     at=len(rec.logs.get(log, [])))
    return {"source": src, "text": fetch.plain(text) if plain else text}


@mcp.tool()
def merge(audit: str, folder: str) -> dict:
    """Read in log files handed over from elsewhere (a folder of <log>.jsonl), verify
    every hash, and merge them into the audit by hash. Forks are kept, not resolved."""
    try:
        rec = Record.load(*[p for p in (_folder(audit), Path(folder)) if p.exists()],
                          keys=read_keys(_folder(audit)))
    except Refused as r:
        return {"refused": r.rule, "message": str(r)}
    rec.save(_folder(audit))
    return {"logs": {log: len(es) for log, es in rec.logs.items()}, "forks": rec.forks()}


# --- reading ------------------------------------------------------------------
@mcp.tool(name="report")
def report_(audit: str, logs: list[str] | None = None,
            heads: dict[str, str] | None = None) -> dict:
    """The reports for an audit, computed now: withdrawn, fell (with chains), open
    (verdicts or varies on one object with different values, disputes, differing answers
    to one ask; two holders named for one reading do not oppose),
    on_open, pending commits, met-unanswered, single-source and second-hand looks,
    stops (a vary that ends the audit), constitutive readings,
    recovers awaiting a grant (with what rests on them), proposed (agent
    verdicts), same_object (verdicts, varies and holders by two or more authors on one
    object, with quotes of the same words taken as one), stands, verdicts that stand, open questions only between agents,
    unsigned logs and person-only acts in them (unverified), agent sources not fetched
    through `read` (unfetched), agent commits written after their author fetched more than the quoted
    lines (committed_after_reading), entries named in `sources` instead of `rests`
    (entries_as_sources), open_asks (asks no other author has answered), answers_to_compare (asks answered by two
    or more authors, not all with a value), unread_marks (marks no precize narrows:
    readings written only in a mark's body), nescio (a holder's
    "I don't know which reading I meant", with the readings in doubt, not yet decided),
    decided (decide entries and the reading each chose, not found), marks_differ (marks of one
    object by two or more authors on different words), drift
    (a precization or claim found narrowed after a look bore on it; not a mark's first reading), grant withdrawals (on evidence or under
    the check), rests on what was not read, and what was read: heads, logs and entries
    cited but not read, forks. `logs` reads only those logs; `heads` reads a log only up
    to an entry. A report is true of what it read and says what that was."""
    rec = _load(audit, logs, heads)
    out = asdict(report(rec))
    return _jsonable(out)



@mcp.tool()
def entry(audit: str, ref: str) -> dict:
    """One entry, with what rests on it and what answers it."""
    rec = _load(audit)
    if ref not in rec.by_ref:
        return {"error": f"no entry {ref}"}
    e = rec.get(ref)
    return {"entry": e.to_json(),
            "rested_on_by": [x.ref for x in rec.entries() if ref in x.rests],
            "answered_by": [x.ref for x in rec.entries() if any(a.ref == ref for a in x.answers)]}


@mcp.tool(name="render")
def render_(audit: str) -> dict:
    """The audit as a document for a person to read: LaTeX made from the record and the
    reports, compiled to PDF if a TeX engine is found. Verdicts (the person's first,
    then the proposed ones, grouped by object), the sentence, terms and readings,
    evidence (each commit with the looks answering it), what was withdrawn or fell, a
    box of what waits for a person, and every entry with its hash. Written outside the
    record (AUDIT_OUT, default ./out); returns the paths."""
    return render.render(_folder(audit), OUT)


@mcp.tool()
def audits() -> list[str]:
    """The audits on this server."""
    return sorted(p.name for p in DATA.iterdir() if p.is_dir()) if DATA.exists() else []


# --- resources ----------------------------------------------------------------
@mcp.resource("audit://card", mime_type="text/plain", description="The procedure on one page (Appendix A)")
def card() -> str:
    return CARD.read_text(encoding="utf-8") if CARD.exists() else "card not found"


@mcp.resource("audit://{audit}/log/{log}", mime_type="application/x-ndjson")
def log_resource(audit: str, log: str) -> str:
    p = _folder(audit) / f"{log}.jsonl"
    return p.read_text(encoding="utf-8") if p.exists() else ""


# --- prompts ------------------------------------------------------------------

@mcp.prompt()
def audit_sentence(audit: str, sentence: str, source: str) -> str:
    """Audit one sentence with the card's procedure."""
    return (f"Audit this sentence in audit '{audit}': \"{sentence}\" (source: {source}). "
            "Read audit://card first. Begin with a quote entry citing the source passage, "
            "then mark the term you suspect, and precize its readings. " + STOP)


@mcp.prompt()
def audit_argument(audit: str, argument: str, source: str) -> str:
    """Audit an argument: recover its norms, ask for grants before attacking."""
    return (f"Audit this argument in audit '{audit}': {argument} (source: {source}). "
            "Read audit://card first. Recover the norm each step needs, and do not write "
            "a check on a premise until a person has granted it. " + STOP)


if __name__ == "__main__":
    mcp.run()
