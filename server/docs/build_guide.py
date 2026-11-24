"""Build the guide: what the audit record is for, how to read a report, and the cases.

  .venv/bin/python docs/build_guide.py [OUT_DIR]      (default: out/)

Part I is general and belongs with the server. Part II is written from the about.json
files in data/<audit>/, the same text the reports show in their case box, so a case is
described in one place only. The guide is the author's text, not computed from any record.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit.render import engine, esc  # noqa: E402

PART_ONE = r"""
\part*{I\quad Using the audit record}
\addcontentsline{toc}{part}{I\quad Using the audit record}

\section{The idea}

A sentence can be argued over for a long time without anyone noticing that the two sides
mean different things by one of its words. \emph{Saying What You Mean} gives a card for
checking that: mark the word the sentence turns on, write down its readings, see whether
the sentence is true under one and false under another, find who holds which reading, and
only then say what kind of disagreement it is.

The audit record lets agents do much of this work, and keeps a person responsible for the
part that needs one. Three ideas carry it.

\begin{description}[leftmargin=1.2em,style=nextline]
\item[Agents analyse, people decide.] An agent may quote, mark, list readings, look at
  sources and propose a verdict. It may not say who holds a reading, accept a norm,
  settle a question, or decide what a sentence is to mean. Those acts need a person, and the server refuses them from an agent.
\item[The record shows who saw what.] Every author writes to their own log. Each entry is
  signed and chained to the one before it, so nothing can be changed afterwards without
  showing. A look must name the lines it read, and a conclusion must name what it rests on.
  Anyone can later check what a verdict was based on, and whether that was ever read.
\item[Reports are computed, not written.] A report is worked out from the logs each time it
  is asked for, and is never stored. It shows what is open, what was proposed, what stands
  and what fell, but it never decides anything itself.
\end{description}

\section{What happens in an audit}

\begin{enumerate}[leftmargin=1.5em,itemsep=2pt]
\item An agent is given a sentence and its source, and reads the card
  (\texttt{audit://card}).
\item It may \emph{commit} first: say what would change its mind before it reads the
  evidence, or what it already knows about the case.
\item It works through the card with \texttt{write}: \emph{quote}, \emph{mark},
  \emph{precize} (a reading), \emph{vary} (does the truth value change?), \emph{look}
  (with the lines read through \texttt{read}), \emph{property}, \emph{recover}, and a
  proposed \emph{verdict}.
\item Where the card needs a person, it stops and \emph{closes} its log. The report's box
  \emph{For a person} lists what is waiting.
\item A person writes under their own key: \emph{holder} (who holds which reading),
  \emph{grant} (accepts a norm), their own \emph{verdict}, \emph{settle}. A holder
  who cannot say which reading they meant is written as a \emph{holder} with the value
  \emph{nescio}, naming the readings in doubt. A person may then \emph{decide} one of
  them, and the report lists it as decided, not found.
  A person can also \emph{withdraw}, and what rested on the withdrawn entry falls with it.
\end{enumerate}

The verdicts are those of the card.

\begin{description}[leftmargin=2.2em,labelwidth=1.6em,labelsep=0.6em,itemsep=1pt,font=\normalfont\bfseries]
\item[1a\label{v:1a}] Pseudo-disagreement: the sides only seem to disagree.
\item[1b\label{v:1b}] Pseudo-agreement: the sides only seem to agree.
\item[2\label{v:2}] Real disagreement: same facts, same readings, different conclusion.
\item[3\label{v:3}] Equivocation: the sentence slides between readings.
\item[4\label{v:4}] Rule--property divergence: the rule is kept but the property it was
  meant to secure is not.
\item[5\label{v:5}] Pseudo-alternatives: the options offered are not all there are.
\item[none\label{v:none}] No verdict can be given yet, often with the \emph{frame}, one of
  the above, that would fit once a case appears.
\end{description}

\section{How to read a report}

\begin{description}[leftmargin=1.2em,style=nextline]
\item[The case.] If the audit folder has an \texttt{about.json}, the report opens with a
  box describing the case. It is the author's text, not computed, and says so.
\item[What was read.] One row per log: agent or person, number of entries, whether the
  signatures verify, and where each log ends.
\item[For a person.] What waits for a human: \emph{open} questions where verdicts differ,
  commits that no look has met, readings without a named holder, answers to the same
  question by different authors, and \emph{drift} (a reading narrowed after a look bore on
  it).
\item[Verdicts.] Settled verdicts first, then those proposed by agents. A verdict
  \emph{stands} while everything it rests on stands.
\item[Terms and readings, evidence.] What was marked, the readings, who holds them,
  whether the truth value varies, and each look with the lines it read.
\item[Withdrawn and fallen.] What a person took back, and what fell because of it.
\item[The record, entry by entry.] Every entry in order, with its hash and whether it is
  signed.
\end{description}

\section{What the record does not do}

It does not judge whether an analysis is good. Two agents can agree and both be wrong, and
the report shows only that they agree. It cannot see what an agent read outside the server,
or what it knew before it started (60); a commit can make prior knowledge visible, but cannot
remove it (58). Readings in different logs are not matched by meaning, only by identical words (56).
And it was tried on ten sentences by one author, mostly with one model.

Nor does it correct anything. An entry is signed and chained to the next, so a slip stays
exactly as it was written; changing one letter would break the signature and every link
after it. The checks look at quotations, not at an author's own prose. In the Education Act
audit, for instance, the mark \texttt{g2 (for A):m1} says \emph{Uneningheten} where Swedish
has \emph{oenigheten} (the disagreement), and one of its clauses lacks a verb. The report
shows the entry as written. A correction, if one is wanted, is a new entry that says so.

\section{Writing a case description}

To give an audit a case box, put \texttt{about.json} in its folder. Every field is
optional: \texttt{sentence}, \texttt{source}, \texttt{about} (why it is contested),
\texttt{setup} (what was done), \texttt{outcome}, \texttt{taught} (what it showed),
\texttt{trial}. A key for a language, such as \texttt{"sv": \{...\}}, overrides fields
when the report is rendered in that language. The file is not a log and the record
ignores it.
"""

PART_TWO_INTRO = r"""
\part*{II\quad The cases}
\addcontentsline{toc}{part}{II\quad The cases}

These are the ten audits behind the working paper \emph{Who saw what}. Each was run to find
out where the record breaks, and most of them broke it somewhere; the numbers in brackets
are the findings in \texttt{FINDINGS.md}, listed with their titles at the end. Numbers and verdict codes are links. Persons named as fictional had stances stipulated
by the author and are nobody's judgment. Sources are described rather than quoted, apart
from the audited sentence itself.
"""

VERDICT = r"(1a|1b|[2-5])"
LEAD = r"\b((?:verdict|verdicts|frame|frames|proposed|gave|named|and|or)[,:]? )"


def link(text: str, cited: set) -> str:
    """Escaped text with finding numbers and verdict codes made into links."""
    def fnum(m):
        nums = re.findall(r"\d+", m.group(1))
        cited.update(int(n) for n in nums)
        return "(" + ", ".join(rf"\hyperref[f:{n}]{{{n}}}" for n in nums) + ")"
    text = re.sub(r"\((\d{1,2}(?:, \d{1,2})*)\)", fnum, text)
    text = re.sub(LEAD + VERDICT + r"\b",
                  lambda m: m.group(1) + rf"\hyperref[v:{m.group(2)}]{{{m.group(2)}}}", text)
    return re.sub(r"\b(1a|1b|[2-5])(?=, (?:pseudo|real|equivocation|rule))",
                  lambda m: rf"\hyperref[v:{m.group(1)}]{{{m.group(1)}}}", text)


def findings() -> dict:
    """Number -> bold title, from FINDINGS.md."""
    md = (ROOT / "FINDINGS.md").read_text(encoding="utf-8")
    return {int(n): t.replace("\n", " ") for n, t in
            re.findall(r"^(\d+)\. \*\*(.+?)\*\*", md, flags=re.M | re.S)}


def title_tex(t: str) -> str:
    parts = t.split("`")
    return "".join(rf"\texttt{{{esc(x)}}}" if i % 2 else esc(x) for i, x in enumerate(parts))


FIELDS = (("source", "Source"), ("about", "Why it is contested"), ("setup", "What was done"),
          ("outcome", "Outcome"), ("taught", "What it showed"))


def case(name: str, a: dict, cited: set) -> str:
    out = [rf"\section{{{esc(a.get('trial', name)).replace('′', chr(36) + chr(39) + chr(36))}}}",
           rf"{{\footnotesize\color{{tagc}}\texttt{{{esc(name)}}}}}\par\smallskip"]
    if a.get("sentence"):
        out.append(rf"\begin{{quote}}\itshape {esc(a['sentence'])}\end{{quote}}")
    out.append(r"\begin{description}[leftmargin=0pt,itemsep=4pt]")
    out += [rf"\item[{lab}:] {link(esc(a[k]), cited)}" for k, lab in FIELDS if a.get(k)]
    out.append(r"\end{description}")
    return "\n".join(out)


PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[a4paper,margin=2.4cm]{geometry}
\usepackage{fontspec}
\IfFontExistsTF{FiraSans-Regular.otf}{%
  \setmainfont{FiraSans-Regular.otf}[BoldFont=FiraSans-Medium.otf,
    ItalicFont=FiraSans-Italic.otf, BoldItalicFont=FiraSans-MediumItalic.otf]
  \setmonofont{FiraMono-Regular.otf}[Scale=MatchLowercase]}{}
\usepackage{xcolor}
\definecolor{tagc}{HTML}{6B6B6B}
\usepackage{enumitem}
\usepackage{ragged2e}
\usepackage{titlesec}
\titleformat{\section}{\large\bfseries}{}{0em}{}
\titlespacing*{\section}{0pt}{16pt}{6pt}
\titleformat{\part}[display]{\LARGE\bfseries}{}{0pt}{}
\setlength{\parskip}{4pt}\setlength{\parindent}{0pt}
\definecolor{linkc}{rgb}{0.12,0.30,0.55}
\usepackage[colorlinks,linkcolor=linkc,urlcolor=linkc]{hyperref}
\begin{document}\RaggedRight
{\noindent\LARGE\bfseries The audit record: a guide\par}
\smallskip{\color{tagc}What it is for, how to read a report, and the ten cases behind
\emph{Who saw what}. Written by the author; not computed from any record.\par}
\bigskip
\tableofcontents
\clearpage
"""


def main(out="out"):
    out = Path(out) if Path(out).is_absolute() else ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    cases = []
    for f in sorted((ROOT / "data").glob("*/about.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        cases.append((a.get("order", 99), f.parent.name, a))
    cited = {33, 56, 58, 59, 60}   # those Part I cites
    body = "\n\\clearpage\n".join(case(n, a, cited) for _, n, a in sorted(cases))
    F = findings()
    body += ("\n\\clearpage\n\\section{The findings cited}\n"
             "Titles as in \\texttt{FINDINGS.md}, where each finding is given in full.\n\n"
             "\\begin{description}[leftmargin=2.4em,labelwidth=1.8em,labelsep=0.6em,"
             "itemsep=2pt,font=\\normalfont\\bfseries]\n"
             + "\n".join(rf"\item[{n}\label{{f:{n}}}] {title_tex(F.get(n, '(missing)'))}"
                          for n in sorted(cited)) + "\n\\end{description}\n")
    tex = out / "guide.tex"
    tex.write_text(PREAMBLE + PART_ONE + "\n\\clearpage\n" + PART_TWO_INTRO + "\n" + body
                   + "\n\\end{document}\n", encoding="utf-8")
    cmd = engine()
    if cmd is None:
        print("no TeX engine; wrote", tex)
        return 0
    for _ in range(1 if "tectonic" in cmd[0] else 2):
        r = subprocess.run([*cmd, tex.name], cwd=out, capture_output=True, text=True)
    print(tex.with_suffix(".pdf") if r.returncode == 0 else r.stdout[-2000:] + r.stderr[-2000:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
