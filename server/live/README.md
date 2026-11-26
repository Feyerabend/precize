# A live agent

`live/` is a page where a visitor runs an agent on a sentence of their own. They give a
text, name the sentence (T₀) and its line, and a Claude model, called with the visitor's own
API key, audits it by the card. It quotes the sentence, marks the word the claim turns on,
commits to what would change its mind, reads the text, spells out the readings and proposes
a verdict. It stops where a person is needed (holder, grant, settle, the audit's verdict).
The run then goes to the playground, where the visitor writes as that person.

The page runs in the browser alone. There is no server of ours and no MCP: the page calls
the Claude API directly and runs the tools itself.

## The key and the cost

- The visitor types their key into the page. It is kept in memory only: not in
  `localStorage` or a cookie, and not in the downloaded run or transcript. It is sent only
  to `api.anthropic.com`, through the Anthropic TypeScript SDK in browser mode. Reloading
  the page drops it.
- Every turn is billed to that key. A run is typically 20 to 40 turns. The page has a turn
  limit (40 by default) and a Stop button. The system prompt (the instructions and the card)
  is cached, so later turns cost less than the first.
- Only what the agent fetches with `read` goes to the model, a slice at a time, but the
  visitor should not paste a text they would not send to an API.

## Running it

The page needs `../playground/` next to it, so serve the folder above:

```bash
cd mcp-audit && python3 -m http.server 8766 --bind 127.0.0.1
```

Then open http://127.0.0.1:8766/live/. Opening `index.html` as a file does not work: the
browser blocks the module and the API call from `file://`.

To try it without a text of your own, press **Load the example**. It loads two short
fictional texts in `examples/`: an allotment society's rules, where line 15 reads
"Members shall not keep animals or poultry on their plot unless the committee agrees", and
committee minutes that bear on how far "unless" reaches.

## What the agent gets

The same texts an agent gets from the MCP server, word for word: the server's
instructions, the descriptions of `write`, `read`, `report` and `entry`, and the card. They
come from `server.py` and `card.txt` through `export.py`, which writes `prompt.js`. After
either file changes, remake it:

```bash
python3 live/export.py
```

The page adds a short preamble (which documents there are; the `audit` argument is left out,
since there is one audit) and the brief. The brief is the one in
`trials/HOW-TO-RUN.md`, for the evidence run or the drafting run, optionally with a line
asking for Swedish entry bodies. The page shows it before the run starts.

The model is Opus 5.5, Sonnet 5.5 or Haiku 5.5, with an effort setting (not for Haiku). Opus
and Sonnet are called with server-side fallbacks on: if the chosen model is overloaded the
API may answer with another one, and the run's stats say which model answered.

## The rules

The tools write through the same checks as the server, ported to JavaScript:

- `../playground/audit.js` is the record, as `audit/store.py`: hashes, the chain, citation,
  the act rules (quote before mark, readings before a verdict, and so on), and the report.
- `ledger.js` is `audit/fetch.py`: what was fetched, and when. Words an agent puts in
  quotation marks, in an entry that cites what the log fetched, must be in that text
  (verbatim); an entry that cites nothing is not checked, as on the server. A look must not cite a passage fetched before the commit it
  answers (commit-first). A commit written after reading stands, with a note, and the
  report lists it under `committed_after_reading`. A source that was never fetched is
  listed under `unfetched`.
- `tools.js` is the tools: one agent log, `g1 (for <person>)`. A write of a kind other than
  `agent` is refused, and a holder, grant, settle or decide from an agent is refused (rule
  `person`), as on the server. A precize must name what it narrows. Each entry is signed with
  an Ed25519 key made in the page.

What is refused is shown in the trace with its rule, and goes back to the model as the
server's message, so the agent can correct itself.

## Into the playground

When the agent stops, **Take your turn in the playground** keeps the run in
`sessionStorage` and opens `../playground/#live`, which picks it as the first case. There the
visitor reads the agent's log and writes as the person: who holds a reading, which they go
by, or that they cannot tell, and the audit's verdict.

**Download the run** saves `live-run.json`: the log, its public key, and what the agent
fetched (sources and when, not the text). The playground loads it again with **Load a run**.
**Download the transcript** saves every message sent to and from the model.

## Testing

```bash
node live/check.mjs
```

It needs `.venv` (or the Python to use in `PY`). A scripted agent, with no model, runs the tools on the example: a wrong
quote, a holder, a precize without `narrows`, a person's kind, another log, a look on what
was read before the commit, a cite of nothing and a write after close must each be refused
with the server's rule. The log, its key and the fetch ledger are then written as the server
writes them, and Python (`audit.store`, `audit.fetch`, `audit.report`) must load them, check
the hashes and signatures, and give the same report, `unfetched` and
`committed_after_reading` included. It also checks `plain()` and `unquoted()` against
`fetch.py`.

## The files

| File | What it is |
| --- | --- |
| `index.html` | The page: the key, the text, the sentence, the run |
| `agent.js` | The loop: calls the model, runs the tools, shows the trace |
| `tools.js` | `write`, `read`, `report`, `entry`, the brief and the system prompt |
| `ledger.js` | The fetch ledger: verbatim, commit-first, unfetched, committed after reading |
| `prompt.js` | Made by `export.py`: the server's instructions, tool texts and the card |
| `export.py` | Reads `server.py` (without running it) and `card.txt`, writes `prompt.js` |
| `live.css` | Additions to `../playground/style.css` |
| `check.mjs` | The test above |
| `examples/` | The two fictional example texts |

## What it is not

- It is not the MCP server. The tools are a port and the checks are kept in step by
  `check.mjs`, but the server stays the reference. A log written here loads in the server.
- One agent log per run. Several runs, and logs from other people, are for the server.
- It reads only the documents given, by name and line. It does not fetch from the web.
- It does not render the record as the paper's appendix does; for that, load the log in the
  server and use `render`.

## An example of what the server makes of a run

`data/live-allotment/` is one run of the example, downloaded from the page and written as
the server writes it: the log, its public key and what was fetched (Claude Opus 5.5, effort
high, the evidence brief, 16 turns, 29 entries). `about.json` adds the case box. The server
renders it as any trial (`out/live-allotment.pdf`, and `.sv.pdf` with Swedish labels):

```bash
.venv/bin/python -m audit.render data/live-allotment out
```

No person wrote in it, so the report shows the agent's part alone: the marks, the commits
written before the reading, the readings, the looks and what is absent, the grid, a question
for V, and a verdict shown as proposed, which no person has answered. The rows for holders,
grants and the audit's verdict are what V would fill in the playground.
