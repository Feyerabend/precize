# audit-record

A small MCP server for the audit record described in the paper *Who saw what*, after
*Saying What You Mean* and Volume IV of *A Calculus of Representation*. A prototype:
it computes the reports of the hand tests, and nothing has been proved.

- `audit/`: the library. `record.py` holds entries, logs (one JSON Lines file per author,
  hash-chained), the write-time rules, merging and forks. `reports.py` computes the
  reports, which are never stored.
- `server.py`: the MCP wrapper. Tools: `write`, `report`, `entry`, `merge`, `audits`, `render`.
  Resources: `audit://card`, `audit://{audit}/log/{log}`. Prompts: `audit_sentence`,
  `audit_argument`.
- `docs/build_guide.py`: builds `out/guide.pdf`. Part I says what the record is for and how
  to read a report; Part II describes the cases, from `data/<audit>/about.json`. The same
  file gives each report a case box. It is the author's text, not part of the record.
- `tests/`: the hand tests as fixtures. `FINDINGS.md` says where they and the server part.

## The acts

The acts follow the card. Sixteen do the audit, and three keep the record.

| Act | What it records | Must cite |
|-----|-----------------|-----------|
| `quote` | the sentence, exactly as uttered | a source passage |
| `mark` | the word the sentence turns on | a quote |
| `precize` | one reading of the word, with cases | the mark, reading or look it narrows |
| `vary` | whether the truth of the sentence varies across the readings | a mark |
| `holder` | who reads the word one way | a precize |
| `grid` | two marked words, in all four combinations | two marks |
| `property` | what a reading is meant to secure, as a question about the case | a precize |
| `recover` | a norm an argument needs but does not state | the argument's quote |
| `grant` | a party accepts that norm | a recover |
| `check` | an attack built on the granted norm | a grant |
| `commit` | what would change the author's mind | what it is about |
| `look` | evidence examined | a source passage |
| `verdict` | one of the five verdicts, or none | what it rests on, and its object |
| `withdraw` | the author takes back an entry of their own | that entry |
| `settle` | a person closes an open question | both sides of it |
| `decide` | a person chooses a reading, past a nescio | the nescio it answers |
| `close`, `ask`, `show` | end a log; ask for its head; hand it over | — |

## Running

```bash
python3 -m venv .venv && .venv/bin/pip install mcp pytest
.venv/bin/python -m pytest -q
```

`.mcp.json` registers the server for Claude Code sessions opened in this folder. It holds
absolute paths and is not in the repository: copy `.mcp.json.example` to `.mcp.json` and
replace `/path/to/mcp-audit` with this folder's path.

Four environment variables move what the server reads and writes. `AUDIT_SOURCES` is the
folder `read` may fetch from (default: the folder above this one). `AUDIT_DATA` holds the
logs (default `data/`). `AUDIT_OUT` takes the rendered reports (default `out/`).
`AUDIT_CARD` is the procedure card served as `audit://card` (default `card.txt`, the
one-page procedure from *Saying What You Mean*, Appendix A).

## Reports as PDF

```bash
.venv/bin/python -m audit.render data/yates-tangible-object out
.venv/bin/python -m audit.render data/yates-tangible-object out --lang sv
.venv/bin/python docs/build_guide.py out
```

The first writes `out/yates-tangible-object.tex`, made from the logs each time, and compiles
it to PDF if tectonic, lualatex or xelatex is installed. `--lang sv` gives the labels in
Swedish. The third builds the guide to reading a report. The server's `render` tool does the
same as the first. `../examples/` holds the PDFs rendered from `data/`.
