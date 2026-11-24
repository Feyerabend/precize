"""The audit, as a document a person reads: LaTeX made from the record and the reports,
compiled to PDF when a TeX engine is found. Like the reports, it is computed and never
written into the record.

    python -m audit.render AUDIT_DIR [OUT_DIR] [--lang sv]

writes OUT_DIR/<audit>.tex (default OUT_DIR: ./out) and, if tectonic, lualatex or
xelatex is on the path, OUT_DIR/<audit>.pdf. With --lang sv the labels are in Swedish and the
files are <audit>.sv.tex and <audit>.sv.pdf; the entries are printed as written.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import fetch, store
from .record import Entry, Record
from .reports import Report, canon, marked_words, report, same_value

# ---------------------------------------------------------------------------- text

_ESC = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
        "#": r"\#", "^": r"\textasciicircum{}", "_": r"\_", "%": r"\%",
        "~": r"\textasciitilde{}", "<": r"\textless{}", ">": r"\textgreater{}"}


def esc(s: str | None) -> str:
    """Plain text to LaTeX. Straight double quotes become curly ones, in pairs."""
    if not s:
        return ""
    out = "".join(_ESC.get(c, c) for c in s)
    out = re.sub(r'"([^"]*)"', "“\\1”", out)
    return out.replace('"', "”")


def tt(s: str) -> str:
    """Mono, breakable after / , : and - so long paths fit the measure."""
    return r"\texttt{" + re.sub(r"([/,:\-])", r"\1\\allowbreak{}", esc(s)) + "}"


def anchor(e: Entry) -> str:
    return "e" + e.hash[:12]


# ---------------------------------------------------------------------------- language

SV = {
    # tags
    "withdrawn": "återkallad", "fell": "föll", "proposed": "föreslagen", "stands": "står",
    "open": "öppen", "pending": "väntar", "met, unanswered": "mött, obesvarat",
    "one source": "en källa", "second hand": "i andra hand", "unanswered": "obesvarad",
    "drift": "drift", "rests on unread": "vilar på oläst", "unfetched": "ej hämtad",
    "unverified": "ej verifierad", "loose object": "löst objekt", "no readings": "inga läsningar", "not read": "ej läst",
    "nescio": "nescio", "decided": "beslutad", "chosen": "vald",
    "fork": "förgrening", "unsigned": "osignerad", "no": "nej", "yes": "ja",
    # fields
    "value": "värde", "object": "objekt", "narrows": "snävar in", "about": "om", "between": "mellan",
    "source": "källa", "via": "via", "rests on": "vilar på", "answers": "besvarar",
    " (disputes)": " (bestrider)", " (meets)": " (möter)", " (does not meet)": " (möter inte)",
    "absent": "saknas", "in": "i", "withdraws": "återkallar", "procedure": "procedur",
    "grant": "medgivande", "withdrawn ": "återkallat ",
    # hand-over
    "For a person": "Till en person",
    "Open between agents, taken up by no person": "Öppet mellan agenter, inte upptaget av någon person",
    "Open": "Öppet",
    "Proposed verdicts no person has answered or rested on":
        "Föreslagna utslag som ingen person har besvarat eller vilat på",
    "Recovers awaiting a grant": "Rekonstruktioner som väntar på medgivande",
    "Commits no look meets yet": "Åtaganden som ingen granskning möter ännu",
    "Commits met, and not answered by their author": "Åtaganden som mötts men inte besvarats av sin författare",
    "A person's readings with no holder named": "En persons läsningar utan namngiven innehavare",
    "Stops (the card says the audit ends here)": "Stopp (kortet säger att granskningen slutar här)",
    "Marks of one sentence on different terms, by different authors":
        "Markeringar av en mening på olika termer, av olika författare",
    "One term marked at two lengths, by different authors (compare the spans)":
        "En term markerad i två längder, av olika författare (jämför spannen)",
    "holds": "rymmer",
    "Entries named as sources (sources cite texts)":
        "Poster angivna som källor (källor anger texter)",
    "Commits written after their author read further (shown by the fetch log)":
        "Åtaganden skrivna efter att författaren läst vidare (syns i hämtloggen)",
    "Readings a holder does not know (nescio), not decided":
        "Läsningar som en innehavare inte vet (nescio), inte beslutade",
    "Decided, not found": "Beslutat, inte funnet",
    "Marks with no reading written as a precize":
        "Markeringar utan någon läsning skriven som precisering",
    "Questions asked of a person, not answered": "Frågor ställda till en person, obesvarade",
    "Questions answered by different authors, to compare by hand":
        "Frågor besvarade av olika författare, att jämföra för hand",
    "Drift (a reading narrowed after a look bore on it)":
        "Drift (en läsning snävades in efter att en granskning berört den)",
    "Sources an agent did not fetch through the server": "Källor som en agent inte hämtade via servern",
    "Resting on what was not read": "Vilar på det som inte lästes",
    "Person-only acts in unsigned logs": "Personakter i osignerade loggar",
    "Objects that name no entry": "Objekt som inte namnger någon post",
    "Nothing is waiting.": "Inget väntar.",
    # document
    "Audit": "Granskning", "Computed": "Beräknad", "from the record. Not part of the record.":
        "ur protokollet. Inte en del av protokollet.",
    "What was read": "Vad som lästes", "Log": "Logg", "Kind": "Slag", "Entries": "Poster",
    "Signed": "Signerad", "Head": "Huvud", "Logs cited but not read": "Loggar som citeras men inte lästes",
    "Entries cited but not read": "Poster som citeras men inte lästes", "in": "i",
    "Verdicts": "Utslag", "No verdict is on the record.": "Inget utslag finns i protokollet.",
    "The audit's verdicts, by a person": "Granskningens utslag, av en person",
    "Settled": "Avgjort", "Proposed by agents": "Föreslaget av agenter",
    "On one object,": "På ett objekt,", "The sentence": "Meningen", "None.": "Inga.",
    "Terms and readings": "Termer och läsningar", "Marked": "Markerat",
    "Precizations": "Preciseringar", "Holders": "Innehavare",
    "Does the truth value vary?": "Varierar sanningsvärdet?", "Properties": "Egenskaper",
    "Recovered, granted, checked": "Rekonstruerat, medgivet, prövat",
    "narrowing": "snävar in", "nothing": "ingenting",
    "Evidence": "Belägg", "Looks that answer no commit": "Granskningar som inte besvarar något åtagande",
    "No evidence is on the record.": "Inga belägg finns i protokollet.",
    "looks answering it": "granskningar som besvarar det",
    "Withdrawn and fallen": "Återkallat och fallet", "Nothing was withdrawn.": "Inget återkallades.",
    "fell, by": "föll, genom",
    "The record, entry by entry": "Protokollet, post för post",
    "RECORD_NOTE": (r"Varje logg i den ordning den skrevs. Hashen är de tolv första tecknen "
                    r"i postens SHA-256; \emph{signerad} betyder att postens signatur "
                    r"verifierades mot nyckeln som registrerats för loggen."),
    "Id": "Id", "Act": "Akt", "Hash": "Hash", "Body": "Text",
    "agent": "agent", "person": "person",
    "The case": "Fallet", "Source": "Källa", "Why it is contested": "Varför den är omstridd",
    "What was done": "Vad som gjordes", "Outcome": "Utfall", "What it showed": "Vad det visade",
    "REF_NOTE": (r"En hänvisning som \texttt{g1:vd1} pekar ut en post: loggen med sitt namn "
                 r"i tabellen och sedan postens id, som dess författare valt. Varje hänvisning "
                 r"är en länk till posten i bilagan, där dess akt och text står."),
    "CASE_NOTE": r"Skrivet av författaren, inte beräknat. Inte en del av protokollet.",
    "Name": "Namn", "At a glance": "Översikt", "Readings": "Läsningar",
    "Truth value": "Sanningsvärde", "Property": "Egenskap", "Decided": "Beslutat",
    "Commits / looks": "Åtaganden / granskningar", "Verdict": "Utslag",
    "Withdrawn": "Återkallat", "Who": "Vem", "Value": "Värde", "Adopts": "Antar",
    "Status": "Läge", "Verdicts on the record": "Utslag i protokollet",
    "Open against each other": "Öppna mot varandra", "Other open questions": "Andra öppna frågor",
    "What each verdict rests on": "Vad varje utslag vilar på", "above": "ovan",
    "further": "till",
    "TREE_NOTE": (r"Varje utslag med det det vilar på, två led ned. En post som redan visats "
                  r"står med $\uparrow$ och visas inte igen; (+$n$ till) säger hur många poster en post längre ned vilar på. Varje id är en länk till posten."),
    "GLANCE_NOTE": (r"En kolumn per logg, en rad per steg på kortet. Varje id är en länk till "
                    r"posten. Tabellen ordnar bara det som står i protokollet; att två loggars "
                    r"läsningar med samma namn är samma läsning avgör den inte."),
}
EN = {"REF_NOTE": (r"A reference such as \texttt{g1:vd1} names one entry: the log by its "
                   r"name in the table, then the entry's id, which its author chose. Each is a "
                   r"link to the entry in the appendix, where its act and text are given."),
      "TREE_NOTE": (r"Each verdict with what it rests on, two steps down. An entry already "
                    r"shown is marked $\uparrow$ and not shown again; (+$n$ further) gives how many entries a deeper entry rests on. Each id is a link to the entry."),
      "GLANCE_NOTE": (r"One column per log, one row per step of the card. Each id is a link to "
                      r"the entry. The table only arranges what is on the record; it does not "
                      r"say that two logs' readings with the same name are the same reading."),
      "CASE_NOTE": r"Written by the author, not computed. Not part of the record.",
      "RECORD_NOTE": (r"Each log in the order written. The hash is the first twelve characters "
                      r"of the entry's SHA-256; \emph{signed} means the entry's signature was "
                      r"verified against the key registered for its log.")}
LANG = {"en": EN, "sv": SV}


# ---------------------------------------------------------------------------- status

def statuses(rec: Record, R: Report, unf: dict) -> dict[str, list[str]]:
    """What the reports say of each entry, as short tags."""
    sides = {x for a, b, _ in R.open for x in (a, b)}
    chosen = set(R.decided.values())
    tags: dict[str, list[str]] = {}
    for e in rec.entries():
        t = []
        if e.ref in R.withdrawn:
            t.append("withdrawn")
        elif e.ref in R.fell:
            t.append("fell")
        elif e.ref in R.proposed:
            t.append("proposed")
        elif e.ref in R.verdicts_stand:
            t.append("stands")
        if e.ref in sides:
            t.append("open")
        if e.ref in R.pending_commits:
            t.append("pending")
        if e.ref in R.met_unanswered:
            t.append("met, unanswered")
        if e.ref in R.single_source:
            t.append("one source")
        if e.ref in R.second_hand:
            t.append("second hand")
        if e.ref in R.open_asks:
            t.append("unanswered")
        if e.ref in R.drift:
            t.append("drift")
        if e.ref in R.rests_unread:
            t.append("rests on unread")
        if e.ref in unf:
            t.append("unfetched")
        if e.ref in R.unverified:
            t.append("unverified")
        if e.ref in R.loose_objects:
            t.append("loose object")
        if e.ref in R.unread_marks:
            t.append("no readings")
        if e.ref in R.nescio:
            t.append("nescio")
        if e.ref in R.decided:
            t.append("decided")
        if e.ref in chosen:
            t.append("chosen")
        tags[e.ref] = t
    return tags


WARN = {"withdrawn", "fell", "open", "pending", "met, unanswered", "unanswered", "drift",
        "rests on unread", "unfetched", "unverified", "loose object", "no readings", "nescio"}


def short_names(logs) -> dict[str, str]:
    """Each log's short name: the part before " (", as "g1" for "g1 (for A)", when no
    other log has it; otherwise the whole name."""
    first = {log: log.split(" (", 1)[0].strip() or log for log in logs}
    count = {}
    for n in first.values():
        count[n] = count.get(n, 0) + 1
    return {log: (n if count[n] == 1 and n not in logs or n == log else log)
            for log, n in first.items()}


class Doc:
    def __init__(self, folder: Path, lang: str = "en"):
        self.lang = lang
        self.folder = Path(folder)
        self.rec = store.load(self.folder)
        self.R = report(self.rec)
        self.unf = fetch.unfetched(self.folder, self.rec)
        self.first = fetch.read_first(self.folder, self.rec)
        self.tags = statuses(self.rec, self.R, self.unf)
        self.names = short_names(self.rec.logs)
        self.out: list[str] = []

    # -- small pieces
    def t(self, s: str) -> str:
        """The label in the report's language; English is the default."""
        return LANG.get(self.lang, EN).get(s, s)

    def w(self, *lines: str) -> None:
        for ln in lines:   # a heading is not left alone at the foot of a page
            self.out.append(r"\needspace{5\baselineskip}" + ln
                            if ln.startswith(r"\subsection*") else ln)

    def short(self, r: str) -> str:
        """A reference with its log's short name: "G (fictional ...):vd1" is "G:vd1"."""
        for log, n in self.names.items():
            if r.startswith(log + ":"):
                return n + r[len(log):]
        return r

    def sh(self, text: str) -> str:
        """Computed text (not an entry's own) with every log's short name."""
        for log in sorted(self.names, key=len, reverse=True):
            text = text.replace(log + ":", self.names[log] + ":")
        return text

    def ref(self, r: str) -> str:
        e = self.rec.by_ref.get(r)
        if e is None:
            return tt(self.short(r)) + r"\,\etag{" + self.t("not read") + "}"
        return r"\hyperlink{" + anchor(e) + "}{" + tt(self.short(r)) + "}"

    def refs(self, rs) -> str:
        return ", ".join(self.ref(r) for r in rs) or "—"

    def tagline(self, r: str) -> str:
        return "".join((r"\warn{" if t in WARN else r"\etag{") + esc(self.t(t)) + "}"
                       for t in self.tags.get(r, []))

    def item(self, e: Entry, extra: str = "") -> str:
        """One entry as a paragraph: ref, author kind, tags, body, then the fields."""
        who = r"\agent" if e.kind == "agent" else r"\person"
        head = rf"\entryhead{{{self.ref(e.ref)}}}{{{who}}}{{{self.tagline(e.ref)}}}"
        L = self.t
        rows = []
        if e.value is not None:
            rows.append((L("value"), esc(e.value)))
        if e.object:
            rows.append((L("object"), self.obj(e.object)))
        if e.narrows:
            rows.append((L("narrows"), self.ref(e.narrows)))
        if e.about:
            rows.append((L("about"), self.ref(e.about)))
        if e.between:
            rows.append((L("between"), self.refs(e.between)))
        for s in e.sources:
            rows.append((L("source"), tt(s)))
        if e.via:
            rows.append((L("via"), esc(e.via)))
        if e.rests:
            rows.append((L("rests on"), self.refs(e.rests)))
        if e.answers:
            rows.append((L("answers"), ", ".join(
                self.ref(a.ref) + (L(" (disputes)") if a.disputes else "") +
                ({True: L(" (meets)"), False: L(" (does not meet)")}.get(a.meets, ""))
                for a in e.answers)))
        if e.absent:
            rows.append((L("absent"), esc(f"{L('in')} {e.absent.get('in')}: {e.absent.get('what')}"
                                       f" ({e.absent.get('where')})")))
        if e.withdraws:
            rows.append((L("withdraws"), self.ref(e.withdraws) +
                         (f" — {esc(e.reason)}" if e.reason else "")))
        if e.procedure:
            rows.append((L("procedure"), esc(e.procedure)))
        fields = "".join(rf"\field{{{k}}}{{{v}}}" for k, v in rows)
        return head + r"\entrybody{" + esc(e.body) + "}" + fields + extra + r"\entryend"

    def obj(self, o: str) -> str:
        base, sep, qual = o.partition("|")
        b = self.ref(base) if base in self.rec.by_ref else esc(base)
        return b + (r" \textbar{} " + esc(qual) if sep else "")

    def section(self, title: str, es: list[Entry], empty: str = "None.") -> None:
        self.w(rf"\section{{{self.t(title)}}}")
        if not es:
            self.w(esc(self.t(empty)), "")
        for e in es:
            self.w(self.item(e), "")

    def of(self, *acts: str) -> list[Entry]:
        return [e for e in self.rec.entries() if e.act in acts]

    # -- the hand-over list
    def handover(self) -> list[tuple[str, str]]:
        rec, R = self.rec, self.R
        live = [e for e in rec.entries() if e.ref not in R.withdrawn and e.ref not in R.fell]
        persons = [e for e in live if e.kind == "person"]
        taken = set()
        for p in persons:
            taken |= set(p.rests) | {a.ref for a in p.answers}
        untaken = sorted(r for r in R.proposed if r not in taken)
        held = set()
        for h in (e for e in live if e.act == "holder"):
            held |= {h.object.partition("|")[0]} | set(h.rests) if h.object else set(h.rests)
        readings = sorted(e.ref for e in live if e.act in ("mark", "precize")
                          and e.kind == "person" and e.ref not in held)
        out = []

        def lines(items):  # one item per line, a wrapped item hangs under its first line
            return r"\mbox{}" + "".join(
                r"\par\parshape=0\noindent\hangindent=1.5em\hangafter=1 " + i for i in items)

        def add(what, rs, how=None):
            if rs:
                out.append((self.t(what), how(rs) if how else self.refs(rs)))
        add("Open between agents, taken up by no person",
            [x for a, b, _ in R.open_between_agents for x in (a, b)])
        isv = lambda r: rec.get(r).act in ("verdict", "settle")
        add("Other open questions" if any(isv(a) and isv(b) for a, b, _ in R.open) else "Open",
            [(a, b, w) for a, b, w in R.open if not (isv(a) and isv(b))], lambda ps: lines(
            f"{self.ref(a)} / {self.ref(b)} ({esc(self.sh(w))})" for a, b, w in ps))
        add("Proposed verdicts no person has answered or rested on", untaken)
        add("Recovers awaiting a grant", sorted(R.awaiting_grant))
        add("Commits no look meets yet", sorted(R.pending_commits))
        add("Commits met, and not answered by their author", sorted(R.met_unanswered))
        add("A person's readings with no holder named", readings)
        add("Stops (the card says the audit ends here)", sorted(R.stops), lambda rs: lines(
            f"{self.ref(r)}: {esc(self.sh(R.stops[r]))}" for r in rs))
        add("Marks of one sentence on different terms, by different authors",
            sorted(r for rs in R.marks_differ.values() for r in rs))
        add("One term marked at two lengths, by different authors (compare the spans)",
            sorted(p for ps in R.marks_nested.values() for p in ps), lambda ps: lines(
                f"{self.ref(a)} {self.t('holds')} {self.ref(b)}" for a, b in ps))
        add("Marks with no reading written as a precize", sorted(R.unread_marks))
        add("Readings a holder does not know (nescio), not decided", sorted(R.nescio),
            lambda rs: lines(f"{self.ref(r)}: " + self.refs(R.nescio[r]) for r in rs))
        add("Questions asked of a person, not answered", sorted(R.open_asks))
        add("Questions answered by different authors, to compare by hand",
            sorted(R.answers_to_compare), lambda qs: lines(
                f"{self.ref(q)}: " + ", ".join(self.ref(a) for a in R.answers_to_compare[q])
                for q in qs))
        add("Drift (a reading narrowed after a look bore on it)", sorted(R.drift))
        add("Commits written after their author read further (shown by the fetch log)",
            sorted(self.first), lambda rs: lines(
                f"{self.ref(r)}: " + esc("; ".join(self.first[r])) for r in rs))
        add("Sources an agent did not fetch through the server", sorted(self.unf))
        add("Entries named as sources (sources cite texts)", sorted(R.entries_as_sources),
            lambda rs: lines(f"{self.ref(r)}: " + self.refs(R.entries_as_sources[r]) for r in rs))
        add("Resting on what was not read", sorted(R.rests_unread))
        add("Person-only acts in unsigned logs", sorted(R.unverified))
        add("Objects that name no entry", sorted(R.loose_objects))
        return out

    # -- the overview
    def cut(self, v: str | None, n: int = 34) -> str:
        v = " ".join((v or "").split())
        return esc(v if len(v) <= n else v[:n - 1].rstrip() + "…")

    def cell(self, e: Entry, value: str = "") -> str:
        """One entry in the overview: its id as a link, a short value, the tags that matter."""
        tags = [t for t in self.tags.get(e.ref, []) if t in ("withdrawn", "fell", "open")]
        return (r"\hyperlink{" + anchor(e) + "}{" + tt(e.id) + "}"
                + (" " + value if value else "")
                + "".join(r"\warn{" + esc(self.t(t)) + "}" for t in tags))

    def glance(self) -> None:
        """The overview: one column per log, one row per step of the card. It arranges what
        is on the record and decides nothing; readings are not matched across logs."""
        rec, T = self.rec, self.t
        logs = list(rec.logs)
        val = lambda e: self.cut(self.sh(e.value or ""))
        rows = [
            ("The sentence", ("quote",), lambda e: ""),
            ("Marked", ("mark",), lambda e: "“" + self.cut(marked_words(e), 24) + "”"),
            ("Readings", ("precize",), lambda e: ""),
            ("Truth value", ("vary",), val),
            ("Property", ("property",), val),
            ("Holders", ("holder",), val),
            ("Decided", ("decide",), val),
            ("Verdict", ("verdict", "settle"), lambda e: r"\textbf{" + val(e) + "}"),
            ("Withdrawn", ("withdraw",), lambda e: ""),
        ]
        body = []
        for title, acts, how in rows:
            cells = []
            for log in logs:
                es = [e for e in rec.logs[log] if e.act in acts]
                sep = ", " if acts in (("precize",), ("withdraw",), ("quote",)) else r"\newline "
                cells.append(sep.join(self.cell(e, how(e)) for e in es) or r"\leavevmode{\color{tagc}—}")
            if any("hyperlink" in c for c in cells):
                body.append(rf"\textbf{{{T(title)}}} & " + " & ".join(cells) + r" \\")
            if title == "Holders":   # the evidence, counted
                n = [(sum(e.act == "commit" for e in rec.logs[l]), sum(e.act == "look" for e in rec.logs[l]))
                     for l in logs]
                if any(a or b for a, b in n):
                    body.append(rf"\textbf{{{T('Commits / looks')}}} & "
                                + " & ".join(f"{a} / {b}" for a, b in n) + r" \\")
        if not body:
            return
        k = len(logs)
        col = rf">{{\RaggedRight\arraybackslash}}p{{\dimexpr(\linewidth-20mm-{2 * k}\tabcolsep)/{k}\relax}}"
        self.w(rf"\section*{{{T('At a glance')}}}", r"{\footnotesize\setlength{\tabcolsep}{3pt}",
               r"\noindent\begin{tabular}{@{}>{\RaggedRight}p{20mm}" + col * k + r"@{}}\toprule",
               " & ".join([""] + [rf"\textbf{{{esc(self.names[l])}}}\newline{{\color{{tagc}}{T(rec.logs[l][0].kind if rec.logs[l] else '')}}}"
                                  for l in logs]) + r" \\ \midrule")
        for i, b in enumerate(body):
            self.w(b + (r" \addlinespace[2pt]" if i < len(body) - 1 else ""))
        self.w(r"\bottomrule\end{tabular}\par}", "",
               rf"{{\footnotesize\color{{tagc}}{T('GLANCE_NOTE')}}}\par", "")

    def trees(self, depth: int = 2) -> None:
        """What each verdict rests on, as an indented tree. What it rests on is a graph,
        not a tree, so each entry is expanded once; later it is marked as shown above."""
        rec, T = self.rec, self.t
        vs = [e for e in rec.entries() if e.act in ("verdict", "settle")]
        if not vs:
            return
        vs.sort(key=lambda e: (e.act != "settle", e.kind != "person"))
        shown: set[str] = set()
        self.w(rf"\section*{{{T('What each verdict rests on')}}}",
               rf"{{\footnotesize\color{{tagc}}{T('TREE_NOTE')}}}\par\medskip", r"{\small\setlength{\parskip}{1pt}")

        def label(r: str) -> str:
            e = rec.by_ref.get(r)
            if e is None:
                return self.ref(r)
            v = (e.value if e.value is not None and e.act != "mark" else
                 f"“{marked_words(e)}”" if e.act == "mark" else
                 "" if e.act == "quote" else e.body)
            tags = [t for t in self.tags.get(r, []) if t in ("withdrawn", "fell", "open")]
            return (self.ref(r) + rf"\enspace{{\footnotesize\color{{tagc}}{esc(e.act)}}}"
                    + (r"\enspace " + self.cut(self.sh(v), 60) if v else "")
                    + "".join(r"\warn{" + esc(self.t(t)) + "}" for t in tags))

        def walk(r: str, d: int) -> None:
            e = rec.by_ref.get(r)
            ind = rf"\par\noindent\hangindent={1.4 * d + 1.4:.1f}em\hspace*{{{1.4 * d:.1f}em}}"
            if d and r in shown:
                self.w(ind + label(r) + r"\enspace{\color{tagc}$\uparrow$}")
                return
            more = bool(e and e.rests and d >= depth)
            self.w(ind + (r"\textbf{" + label(r) + "}" if d == 0 else label(r))
                   + (rf"\enspace{{\footnotesize\color{{tagc}}(+{len(e.rests)} {T('further')})}}"
                      if more else ""))
            shown.add(r)
            if e is None or not e.rests or more:
                return
            for x in e.rests:
                walk(x, d + 1)

        for e in vs:
            walk(e.ref, 0)
            self.w(r"\par\medskip")
        self.w(r"\par}", "")

    def verdict_table(self) -> list[str]:
        """The verdicts on the record, one row each, and which values are open against
        each other. For the box headed For a person."""
        rec, R, T = self.rec, self.R, self.t
        vs = [e for e in rec.entries() if e.act in ("verdict", "settle")]
        if not vs:
            return []
        out = [rf"\textit{{{T('Verdicts on the record')}}}\par\nopagebreak",
               r"{\small\noindent\begin{tabular}{@{}lll>{\RaggedRight\arraybackslash}p{40mm}l@{}}\toprule",
               rf"{T('Who')} & {T('Kind')} & {T('Value')} & {T('Adopts')} & {T('Status')} \\ \midrule"]
        for e in vs:
            adopts = [r for r in e.rests if (x := rec.by_ref.get(r)) is not None and x.act == "verdict"]
            st = ", ".join(self.t(t) for t in self.tags.get(e.ref, [])
                           if t in ("withdrawn", "fell", "proposed", "stands", "open"))
            out.append(rf"{self.ref(e.ref)} & {T(e.kind)} & \textbf{{{self.cut(self.sh(e.value or ''), 28)}}} & "
                       rf"{self.refs(adopts) if adopts else '—'} & {esc(st)} \\")
        out.append(r"\bottomrule\end{tabular}\par}")
        both = [(a, b) for a, b, _ in R.open
                if rec.get(a).act in ("verdict", "settle") and rec.get(b).act in ("verdict", "settle")]
        if both:
            groups: list[tuple[str, list[str]]] = []
            for r in dict.fromkeys(x for p in both for x in p):
                v = rec.get(r).value or ""
                for g in groups:
                    if same_value(g[0], v):
                        g[1].append(r)
                        break
                else:
                    groups.append((v, [r]))
            out.append(r"\smallskip\noindent\textbf{" + T("Open against each other") + ":} " + " · ".join(
                rf"\textbf{{{self.cut(self.sh(v), 28)}}} ({', '.join(tt(self.names.get(rec.get(r).log, rec.get(r).log)) for r in rs)})"
                for v, rs in groups) + r"\par")
        return out

    # -- the document
    def case(self) -> None:
        """The case box: what the audit is about, from about.json beside the logs, if there is
        one. It is the author's description, not computed from the record, and says so."""
        f = self.folder / "about.json"
        if not f.exists():
            return
        a = json.loads(f.read_text(encoding="utf-8"))
        a = {**a, **a.get(self.lang, {})} if isinstance(a.get(self.lang), dict) else a
        T = self.t
        self.w(r"\begin{casebox}", rf"\textbf{{{T('The case')}}}"
               + (rf" \hfill{{\footnotesize\color{{tagc}}{esc(a['trial']).replace('′', chr(36) + chr(39) + chr(36))}}}" if a.get("trial") else "")
               + r"\par\smallskip")
        if a.get("sentence"):
            self.w(rf"\begin{{quote}}\itshape {esc(a['sentence'])}\end{{quote}}")
        self.w(r"\begin{description}[leftmargin=0pt,itemsep=3pt]")
        for k, lab in (("source", "Source"), ("about", "Why it is contested"),
                       ("setup", "What was done"), ("outcome", "Outcome"), ("taught", "What it showed")):
            if a.get(k):
                self.w(rf"\item[{T(lab)}:] {esc(a[k])}")
        self.w(r"\end{description}", rf"{{\footnotesize\color{{tagc}}{T('CASE_NOTE')}}}",
               r"\end{casebox}", "")

    def build(self) -> str:
        rec, R = self.rec, self.R
        name = self.folder.name
        when = _dt.date.today().isoformat()
        T = self.t
        self.w(PREAMBLE, rf"\renewcommand{{\agent}}{{{{\footnotesize\color{{tagc}}{T('agent')}}}}}",
               rf"\renewcommand{{\person}}{{{{\footnotesize\color{{tagc}}{T('person')}}}}}",
               rf"\renewcommand{{\lookshead}}{{{T('looks answering it')}}}",
               r"\usepackage{polyglossia}\setdefaultlanguage{swedish}" if self.lang == "sv" else "",
               r"\begin{document}",
               rf"\title{{{T('Audit')} \texttt{{{esc(name)}}}}}",
               rf"\date{{{T('Computed')} {when} {T('from the record. Not part of the record.')}}}",
               r"\author{}", r"\maketitle", r"\thispagestyle{empty}", "")
        self.case()

        # what was read
        self.w(rf"\section*{{{T('What was read')}}}",
               r"\begin{tabular}{@{}lllrll@{}}\toprule",
               rf"{T('Name')} & {T('Log')} & {T('Kind')} & {T('Entries')} & {T('Signed')} & {T('Head')} \\ \midrule")
        for log, es in rec.logs.items():
            kind = es[0].kind if es else ""
            signed = T("yes") if log in rec.signed else rf"\warn{{{T('no')}}}"
            heads = ", ".join(r"\hyperlink{" + anchor(rec.by_ref[h]) + "}{" + tt(h.split(":", 1)[1]) + "}"
                              if h in rec.by_ref else tt(h.split(":", 1)[1]) for h in R.heads.get(log, []))
            self.w(rf"\textbf{{{esc(self.names[log])}}} & {esc(log)} & {T(kind)} & {len(es)} & {signed} & {heads} \\")
        self.w(r"\bottomrule\end{tabular}", "",
               rf"{{\footnotesize\color{{tagc}}{T('REF_NOTE')}}}\par", "")
        if R.logs_not_read:
            self.w(r"\noindent " + T("Logs cited but not read") + ": " +
                   ", ".join(esc(x) for x in sorted(R.logs_not_read)) + ".\\par")
        if R.entries_not_read:
            self.w(r"\noindent " + T("Entries cited but not read") + ": " +
                   ", ".join(tt(x) for x in sorted(R.entries_not_read)) + ".\\par")
        for log, at, succ in R.forks:
            self.w(rf"\noindent\warn{{{T('fork')}}} {T('in')} {esc(log)} at {self.ref(at)}: "
                   rf"{self.refs(succ)}.\par")
        self.w("")
        self.glance()

        # the hand-over
        ho = self.handover()
        vt = self.verdict_table()
        self.w(r"\begin{handover}", rf"\textbf{{{T('For a person')}}}\par\smallskip", *vt)
        if vt and ho:
            self.w(r"\medskip")
        if ho:
            self.w(r"\begin{description}[leftmargin=0pt,itemsep=2pt]")
            for what, v in ho:
                self.w(rf"\item[{esc(what)}:] {v}")
            self.w(r"\end{description}")
        elif not vt:
            self.w(T("Nothing is waiting."))
        self.w(r"\end{handover}", "")
        self.trees()

        # verdicts first: what the audit concluded
        self.w(rf"\section{{{T('Verdicts')}}}")
        verdicts = self.of("verdict")
        mine = [e for e in verdicts if e.kind == "person"]
        theirs = [e for e in verdicts if e.kind == "agent"]
        if not verdicts:
            self.w(T("No verdict is on the record."), "")
        if mine:
            self.w(r"\subsection*{" + T("The audit's verdicts, by a person") + "}")
            for e in mine:
                self.w(self.item(e), "")
        settles = self.of("settle")
        if settles:
            self.w(rf"\subsection*{{{T('Settled')}}}")
            for e in settles:
                self.w(self.item(e), "")
        if theirs:
            self.w(rf"\subsection*{{{T('Proposed by agents')}}}")
            grouped = set()
            for key, rs in R.same_object.items():
                rs = [r for r in rs if r.startswith(tuple(f"{e.log}:" for e in theirs))
                      and rec.get(r).act == "verdict" and rec.get(r).kind == "agent"]
                if not key.startswith("verdict ") or len(rs) < 2:
                    continue
                o = key.split(" ", 1)[1]
                self.w(r"\noindent\textit{" + T("On one object,") + " " + esc(o) + r"}\par\nopagebreak")
                for r in rs:
                    self.w(self.item(rec.get(r)), "")
                    grouped.add(r)
            for e in theirs:
                if e.ref not in grouped:
                    self.w(self.item(e), "")

        self.section("The sentence", self.of("quote"))
        self.w(rf"\section{{{T('Terms and readings')}}}")
        for title, acts in (("Marked", ("mark",)), ("Precizations", ("precize",)),
                            ("Holders", ("holder",)), ("Decided, not found", ("decide",)), ("Does the truth value vary?", ("vary",)),
                            ("Properties", ("property",)), ("Recovered, granted, checked",
                                                            ("recover", "grant", "check", "grid"))):
            es = self.of(*acts)
            if not es:
                continue
            self.w(rf"\subsection*{{{T(title)}}}")
            if acts == ("precize",):
                by: dict[str, list[Entry]] = {}
                for e in es:
                    by.setdefault(e.narrows or "", []).append(e)
                for n, xs in by.items():
                    self.w(r"\noindent\textit{" + T("narrowing") + "} " + (self.ref(n) if n else T("nothing"))
                           + r"\par\nopagebreak")
                    for e in xs:
                        self.w(self.item(e), "")
            else:
                for e in es:
                    self.w(self.item(e), "")

        # evidence: each commit, with the looks that answer it
        self.w(rf"\section{{{T('Evidence')}}}")
        commits = self.of("commit")
        looks = self.of("look")
        shown = set()
        for c in commits:
            self.w(self.item(c), "")
            ans = [x for x in looks if any(a.ref == c.ref for a in x.answers)]
            if ans:
                self.w(r"\begin{answering}")
                for x in ans:
                    self.w(self.item(x), "")
                    shown.add(x.ref)
                self.w(r"\end{answering}", "")
        other = [x for x in looks if x.ref not in shown]
        if other:
            if commits:
                self.w(rf"\subsection*{{{T('Looks that answer no commit')}}}")
            for x in other:
                self.w(self.item(x), "")
        if not commits and not looks:
            self.w(T("No evidence is on the record."), "")

        # what came down
        self.w(rf"\section{{{T('Withdrawn and fallen')}}}")
        if not R.withdrawn and not R.fell:
            self.w(T("Nothing was withdrawn."), "")
        for e in self.of("withdraw"):
            why = R.grant_withdrawals.get(e.ref)
            self.w(self.item(e, rf"\field{{{T('grant')}}}{{{T('withdrawn ')}{esc(why)}}}" if why else ""), "")
        if R.fell:
            self.w(r"\begin{description}[leftmargin=1em,itemsep=1pt]")
            for r, ch in sorted(R.fell.items()):
                self.w(rf"\item[{self.ref(r)}] {T('fell, by')} " +
                       r" $\rightarrow$ ".join(self.ref(x) for x in ch))
            self.w(r"\end{description}")

        # the record itself
        self.w(r"\appendix", rf"\section{{{T('The record, entry by entry')}}}",
               T("RECORD_NOTE") + r"\par\medskip")
        for log, es in rec.logs.items():
            self.w(rf"\subsection*{{{esc(self.names[log])}\quad{{\mdseries {esc(log)}}}}}" if self.names[log] != log
                   else rf"\subsection*{{{esc(log)}}}",
                   r"\begin{longtable}{@{}>{\RaggedRight}p{14mm}p{15mm}p{21mm}>{\RaggedRight\arraybackslash}p{\dimexpr\linewidth-58mm-6\tabcolsep}@{}}",
                   rf"\toprule {T('Id')} & {T('Act')} & {T('Hash')} & {T('Body')} \\ \midrule \endhead",
                   r"\bottomrule \endfoot")
            for e in es:
                sig = "" if log in rec.signed else rf"\newline\warn{{{T('unsigned')}}}"
                body = esc(e.body)
                if e.act in ("verdict", "vary", "holder", "property", "decide"):
                    body = rf"\textit{{{esc(e.value)}}}. " + body
                self.w(rf"\hypertarget{{{anchor(e)}}}{{{tt(e.id)}}} & {esc(e.act)} & "
                       rf"\texttt{{\footnotesize {e.hash[:12]}}}{sig} & "
                       rf"{{\footnotesize {body}}} \\")
            self.w(r"\end{longtable}")
        self.w(r"\end{document}")
        doc = "\n".join(self.out) + "\n"
        return doc.replace("“", "”") if self.lang == "sv" else doc   # Swedish: ” on both sides


PREAMBLE = r"""\documentclass[10pt,a4paper]{article}
\usepackage[margin=22mm]{geometry}
\usepackage{fontspec}
\IfFontExistsTF{FiraSans-Regular.otf}{%
  \setmainfont{FiraSans-Regular.otf}[BoldFont=FiraSans-Medium.otf,
    ItalicFont=FiraSans-Italic.otf, BoldItalicFont=FiraSans-MediumItalic.otf]
  \setmonofont{FiraMono-Regular.otf}[Scale=MatchLowercase]}{}
\usepackage{amssymb}\usepackage{newunicodechar}
\newunicodechar{≺}{\ensuremath{\prec}}\newunicodechar{→}{\ensuremath{\rightarrow}}
\newunicodechar{⊥}{\ensuremath{\perp}}\newunicodechar{≠}{\ensuremath{\neq}}
\newunicodechar{≤}{\ensuremath{\leq}}\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{₀}{\textsubscript{0}}\newunicodechar{₁}{\textsubscript{1}}
\newunicodechar{₂}{\textsubscript{2}}\newunicodechar{₃}{\textsubscript{3}}
\newunicodechar{₄}{\textsubscript{4}}\newunicodechar{₅}{\textsubscript{5}}
\usepackage{booktabs,longtable,array,enumitem,xcolor}
\usepackage[framemethod=default]{mdframed}
\usepackage[colorlinks,linkcolor=linkc,urlcolor=linkc,citecolor=linkc]{hyperref}
\definecolor{linkc}{rgb}{0.12,0.30,0.55}
\usepackage{ragged2e}
\setlength{\emergencystretch}{3em}  % long tt refs: let a line fall short, not run over
\linespread{1.15}
\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}
\definecolor{tagc}{gray}{0.40}\definecolor{warnc}{rgb}{0.70,0.15,0.10}
\definecolor{boxc}{rgb}{0.96,0.95,0.91}\definecolor{rulec}{gray}{0.75}
\newcommand{\etag}[1]{\,{\footnotesize\color{tagc}[#1]}}
\newcommand{\warn}[1]{\,{\footnotesize\color{warnc}[#1]}}
\newcommand{\agent}{{\footnotesize\color{tagc}agent}}
\newcommand{\person}{{\footnotesize\color{tagc}person}}
\newcommand{\entryhead}[3]{\par\needspace{3\baselineskip}\noindent\textbf{#1}\enspace#2#3\par\nopagebreak}
\newcommand{\entrybody}[1]{\begin{RaggedRight}\leftskip=1em #1\par\end{RaggedRight}\nopagebreak}
\newcommand{\field}[2]{\par\noindent\hspace*{1em}\parbox[t]{5.5em}{\leavevmode\footnotesize\color{tagc}\strut#1}%
  \parbox[t]{\dimexpr\linewidth-6.5em}{\RaggedRight\small #2\strut}}
\newcommand{\entryend}{\par\smallskip}
\newcommand{\lookshead}{looks answering it}
\newenvironment{answering}{\begin{list}{}{\leftmargin=1.5em}\item\relax
  \footnotesize\textit{\lookshead}\normalsize\par}{\end{list}}
\newenvironment{handover}{\begin{mdframed}[backgroundcolor=boxc,linecolor=rulec,
  innertopmargin=8pt,innerbottommargin=8pt]\RaggedRight}{\end{mdframed}}
\newenvironment{casebox}{\begin{mdframed}[linecolor=rulec,linewidth=0.6pt,
  innertopmargin=8pt,innerbottommargin=8pt]\RaggedRight}{\end{mdframed}}
\usepackage{needspace}
\usepackage{titlesec}
\titleformat{\section}{\large\bfseries}{\thesection}{0.8em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{0.8em}{}
\titlespacing*{\section}{0pt}{14pt}{4pt}
\titlespacing*{\subsection}{0pt}{10pt}{2pt}
\renewcommand{\maketitle}{{\noindent\LARGE\bfseries\csname @title\endcsname\par
  \smallskip\noindent\normalsize\color{tagc}\csname @date\endcsname\par\bigskip}}
"""


# ---------------------------------------------------------------------------- compile

def engine() -> list[str] | None:
    for name, args in (("tectonic", ["-X", "compile"]), ("lualatex", ["-interaction=nonstopmode"]),
                       ("xelatex", ["-interaction=nonstopmode"])):
        p = shutil.which(name) or (f"/opt/homebrew/bin/{name}"
                                   if Path(f"/opt/homebrew/bin/{name}").exists() else None)
        if p:
            return [p, *args]
    return None


def render(folder: Path, out: Path, lang: str = "en") -> dict:
    """Write <out>/<audit>.tex and, if an engine is found, compile it. Returns the paths,
    or the tail of the log if compiling failed."""
    folder, out = Path(folder), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    stem = folder.name + ("" if lang == "en" else f".{lang}")
    tex = out / f"{stem}.tex"
    tex.write_text(Doc(folder, lang).build(), encoding="utf-8")
    res = {"tex": str(tex)}
    cmd = engine()
    if cmd is None:
        res["pdf"] = None
        res["note"] = "no TeX engine found (tectonic, lualatex or xelatex); the .tex is written"
        return res
    runs = 1 if "tectonic" in cmd[0] else 2   # tectonic reruns by itself
    for _ in range(runs):
        p = subprocess.run([*cmd, tex.name], cwd=out, capture_output=True, text=True)
    pdf = out / f"{stem}.pdf"
    if p.returncode != 0 or not pdf.exists():
        res["pdf"] = None
        res["error"] = (p.stdout + p.stderr)[-2000:]
    else:
        res["pdf"] = str(pdf)
    return res


if __name__ == "__main__":
    args = sys.argv[1:]
    lang = "en"
    if "--lang" in args:
        i = args.index("--lang")
        lang = args[i + 1]
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    r = render(Path(args[0]), Path(args[1] if len(args) > 1 else "out"), lang)
    for k, v in r.items():
        print(f"{k}: {v}")
    sys.exit(0 if r.get("pdf") or "note" in r else 1)
