# precize

An audit record where agents stop and people decide.

An agent built on a language model can do much of the work of auditing a contested word:
quote the sentence, mark the word it turns on, list its readings, and propose what kind of
disagreement there is. Some steps need a person. To say who holds a reading is a claim
about people, and to settle what a law means is a judgement. This repository holds a
server that keeps a record of such audits. Agents call it over the Model Context Protocol
(MCP). Each author writes to their own signed log, and every entry names what it rests on.
The server refuses from an agent the acts that need a person, and it computes its reports
from the logs each time, never storing them.

The procedure comes from *Saying What You Mean* (Lonnert 2026), after Arne Naess. The
record comes from *A Calculus of Representation*, vol. IV.

## Contents

- `summary/`: *Who saw what: a summary*, a four-page account of the design and the trials,
  as a PDF.
- `server/`: the MCP server, its library, its tests, the trial records and the findings.
  See `server/README.md` to run it.
- `examples/`: the report of each trial in `server/data/`, rendered to PDF in English and in
  Swedish (`.sv.pdf`), and `guide.pdf`, on how to read a report. They are made from the logs
  and can be made again; see `server/README.md`. `live-allotment.pdf` is the report of a
  single run of the live agent page (`server/live/`) on two short fictional texts, with no
  person writing: it shows what the server makes of an agent's part alone, up to a verdict
  that is only proposed.

The findings and the trial notes were written in the author's working tree. Where they point
to `../manual/`, `../paper/` or `../sources/`, those files are not in this repository. The
source texts the trials read are not included: supply your own under `sources/`.

The logs of trial 5a are left out, because they quote a copyrighted article (Wood and
Porter 2019) at length. FINDINGS.md still describes the trial, and the two tests that
read its logs skip.

The full paper, *Who saw what: An audit record where agents stop and people decide*, is
deposited on Humanities Commons: [doi:10.17613/vpv2r-1z781](https://doi.org/10.17613/vpv2r-1z781).

## License

The code is under the MIT License (`LICENSE`). The summary and the other texts are under
Creative Commons Attribution 4.0 (CC BY 4.0).
