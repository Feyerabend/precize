# Results: the audit trials with models other than Claude

Run 2026-11-24 on the author's Mac (Apple M5, macOS 27.0), from `TASK.md`. Two audits,
`data/yates-models/` (trial 8 again) and `data/snell-models/` (trial 12 again). The briefs
are in `mcp-audit/trials/models-2026-11/brief-*.md`. The server traffic is in
`traffic-*.jsonl` in the same folder, written by `mcp_tee.py`; `traffic.py` summarises it.
Every time is UTC.

## Limits chosen

- **Local models only.** The author chose this after the one cloud run (m2, Kimi K3.1 Pro)
  stopped at the Free plan's limit. No run here used a large model. The local models are
  8–14B parameters, quantised to 4 bits.
- **One host.** Every run went through LM Studio Bionic. Its own tool layer sits between
  the model and the server: tools load lazily, arguments pass through a `params_json`
  wrapper, and resources are never listed. Host and model are confounded throughout,
  and the Claude runs they are compared with ran in Claude Code.
- **One run per model per trial,** with no repeats. A failed run was recorded as it
  stood and was not rerun under another name.
- **Fewer models than planned.** Gemma and Ministral ran both trials. Kimi ran only the
  start of Yates. DeepSeek R1 ran only Yates, as a check of tool calling.
- **One intervention.** In Snell, m3 stopped to ask a question, and was told "Proceed with
  the brief as written." Nothing else was said to any run. Yates m1 was stopped by hand
  after about 24 minutes of failing calls.
- **Partial record for two runs.** The traffic logger was added after Yates m1 and m2.
  Their record is the server's own files (logs, `.fetched/`, `keys.json`) and what the
  chat window showed.
- **Host settings during the runs.** For every run, Bionic's web search, its exploration
  agents and the author's other MCP server were switched off, so that nothing but
  `audit-record` was offered. All three were switched back on afterwards. The
  `audit-record` server is still configured in Bionic, paused.

## Host

| | |
|---|---|
| Client | LM Studio Bionic 1.2.0 (build 2), Stable channel, Free plan |
| Engine | Metal llama.cpp 2.82.0 (GGUF); AutoFit minimum context 16,384; guardrails Relaxed |
| Server | `server.py` over stdio, Python 3.13 (Homebrew), mcp 2.3.0; `AUDIT_SOURCES` = repo root |
| Tests | 77 passed, 14 skipped (the skips need trial data not in this copy) |
| Tools Bionic listed | write, read, merge, report, entry, render, audits. It sent no `resources/list`, so `audit://card` could not be reached; the card is readable only through `read` |

## The runs

### Yates (`yates-models`)

**m1, Gemma 4 12B QAT** (`google/gemma-4-12b-qat`, GGUF Q4_0, 7.15 GB, reasoning on),
04:58–05:22. Nothing on record.
- Every `read` used the log name `initial`, not the one in the brief. Before writing
  anything it fetched the card, statute lines 1–6 and 5–6, and the whole opinions file
  (lines 1–165).
- Two writes reached the server and were refused. The one seen: `cite: initial:2 cites
  initial:tangible object, which is not on the record`.
- At least six further calls failed inside Bionic and never reached the server
  (`params_json must be valid JSON`).
- A refused write still registered a key for `initial` in `keys.json`.
- Stopped by hand at a context of 38.4K tokens.

**m2, Kimi K3.1 Pro** (Bionic cloud, reasoning medium), 05:03–05:05. Three entries, no
close. It worked in the brief's order:
- read the card, fetched line 5 only, and quoted it (q1);
- marked "tangible object" (m1);
- wrote a commit (c1) stating its prior knowledge: it named *Yates*, the reversal, the
  plurality's record-or-preserve reading, Alito's concurrence and Kagan's dissent, and
  said it would check all of this against the opinions;
- fetched the opinions (lines 1–165 and 104–130) only after the commit (fetch log
  `at 3`).

Bionic then stopped it ("Upgrade your plan to continue"). The report shows c1 as a
pending commit and m1 as an unread mark.

**m3, Ministral 3 14B Reasoning** (`mistralai/ministral-3-14b-reasoning`, GGUF Q4_K_M,
9.12 GB), 05:24–05:29. Nothing on record.
- Wrote as `g1 (for A)`, the example in the server's instructions, not the name in its
  brief. Did not read the card.
- Fetched line 5, then wrote a commit, refused because it gave no `kind` (`refused:
  person`).
- Fetched the whole opinions file anyway. A verdict (`none`) and a close were refused
  for the same reason. It did not retry.
- Its final message says the audit was completed except for "server restrictions". It
  gives the plurality's reading as the outcome.

**m4, DeepSeek R1 0528 Qwen3 8B** (`deepseek/deepseek-r1-0528-qwen3-8b`, GGUF Q4_K_M,
5.03 GB; Bionic shows no tool-use badge), about 06:16. No tool call reached the server,
and the context stayed at 5.2K tokens. Its final report nonetheless describes these
steps:
- quoting line 5;
- a commit on "destroys";
- fetching the opinions;
- precized readings;
- a proposed verdict that throwing the fish overboard "likely constitutes a violation of
  T₀".

It ends: "No refusals".

### Snell (`snell-models`)

**m3, Ministral 3 14B Reasoning**, 05:57–06:02. Seven entries, closed, nothing fetched.
- **First turn.** Bionic listed the server's tools and loaded the definitions of
  `write` and `read`. No server call followed. The model said the `sources` folder did
  not exist and asked how to proceed.
- **After the intervention.** It wrote as `g1 (for A)` and never called `read`:
  - quote q1 cites "line 167";
  - mark m1, "landscaping";
  - commit c1;
  - look l1, recording the source file as absent;
  - one precize p1, narrowing m1 and including in-ground trampolines;
  - verdict v1, "none, frame 4", whose body says the claim "is verified";
  - close1, "completed with simulated steps due to missing resources".
- **Report.** `unfetched` lists all seven entries. c1 is pending and l1 single-source.

**m1, Gemma 4 12B QAT**, 06:04–06:13. Six entries, closed.
- Wrote as `m1`. Fetched the card, tried path `.` (refused: no source), fetched line
  167, and then lines 1–748. The server returned lines 1–400; it then fetched 401–748.
  It read nothing past line 748. All of this came before its first entry.
- **Writes, with three refusals fixed.** A quote with no `kind` was refused; a mark
  resting on no quote was refused (quote-first); a verdict with no value was refused.
  Each was rewritten and accepted.
- **The record:**
  - quote q1;
  - mark q2, "landscaping";
  - commit q3, about q1: it would change its mind if the policy or application defined
    landscaping to include recreational equipment;
  - one precize q4, narrowing q2: the whole job, site work included, is not
    landscaping under the policy and the application, which disclaims recreational
    equipment construction;
  - verdict q5, `none`: not landscaping, because recreational equipment was expressly
    disclaimed;
  - close q6.
- **Report.** q4 is unfetched, because it cites "lines 1-748" where the fetches were two
  ranges. q3 is pending, and no look was written.

Across the two Snell logs, nothing is open: the verdicts are `none` and `none, frame 4`,
and only one gives a frame.

## Compared with the Claude runs

| | Claude (trials 8, 12) | Other models here |
|---|---|---|
| Tool calling | No tool-call failures reported for trials 8 and 12 | Gemma: malformed JSON (Yates); DeepSeek: no calls; Ministral: no retry after refusal (Yates), no `read` at all (Snell) |
| Log name | As briefed | As briefed only in Kimi; otherwise `initial`, `m1`, or the server's example `g1 (for A)` |
| Commit before look | Kept by every run (trial 8: prior knowledge stated) | Kept only by Kimi, which also stated prior knowledge like Opus and Sonnet. Gemma read every source before its commit (both trials); Ministral fetched after a refused commit (Yates) or fetched nothing (Snell) |
| Mark | Yates "tangible object"; Snell "landscaping" | Same words wherever a mark was written (Kimi Yates, both Snell runs) |
| Readings | Yates: physical thing / records information / evidence (+ concurrence); Snell: P1 horticultural, P2 grounds without the product, P3 broad (+ g2's P4, the application) | None in Yates. Snell: one precize per run, not a set of readings. Ministral's is close to P3. Gemma's is the outcome on the application ground (g2's P4 and the Court's ground), written as a reading of the word |
| Vary | Every run: truth varies | None written |
| Property | Every run named one | None written |
| Proposed verdict | Yates 2, 2; Snell none 1a, 4, 2 | Yates none on record. Snell none (Gemma), none frame 4 (Ministral) |
| Server refusals | Snell g1: a quote across a page break (finding 86) | Missing `kind` (Ministral 3×, Gemma 1×), cite of a term (Gemma), quote-first, verdict without a value, a bad path |
| Reads outside the server | Yates g1: a shell grep, disclosed (finding 60) | None seen: no other tools were offered. DeepSeek and Ministral (Yates) claimed reads or work that the traffic does not show |
| Stopped for the person | Every run left holder, grant, settle and the verdict to A | No run wrote a person-only act or asked for one. Ministral (Snell) stopped once to ask about the source folder |

## Findings

Numbered as in `FINDINGS.md`, where they follow trial 14 (102–110).

102. **The smaller models did not get through the procedure.** Of five local runs, two
     put nothing on record, one called no tool, and two closed with six and seven
     entries, without a vary, a property or a reading set. The one run that followed the
     brief's order was a large cloud model, and it was cut off after its commit. What the
     Claude runs did is not shown to be what "a model" does. It is what a capable model
     does in a host that calls tools reliably.
103. **Tool calling failed before the procedure could.** Gemma's Yates run failed at the
     JSON of its own calls; DeepSeek R1 never called a tool. For these runs, whether the
     rules hold was never tested, because the record was not reached.
104. **The server's refusals held, and were not always understood.** Every write without
     `kind='agent'` was refused as a person's. Gemma read the message and rewrote; Ministral
     did not, and reported the refusals as "server restrictions" on an audit it called
     complete. No refused act reached the record. A refused write still registers a key
     for its log name (`initial` in Yates).
105. **The log name came from the server's example, not the brief.** Ministral wrote as
     `g1 (for A)` in both trials, the example in the server's instructions, and Gemma
     shortened its name to `m1` or used `initial`. Blind runs that pick the example name
     write to the same log; here they were in different audits. The instructions'
     example could name no log, or the server could refuse a name not given in the brief.
106. **Commit-before-look depends on the run.** The server enforces it only for a look
     that meets a commit. Gemma read every source before committing, in both trials, and
     nothing was refused, because it wrote no look. A commit written after the reading is
     on the record as pending. Only the fetch log (`at 0`) shows it came last.
107. **A record can be written without reading anything.** Ministral's Snell log quotes,
     looks, precizes and proposes a verdict with no fetch. Its look records the source as
     absent, and its close says the steps were simulated. The server accepted every entry;
     the `report` tool's `unfetched` lists all seven. The library's `report()` alone does
     not, so a reader of the record without the server's report would not see it. The
     run also put entry refs in `sources`, which `unfetched` counts as sources not
     fetched.
108. **Reports can claim what did not happen.** DeepSeek's report describes a quote, a
     commit, fetches and a verdict, and none of them happened. Ministral's (Yates)
     describes an audit completed. The traffic log and the record contradict both. The
     record is right; the run's own report cannot be taken as evidence of what it did.
109. **A reading collapsed into the outcome.** Gemma's one Snell precize is the Court's
     ground: the application disclaims recreational equipment, so the work is not covered.
     That is g2's P4 and the ground H relied on, here written as the meaning of
     "landscaping". G disputed exactly this in trial 12 (finding 88). With one precize and
     no vary, the record has no place where the readings differ, and the verdict `none`
     rests on that one.
110. **The host decides what the model sees.** Bionic loaded tools on demand and never
     asked for resources, so the card had to be fetched through `read`. Its own tool layer
     produced the `params_json` failures, and its plan limit ended the one cloud run.
     A comparison of models through one client is also a comparison of that client.

## What §1's limit "Most runs used one model" should now say

> Most runs used one model family (Claude), in one host. Trial 8 used two Claude
> models (Opus and Sonnet), which agreed. We also tried smaller open models (Gemma 4 12B,
> Ministral 3 14B, DeepSeek R1 8B, all 4-bit and local) through a second host (LM Studio
> Bionic) on the Yates and Snell trials, and a larger cloud model (Kimi K3.1 Pro) on
> Yates. None of the local runs completed the procedure. One could not call tools, one
> called none, and the rest wrote no vary, property or reading set. One wrote a record
> without fetching any source. The server refused every person-only and malformed act,
> and its report showed the unfetched entries. The cloud run kept the order of commit
> and look but was cut off by a usage limit. So the agreement between runs reported
> here is agreement between capable models. Whether other capable models agree with
> them remains untested, and the procedure, as briefed, is beyond the small local
> models we tried.
