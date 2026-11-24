# How to run a trial

Written 2026-11-20 so that a new session need not work this out again. Read this, then
`FINDINGS.md` from "The live trial" on, and nothing else is needed to run one.

## The rules

- **A new trial gets a new audit folder** (`data/<audit>/`). Logs are signed and chained;
  never edit or append to an old trial's logs to "redo" it.
- **Runs are blind to each other.** Each run gets its own log name (`g1 (for A)`,
  `g2 (for A)`, …) and is told not to read the other's log or other audits.
- **Agents never write person-only acts** (holder, grant, settle, the audit's verdict).
  The server refuses them; the brief says so too.
- **Persons, if any, are written by script**, not by an agent through the server, under
  their own keys in `keys-local/` (never published). Real persons write themselves.
- Nothing is committed or published.

## 1. Start the runs

Each run is a separate Claude Code session started from the coordinating session with
`mcp__ccd_session__start_session`:

- `initiation`: `"user_asked"`, `context`: `"fresh"`, `use_worktree`: `false`
- `cwd`: the absolute path of `mcp-audit/`. The `.mcp.json` there
  gives the session the server `audit-record` (tools `write`, `read`, `report`, `entry`,
  `audits`) with `AUDIT_DATA` set to `data/`.
- `model`: leave out for the coordinating model; give another (e.g. a Sonnet id) when the
  trial compares models, as in trial 8.
- Mark a chapter first when starting two at once.

The coordinating session itself does not have the `audit-record` tools (its folder is the
parent); it reads the results from `data/` with Python.

## 2. The brief

Keep briefs identical across runs except for the log name and the run's role. Do not
hint at what the trial is testing. Template (trial 7's, which worked):

> You are agent run `g1 (for A)` in the audit `<audit>` on the MCP server `audit-record`
> (tools `write`, `read`, `report`, `entry`). First read the server's instructions, the
> `write` and `read` tool descriptions, and the card (resource `audit://card`, or
> `manual/body/08-the-procedure-on-one-page.tex` via `read`). Read nothing else in
> `manual/`. [Has it been audited before? Say so, and forbid reading that audit.]
>
> T₀ is <source, place>, in `sources/<file>`, line <n>: "<sentence>". [Notes on the line.]
>
> [Language: "Write every entry body in Swedish. Act names, field names and verdict
> values stay as the server defines them. Quotes stay verbatim."]
>
> You are the evidence run. Steps: 1. Quote T₀, fetching only line <n> at first.
> 2. Mark the term(s) the claim turns on; you decide which. 3. BEFORE fetching more,
> write your commit: what would change your mind. 4. Fetch through `read` what you need;
> cite the `source` it returns; record what is absent. 5. Precize the readings (with
> `narrows`). Look, then propose a verdict with your quote as the object.
>
> (Or, the drafting run: 1. Quote T₀. 2. Mark. 3. Vary and precize. 4. Name the
> property, if any. 5. Propose a verdict.)
>
> Stop at holder, grant, settle and the audit's verdict; those are for person A. End with
> `act='close'`. Edit no files; write only through the server. When done, report in a few
> lines, in English: what you wrote; anything refused, and why; anything unclear in the
> instructions.

`background` (needs 80+ characters): which trial this is, what the server is, that the
other run works in parallel and must not be read.

## 3. While they run

Do not poll. The app continues the coordinating session when the runs end their turns.
A run cut off by a usage limit can be told to close (trial 5 did; say so in FINDINGS).

## 4. After they close

```bash
cd mcp-audit
.venv/bin/python -m audit.render data/<audit> out              # add --lang sv for Swedish
.venv/bin/python -m pytest -q
```

List the entries quickly:

```bash
.venv/bin/python -c "
import json,glob
for f in sorted(glob.glob('data/<audit>/*.jsonl')):
    print('==',f)
    for l in open(f):
        e=json.loads(l); print(e['id'],e['act'],e.get('value'),'|',str(e.get('body'))[:120])"
```

Check what the report says against the logs before believing it (finding 63 was a
report flag nobody had checked).

## 5. Persons (optional)

Copy `trials/yates-fiktiva/` to `trials/<name>/`, write the persons' entries in
`entries.json` (each body says "Fictional person X … (stipulated stance)"), then

```bash
.venv/bin/python trials/<name>/write_persons.py data/<audit> keys-local
```

## 6. Record it

- `data/<audit>/about.json`: sentence, source, about, setup, outcome, taught, trial,
  order (and `"sv"` overrides). The guide (`docs/build_guide.py`) and the report's case
  box read it.
- `FINDINGS.md`: a section for the trial, new numbered findings, and a "Fixed" list for
  any code change, with tests.
- `../paper/audit-record-outline.md` §6.1: a row in the trials table.
