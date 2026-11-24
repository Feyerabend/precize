# What computing the hand tests found

## Stage 1

*2026-11-20. Stage 1 of `../manual/mcp-audit-record-build-plan.md`: the library without
MCP (`audit/record.py`, `audit/reports.py`) and the first three hand tests as fixtures
(`tests/fixtures.py`). 16 tests pass (`python3 -m pytest -q`). Where the computed report
differs from the hand test, the test asserts what the server computes and a comment marked
DIFFERS says how. These are the findings.*

## The design computes

The cascade, open questions, pending commits, the drift flag and why a grant was withdrawn
all come out of the record as the hand tests worked them out:

- §6.4: the same eight entries fall, each with its chain.
- §6.3, as corrected: `a12` and `a14` fall, the grant is withdrawn on evidence (or under the
  check, when `d2` has `a12` in its past), and `a13` is open against `o2`.
- The review: `v1` stands after `e1` is withdrawn, and with the old, unsplit cite it would
  fall. So the split of cites is necessary, not only tidy.

The causal past was enough everywhere. Nothing needed the every-order test.

## Where the hand tests and the server disagree

1. **`a11` cannot be both refused and withdrawn.** The first test says rule 4 refuses `a11`
   at write time, and also counts `a15` as falling because `a11` was withdrawn. In one
   record only one is true. Under the rules, `a11` is never written, so `a12` and `a15`
   could not cite it. The eight-entry cascade describes the book's history, not what the
   server would have recorded. The fixture replays that history with the checks off.
2. **`a12` is missing from the first test's lists.** The commit about the withdrawn `a11`
   rests on nothing that fell (it is *about* `a11`), so it stands. The hand test put it in
   neither list.
3. **"Single source" cannot be read off the fields.** The hand tests name one or two
   single-source findings (`a33`, `e5`). Every look in these records has one source, so the
   computed list holds them all. Which of them matter was a judgment. The report can list
   them, but it cannot choose between them.
4. **A narrowing closes nothing.** The third test says `e3` is open "until A answers", and
   that A answered by narrowing (`a3`). The rules say only a `settle` or a withdrawal closes
   an open question, so `e3` against `v2` stays open. Either the hand test or the rule
   needs changing. A possible rule: a `precize` that narrows the claim in question *and*
   answers the opposing entry closes that question for its author.

## Choices the code had to make that the note does not

- **An entry that rests on another does not oppose it.** `a2` (none of the five) and `v1`
  (not 4) have different values on the same object. Without this rule they would be open,
  although `a2` takes over `v1`'s reading. Values are not all mutually exclusive, so
  resting-on is used as agreement.
- **`narrows` may name a look as well as a precize.** In the Elm case a universal claim
  found (`e3`) is narrowed, not a reading.
- **`v3` and `a4` needed sources.** By rule 4 both would have been refused as written in the
  third test. They are given the only sources the material states.
- **A withdrawal answers its reason. It does not rest on it.** So a withdrawal never falls.


## Stage 2: logs, heads and forks

*2026-11-20. `tests/test_logs_and_forks.py`; 23 tests pass in all. A reader is given some
logs, each up to a head, as files; the server merges them and reports over what it was
given. A fork is made by chaining an entry to an earlier one (`add(..., after=...)`), and
two copies of a log are merged by hash.*

**The fifth test's table is reproduced cell for cell** for `a11` to `a14` and all four
readers. The grant withdrawn on evidence is reported in R2 with its evidence *not read
here* (`O:o1`), and in R4 without that note.

**The sixth test is reproduced.** An old head is a valid log and is not detected; the
report states the head it read. A reader shown one branch sees nothing wrong. Two copies
merged show the fork at `d1`, with both successors, and the union is read: `a12` and `a14`
fall. Opposite claims on two branches of one author are open, and a `settle` by the author
across both branches (the join) closes them.

**Where the hand tests and the server disagree:**

5. **R1 knows of D.** The fifth test's table says R1 knows of no log it has not read. But
   `a12` cites `D:d1`, and the test's own text for R1 names that entry and its log. The
   table should say D for R1, as it does for R3.
6. **A fork found through a cite needs more than logs.** The sixth test lets A find the
   fork alone, because O passes on `d2`'s signed header with the cite. The server is given
   logs only, so it reports `D:d2` as an entry cited and not read (the seventh test's finer
   grain), and `o3` as resting on it. Finding the fork this way needs headers to travel
   with cites. That is a small addition, but it is an addition to the format.

**Choices the code had to make:**

- *Resting on what was not read* is followed through every step of resting-on, so `a14`,
  which rests on `a12`, is marked as well as `a12`. An entry that has fallen is reported as
  fallen, even if it also rests on something unread.
- A forked log's entries are ordered by their chain, not by their place in the file. So an
  author's earlier entries are in an entry's past only along its own branch.
- Two entries with the same id and different hashes are refused on reading. That is a fork
  by rewriting, and the sixth test did not consider it.

## Stage 3: the MCP wrapper

*2026-11-20. `server.py`, on the MCP Python SDK 2.3 (`MCPServer`, which replaces FastMCP).
`tests/test_server.py` drives it through an in-memory MCP client: 25 tests pass in all, run
with `.venv/bin/python -m pytest -q`. The server is registered in `.mcp.json`, but it has not
yet been tried by an agent in a live session.*

The rules hold through the server. A check with no grant is refused. A grant by an agent is
refused. A withdrawn grant brings down the check and the verdict on it. An agent's verdict
is reported as proposed. A report on A's log alone shows the check as resting on `D:d1`,
not read.

**Findings:**

7. **"Person" is only what the writer declares.** The rule that `holder`, `grant`, `settle`
   and the audit's verdict need a person is checked against `kind`, and `kind` is whatever
   the caller sends. An agent that writes `kind: "person"` passes. The rule needs something
   the agent cannot send: a key that only the person holds, so that signatures (stage 4) are
   what make the rule bite. Until then the rule only stops an agent that keeps to it. That
   is the same position as the card, which also relies on the auditor's honesty, but the
   design note speaks as if the server enforced it.
8. **One `write` tool, not one per act.** The plan said one tool per act. Eighteen tools
   with mostly the same fields cost more context than they save. The act is a parameter,
   and the tool's description lists what each act needs. Whether an agent then makes more
   mistakes is a question for the live trial.
9. **The log name is the caller's.** An agent run names its own log (`g1 (for A)`). Nothing
   stops two runs from using the same name, which would be one log with two writers. Forks
   would show it, but only once their entries chain from the same predecessor.

## The live trial (§6.1, T₀ "Bitcoin is money.")

An agent session loaded the server and audited T₀ as `g1 (for A)`, kind=agent, in the
audit `six-one-live`. It wrote eleven entries: q1, m1, v1, p1, p2, pr1, n1, c1, l1, vd1 and
x1, the last being close. It reached a proposed verdict and stopped where it should: at
holder, at the grant of n1, and at settle and the audit's verdict. The server refused two
writes. One was the agent's grant, tried on purpose, refused by `person`. The other was
p1/p2 pointing `narrows` at the mark, refused by `narrows`. The report has `proposed` =
{vd1} and is otherwise empty.

10. **The rules held without being pushed against.** The one refusal the agent did not plan
    came from a misread parameter, not from a rule blocking sound work. Finding 8 asked
    whether one `write` tool causes more mistakes; here it caused one, and the refusal
    message was enough to correct it.
11. **`narrows` reads as "the term this narrows".** An agent took it to mean the mark. The
    first precization of a term has no field that ties it to its mark, other than `rests`.
    Either say so in the tool description or let `narrows` cite a mark.
12. **`single_source` counts strings, not sources.** The look l1 cited two line ranges of
    the manual, so it counted as two sources. But both ranges are the manual quoting the
    decree, so it is one source, and second-hand. A source needs a document and a passage,
    and some mark of first-hand versus quoted.
13. **Nothing reports "awaiting grant".** n1 is a recover that no one has granted, and vd1
    rests on it through pr1/p2. Neither is shown as waiting; both are in `stands`. The
    card's rule (grant before check) is enforced at write time, but the report should say
    which recovers are ungranted and what rests on them. This is the hand-over list the
    agent had to write by hand in x1.
14. **Prompts were not reachable.** The client had no tool for MCP prompts, so the agent
    read the STOP text in `server.py`. The stopping rules must also be in the server's
    `instructions` and the `write` description, not only in a prompt.
15. **Small points.** `stands` lists the close entry. It is unclear whether a commit needs
    `rests` as well as `about`. A vary's value is free text, although the card has three
    outcomes. There is no act for the constitutive/descriptive classification step.

### Fixed after the trial

- **11.** `narrows` may now cite a mark, so a precize can narrow the term marked. The
  tool description says which entries it can point at.
- **12.** `single_source` now counts documents, not strings. The document is the text before
  the passage, as in "document, passage". A look has a new field, `via`, that names the
  document quoting its sources, and the report lists such looks as `second_hand`. `via`
  is left out of the hash when it is empty, so logs written earlier still load.
- **13.** A new report, `awaiting_grant`, maps each recover that no live grant cites to what
  rests on it. On the trial's own log it gives n1 → c1, l1, vd1, which is the hand-over
  list the agent wrote by hand in x1. `stands` no longer lists close, ask or show.
- **14.** The stopping rules are now in the server's `instructions` and in the `write`
  description, not only in the prompts.
- **15.** A vary now takes only the card's three outcomes: "true under all", "false under
  all" and "varies". The first two appear under `stops`, with what the card says to do.
  The classification step needed no new act. A property with value "none
  (constitutive)" marks a reading that has no property, and the report lists it under
  `constitutive`, with what rests on it.

Tests: `tests/test_live_trial.py` covers these fixes, and 31 tests pass.

## The second trial (after the hand-over)

Person A wrote three entries: a holder, h1 (A reads P₂); a grant, a1, of g1:n1; and a
show, a2. A new run, `g2 (for A)`, then wrote a check, k1, resting on A:a1 and g1:l1. The
check found that N's antecedent holds after Decreto 199 but its consequent does not. The
run also proposed a verdict, vd1, of "false under the granted N", and closed. The server
refused nothing. With A:a1 withdrawn (tried in memory only), k1 and g2:vd1 fall with the
chain → A:a1, and n1 is back in `awaiting_grant`.

16. **One log, one kind (fixed).** An agent entry was accepted in person A's log, because
    `kind` was read from each entry as given. Now a log keeps the kind of its first
    entry, and the rule `kind` refuses an entry of any other kind.
17. **`object` is free text, so a disagreement can hide.** g1:vd1 has the object
    'T₀ "Bitcoin is money." read under P₂, for El Salvador after Decreto 199 (2025)'.
    g2:vd1 has the object 'T₀'. The values differ, but the objects do not match, so
    `open` is empty. This is the manual's own point, met in the tool: whether two claims
    disagree depends on their saying the same thing about the same object. The object
    should be a ref to the quote (g1:q1), not a free string. The reading and the case
    belong in a precize or in the body.
    *Fixed:* an object may now be "ref" or "ref|reading". It is qualified at write time,
    so two authors who name the same quote match. Free text is still accepted, because
    the hand tests use objects like "T0|P1", but it is reported as `loose_objects`. On the
    trial record those are g1:vd1, g1:v1 and A:h1. The two first-run proposals cannot be
    rewritten (the log is append-only and closed), so the dispute between them stays
    hidden in this record. A new run would make it visible.
18. **"Under the check" needs a cite.** If A withdraws a1 after reading k1 without citing
    it, the report says "on evidence". The report sees only what is cited. To be read as
    withdrawing under the check, the withdraw must answer k1. This is the design's
    behaviour, but the tool description should say so. *Done:* A withdrew a1 answering
    k1, and the report says "under the check". The `write` description now says this.

## Stage 4: signatures and the agent checks

*2026-11-20. `audit/sign.py`, `audit/store.py`, `audit/fetch.py`, `audit/person.py`, and a
`read` tool in the server. `tests/test_stage4.py` replays the fourth hand test (§6.4 with
two agent runs) through the server: 40 tests pass in all.*

Each log has one ed25519 key, registered with the log's kind in the audit's `keys.json`. An
entry is signed over its hash, so the signature is not part of the hash, and logs written
earlier still load. On load, an entry in a registered log must carry a valid signature of
that log's key, or the whole load is refused. The server makes and holds a key for each
agent log, on the log's first entry. It holds no person key and refuses `kind=person`. A
person makes a key once and writes with `python -m audit.person`, outside the server.

**The fourth test is reproduced.** `g2.4` is refused (`verbatim`): the run fetched the
timeline, and the sentence it quotes is not in it. `g1.3` and `g2.5` are proposed. Their
question is listed as open only between agents until A answers `g2.5` (`a6`), then as open,
until `a8` settles it. `a6` and `a7` stand, `a5` is pending, nothing falls. An agent call
writing as A is refused (`person`).

19. **Finding 7 bites, but only as far as the key does.** The server cannot write a person
    entry, and a person entry written to the file by hand, hashed but not signed by the
    person's key, makes the record refuse to load. But the registry is trust on first use.
    Whoever first registers a key for a log name is its author. An agent with a shell can
    run `audit.person init` for a new name and become a "person". The rule now holds against
    an agent that has only the MCP server, not against one that has the machine. That is
    the seventh test's point: who an author is is settled outside the logs.
20. **The commit check sits on the look, not the commit.** The hand test refuses a commit
    "if what it is about has already been fetched". But a commit is about an entry, and a
    fetch is of a passage, so the server cannot tell which fetches a commit is about. What
    it can check is the other end: a look that meets a commit may cite only passages the
    run first fetched after the commit. Fetching the passage again does not help, since in
    the context is seen. The effect is the same. Evidence seen before the commit cannot
    meet it.
21. **Verbatim is a check on quotation marks.** Only words in quotation marks are checked,
    and only when every source of the entry was fetched through `read`. A paraphrase is
    not checked. A source not fetched through the server is not refused, but is reported
    as `unfetched`, since the server cannot see what a run read elsewhere.
22. **The settle was a narrowing of the object.** A's verdicts are at two boundaries. With
    the object `A:a1` for all four verdicts, `a6` would oppose `g1.3` and `a7` would oppose
    `g2.5`, and `a8` would not close those. Written as `A:a1|evaluation boundary` and
    `A:a1|second boundary`, A's verdicts oppose nothing, and the one question left is the
    runs', which A settles as "both, at different boundaries". So the hand test's `a8` is
    finding 17 again, and it touches finding 4: what closes a question here is that the
    reading was made part of the object.
23. **Open between agents** is computed as: an open pair of agent entries, neither of which
    a person's entry rests on (through every step) or answers.
24. **Old logs are unsigned.** The two §6.1 trials load and are reported under
    `unsigned_logs`, with the person-only acts in them (`A:h1`, `A:a1`) under `unverified`.
    Since the signature is over the hash, A could sign those entries afterwards without
    changing a hash. That is not built.
25. **The keys and the fetch ledger are private.** Each audit folder now holds `.keys/`
    (the server's agent keys) and `.fetched/` (what each run fetched). Neither is part of
    the record. Neither may be published with it.

## The third trial (§6.4, T₀ "Powerful AI systems can go rogue.", signed)

Two agent runs with signatures and `read`: g1 (the evidence run, commit before fetch) and
g2 (the drafting run). Both logs are signed agent logs, `unfetched` is empty. A wrote
afterwards with a person key (`keys-local/A.pem`, outside the audit folder) through
`python -m audit.person`. The record is `data/six-four-live`.

26. **Two verdicts of "4" hid a disagreement.** g1:v1 has the object `g1:q1`, g2:v1 has
    `g2:q1`. Each run quoted T₀ in its own log, so the two verdicts have no common object
    and can open nothing. In substance they differ: g1 says c₁ is undecided at the sandbox,
    g2 says c₁ held on the proxy route and is undecided only for WebDAV. This is finding 17
    from the other side: there, one object with two values hid a narrowing; here, two
    objects hide one question. A split it by route (a7 "4" on the proxy, a8 "undecided" on
    WebDAV, a9 at the second boundary) and settled both proposals with a10. A check that
    two quotes with the same quoted words are one object would have shown it.
27. **Verbatim against LaTeX source.** g1:l2 was refused once: its quotation crossed
    `\emph{...}` and a line break. The check is right that the words are not in the source
    as fetched, but a run reading LaTeX has to quote markup or quote shorter. `read` could
    return the text with markup stripped, and the check compare against that.
28. **Commit-first was exercised once.** g1 fetched lines 434–450 before its commit and
    the looks cite 450–660, fetched after. g2 fetched all of §6.4 before its commit k1 and
    said so in k1, so no look answers k1 and the check had nothing to refuse. An honest
    run steps around the check. A dishonest one could too, by not answering its commit.
    `pending_commits` shows it in both cases.
29. **A commit that takes over another stays two commits.** A's a6 answers g2:k1, but
    k1 stays pending: only a look that meets it removes it. Whether a person's commit that
    answers an agent's should retire it is not decided.
30. **Precize without `narrows`.** g2 wrote c1 and c2 as precize with only `rests`, so
    `drift` cannot be computed for them. A's a4 and a5 narrow g2:c1 and g2:c2. The card
    should say that `narrows` names the precization or term being narrowed (finding 11).
31. **What the runs asked about.** Both runs noted that the task's term "contained" is not
    in T₀ and that "go rogue" was not marked. g2 cited the manual in `via` and in
    `sources` at once, and asked what `property` takes as fields. g1 asked what `meets`
    means for a commit with two clauses, and whether "fetch narrowly" has a limit. The
    card asks for a holder in step 3 while agents must stop at holder. These are points for
    the card and the instructions, not the server.

## The fix round, and a fourth trial (§6.4, "go rogue")

Built after findings 26–31:
- **One object for the same words.** In the report a quote used as an object stands for
  the words it quotes, normalised for case, whitespace and closing punctuation. Two
  authors' quotes of the same words are one object. Only like acts oppose: a holder and a
  verdict on one object do not. A verdict numbered by the card is its number, so "4" and
  "4 rule–property divergence" are one value. The new report `same_object` lists, per act
  and object, the entries of two or more authors.
- **`read(plain=True)`** returns LaTeX source with the markup out. The verbatim check
  takes quoted words found either in the text as fetched or in the plain text.
- **An agent's precize must give `narrows`**, or it is refused ("narrows").
- **Verbatim and unfetched apply to any agent entry that gives sources**, not only quote
  and look (after finding 35).
- **The instructions** say what `property` and `commit` take, what `meets` means for a
  commit of several clauses (any one clause), that `via` names the document the passage
  quotes and not the one read, that a holder candidate goes in the precize's body, and
  in what order to fetch around a commit.

In the third trial's record the report now puts g1:v1 and g2:v1 on one object.

The fourth trial: two runs on the term of T₀ itself, "go rogue", audit
`data/six-four-round`. Both wrote with `narrows` throughout. g2 quoted T₀ through
`read(plain=True)`. Both used `via` for the document quoted, not the one read.

32. **`same_object` works, and showed agreement.** Both runs varied T₀ to "varies" and
    proposed verdict 5 (pseudo-alternatives) on `"powerful ai systems can go rogue"`. The
    report lists both pairs under `same_object` and opens nothing. `open_between_agents`
    was again tested only in the test suite.
33. **The agreement is not independent.** Both runs read the manual's own analysis
    (w₁, w₂, w₃, and the finding that the term is constitutive) and reached it. Two runs
    over a worked text measure whether they can follow it, not whether they would find it.
    A trial of independence needs a case the manual has not audited.
34. **Commit-first refused once, and the run stepped around it.** g2 fetched §6.4 whole,
    wrote its commit, and had a look answering it refused. It rewrote the look without the
    answer, and its commit stays pending. That is finding 28 again: the check stops a false
    claim to have met a commit, not a run that never tries. g1 needed the lines of T₀
    before it could write a commit about the mark, and the instructions now say so.
35. **Verbatim did not reach a precize (fixed).** g1:P2 quotes words from lines 430–470
    but cites 470–600, and was accepted, since verbatim checked only quote and look.
36. **A commit can fail without being met.** g1:L1 found what g1's commit had not
    foreseen: neither reading in circulation fits. None of the commit's clauses was met,
    and the schema has no way to say the commit was incomplete. g1 wrote it in the body.
37. **Small points.** g1's P3 narrows a look, the "claim found" case, as the instructions
    allow. g2 put each precization in `value` as well as the body. `via` on a quote is kept
    but only looks are reported as second hand.

## The fifth trial: two sentences nobody had audited

Two audits, two runs each, briefed only with the card and the source; no worked answer
existed for either. `data/wood-porter`: the last sentence of the abstract of Wood & Porter
(2019), "By and large, citizens heed factual information, even when such information
challenges their ideological commitments." `data/ai-transparency`: a governance norm given
by the user, "Organizations should establish policies and procedures to ensure that AI
systems are sufficiently transparent and explainable…", origin unknown. g1 was the
evidence run, g2 the drafting run. All four closed. The two Wood & Porter runs were cut
off by a usage limit after `vd1` and closed on a second turn without rewriting anything.
PDFs in `out/`. Person A has not written; these findings are from the agents' record
alone.

38. **Independent runs agree on the analysis and part at the verdict.** In each audit
    both runs marked the same term ("heed"; "sufficiently" and "sufficiently transparent
    and explainable"), varied it to "varies", built near-identical ladders of readings in
    the same order (no backfire → movement toward the fact → acceptance → acting on it),
    and wrote almost the same property. They then proposed different verdicts: on Wood &
    Porter 3 (equivocation) against "none of the five; frame of 4 printed"; on the norm
    two different wordings of "none fits". This answers finding 33 in part: without a
    worked text the analysis still converges, and the disagreement sits where the card
    leaves most to judgement. `open_between_agents` fired on a live record for the first
    time, in both audits.
39. **"No verdict" has no value, so two agreements open as a disagreement.** The card's
    step 7 allows "no case: frame printed, finding absent", but it is not a numbered
    verdict, and the `write` description gives no value for it. Three of the four runs
    wrote it as free text. `same_value` compares those as strings, so on the norm the two
    runs, which agree that no verdict can be reached, are reported open against each other.
    The build plan already listed `none` among the values; the card and the server should
    take `none` (with an optional frame number, "none, frame 4") and treat it as one value.
40. **A norm has no truth value, and the card assumes one.** `val(T₀|P)` asks whether T₀
    is true under a reading. Both norm runs, independently, replaced it with "does a given
    organization comply under this reading"; g2 made up a test case (a credit-scoring
    model with a model card and no reason given to a refused applicant) and labelled it as
    its own. The card needs a line for norms: vary compliance of a stated case.
41. **An unknown origin empties steps 3 and 6.** With no speaker and no parties, every
    holder stays a candidate and nobody can be asked. g1 recorded the origin as `absent`
    on a look, which then met its own commit and emptied its reading P3 (an external
    standard whose content is missing) at once. g2's commit, that a definitions clause in
    the source would change its mind, can never be answered and is pending for good. That
    is finding 36 again from the other side: the schema cannot say a commit is
    unanswerable on this record.
42. **Drift flags every first reading written after a look.** The report flags g2:P0–P3
    (Wood & Porter) and g1:P1–P3 (norm) as drift. Each narrows the mark, not an earlier
    precization, and rests on looks because commit-first put the looks before the
    readings. The rule (`reports.py`, flag 8) counts any look in the precize's past and
    not in the narrowed entry's past. It should fire only when `narrows` names a
    precization, or the plan's wording ("a precize that narrows one it rests on") should
    be read that strictly. As computed it cannot tell a reading informed by evidence
    from a reading revised to save a thesis.
43. **One paper, one source.** Every look in Wood & Porter is single-source, since the
    only text is the paper; so is the norm's one look. "Single source" is right, and
    useless as a warning when the audit is of one document's claim about itself. The
    report might say which looks rest on the document T₀ comes from, which is a different
    thing from resting on one witness.
44. **The checks refused only real errors.** Seven `verbatim` refusals in Wood & Porter,
    each a word not in the passage cited, a lowercased or elided quote, or a quote across a
    page break in the pdftotext output (the last is an artefact of extraction, not of the
    run). One `commit-first` refusal, rightly: g1 cited the abstract, read before its
    commit, in a look answering the commit. g1 found that quoting a word of T₀ in a look
    counts as quoting the abstract, and wrote around it without quotation marks.
45. **A structural ambiguity has nowhere to go.** g2 on the norm found that
    "commensurate with the level of risk" (and "throughout the lifecycle") can attach to
    how transparent the system must be or to how rigorous the policies must be. That is
    not a term to mark. It wrote an `ask` for A, which the report does not show anywhere:
    `ask` is a keeping act. An ask to a person should be listed as open until answered.
    g1 noted a second one ("to ensure": having policies, or getting the result) and did
    not record it.
46. **Small points.** The runs did not know how `absent_what`/`absent_where` go with a
    look, whether readings are narrowed again after the looks, or whether marking a second
    term for a grid (norm: "relevant stakeholders") is theirs or A's. g1 on Wood & Porter
    found the paper's own first use of "heed", the elites' complaint about the public's
    failure to heed facts, and offered it as a candidate holder; g2 found the paper uses
    the word in three senses. Neither had been told to look.

### Fixed after the fifth trial

- **39.** A verdict value beginning "none", "no verdict" or "no case" is the one value
  none; "none, frame 4" carries its frame after it. The `write` description says so. The
  two norm runs are no longer open against each other; Wood & Porter (3 against none)
  still is.
- **42.** A `precize` whose `narrows` names a mark is a first reading and does not drift.
  Narrowing a precization or a claim found after a look bore on it still does (the
  review fixture's a3). No drift is now reported in either fifth-trial audit.
- **45.** The report has `open_asks`: asks no entry by another author answers. The
  rendered box lists them, and the entry is tagged *unanswered*. g2:a1 on the norm is
  the one open ask.

Tests in `tests/test_fifth.py`. 40, 41 and 43 are for the card and are not changed.

## The sixth trial: three sentences from one AI answer

Three sentences the user took from one AI assistant answer on Google (possibly Gemini),
prompt unknown, about no known system, policy or study: `data/tenant-sanitized` ("All
user-uploaded documents are sanitized before ingestion into the vector database, ensuring
sensitive internal data cannot leak across tenant boundaries."), `data/expense-entertainment`
("Reimbursements for client entertainment are approved when expenses are reasonable and
directly tied to an active sales opportunity.") and `data/adherence-improvement`
("Patients who demonstrated adequate adherence during the initial phase showed clinically
meaningful improvement at the six-month follow-up", no full stop). Two runs each, briefed
as in the fifth trial and after its fix round. All six closed. Person A has not written.

47. **Every verdict is none, and the fix of 39 both worked and hid something.** All six
    runs proposed none; five gave a frame, four of them frame 4. No pair opened, which is
    right for the expense and adherence audits. But on the tenant sentence g1 wrote "none,
    frame 3" (equivocation, if a case appeared) and g2 "none, frame 4", and that real
    difference is no longer reported. When both values give a frame, the frames should be
    compared.
48. **The first independent split on the mark, and the report does not show it.** On the
    tenant and adherence sentences both runs marked the same term ("sanitized"; "adequate
    adherence"). On the expense sentence g1 marked "reasonable" and g2 "directly tied to an
    active sales opportunity", g2 saying "reasonable" nearly names the property. That is
    the earliest and most consequential place two audits can part, and `mark` is not an
    opposable act, so nothing in the report says the two audits are of different terms.
    Marks on one object by two authors with different words should be listed.
49. **An AI speaker has no reading to ask for.** All six runs, independently, said that the
    card's steps 1 and 6 (ask the speaker, ask the parties) and the holder filter of step 3
    have no one to apply to. Four wrote an `ask` for A instead; the rest named generic
    readers ("a finance reader", "research conventions"). exp-g2 noted that the card's
    filter, taken literally, removes every reading, and only the server's instruction to
    name a candidate keeps them. The card needs a branch for a sentence with a source and
    no speaker: the holders are readers, and the audit is of the text.
50. **A sentence about nothing has no truth value to vary.** With no system, policy or
    study, `val(T₀|P)` is undetermined, not true or false. The runs bent "varies" to fit
    ("variation in principle only"; "whether the guarantee follows from the sanitizing");
    exp-g1 wrote no vary at all. `vary` needs a value for undetermined under every reading,
    or the card a stop: no subject, print the frame after step 2.
51. **Commit-first on a one-file record leaves every commit pending.** Five of six commits
    are pending, and the sixth met only the clause "no study is in the record". The source
    file's header, read with T₀, counts as read before the commit, so a look citing it is
    refused under commit-first even when it says the commit is not met (tenant g1, exp g1).
    That is findings 36 and 41 a third time. Two choices: let a look that does not meet a
    commit answer it whatever was read before, since commit-first exists to stop a false
    claim of meeting; or let a commit be written as unanswerable on this record.
52. **What the audits found in the answer.** On the tenant sentence both runs found that
    only a reading in which "sanitized" includes tenant scoping makes the "ensuring" clause
    follow, and then from the scoping, not from any change to content. That is the frame of
    a rule–property divergence the sentence hides. On adherence both found that a threshold
    set after the outcome makes T₀ true by construction, and g2 a selection effect:
    patients sorted by their own adherence may improve for other reasons. On expense both
    asked whether "when" is a sufficient or a necessary condition, and whether the
    sentence describes practice or states a rule. exp-g1 read the two sibling sources and
    inferred, labelled as inference, that an answer spanning three unrelated topics
    describes no one organization's policy.
53. **Small points.** The brief for the tenant runs said line 4; T₀ is on line 5, and both
    runs caught it. `absent_in` "record" or "world" for "not known to this record" was
    unclear to three runs; all chose record. tenant-g2 wrote readings before the vary, as
    the server needs vary to rest on them, against the card's order. exp-g2 used ≺ for
    "stricter than" and corrected it in a later entry without withdrawing. tenant-g1 had no
    tool to list what `sources/` holds and used `ls`, which the server cannot see.

### Fixed after the sixth trial

- **47.** Two values beginning "none" are one value unless both give a frame and the
  frames differ. The tenant pair ("none, frame 3" against "none, frame 4") is open
  again; the expense and adherence pairs are not.
- **48.** The report has `marks_differ`: for each quoted sentence, the marks of two or
  more authors when they mark different words (the mark's value, or else the first
  passage its body quotes). The rendered box lists them. The expense audit shows g1:m1
  against g2:m1; the other two show nothing.

Tests in `tests/test_fifth.py`. 49–51 are for the card and are not changed.

## The seventh trial, after the hand-over: two fictional persons

No real person wrote. Two fictional persons, A (a school lawyer) and B (an evidence
advocate), were given stipulated stances and written with their own keys by the author
(`trials/skollagen-fiktiva/`). Each wrote without reading the other. Their holders rest on
the bill, prop. 2009/10:165, section 5.4.2 (`../sources/prop-2009-10-165-avsn-5-4-2.txt`).
A took (b) on "och", named the bill as holder of all three readings (the method reading
only weakly), and gave "none, frame 1b". B took (a), held the method reading themself, and
gave 4. The trial tests the record after the hand-over, not anyone's judgement.

54. **Answers to an ask are not compared.** A answered both asks with (b), B with (a). The
    report lists no open asks and nothing else: the two answers are precizes, which are not
    opposable, and neither disputes the other. Opposite answers to one question hide, as
    verdicts did before finding 39.
55. **Holders are read as exclusive.** A named the bill as holder of g2:p2, B named
    themself. The report shows an open pair, but both can be true: a reading has many
    holders. `holder` is in OPPOSABLE as if a reading could have one. Here the record
    invents a conflict.
56. **Readings are not matched across runs.** g1's P2 is g2's P3, and the reverse. Both
    persons used g2's numbering, so their holders met. Had one used g1's, they would not
    have, and nothing would show that the two runs' precizes name the same reading. The
    canon that matches quotes (finding 26) does not reach precizes.
57. **Taking a side works.** Each person verdict rests on one agent's proposal and so
    accepts it, and opposes the other. The agents' pair is no longer open between agents.
    Both person verdicts stand, the agents' are listed as proposed. Five pairs are open,
    A against B among them, and only a settle by an accountable third author closes it. The
    disagreement does not go away when persons arrive. It moves up a level, where the
    record shows it as theirs.

**Fixed (2026-11-20), before the freeze.** Reports are computed, so no trial was run again;
the signed logs are as written.

- **54.** An entry that answers an ask must now carry the answer as its value, and two
  authors' differing answers to one ask are open ("answers g1:a1: (b) / (a)"). A's and B's
  answers were written before the rule and have no value. The report does not read their
  bodies, so it lists them under a new heading, questions answered by different authors,
  to compare by hand (`answers_to_compare`). Comparing them is a judgement of meaning.
- **55.** A holder whose object is a reading (a mark or precize) names one of its holders
  and no longer opposes another. A holder whose object is the holder ("D", value "P1"), as
  in the fork test, says which reading that holder goes by and still opposes. The
  Education Act audit now has four open pairs, not five.
- **56** stays open. Saying that two runs' precizes name one reading is a judgement of
  meaning, and so would be a person's act if it is built.
- 62 tests. Of the nine audits, only the Education Act audit's report changed.

## The eighth trial: Yates, two models, two fictional persons

The English counterpart to the seventh. T₀ is 18 U.S.C. §1519, and the case is *Yates v.
United States* (2015): undersized red grouper thrown overboard after a federal officer told
the captain to keep them. Is a fish a "tangible object"? The statute and the opinions are
public domain (`../sources/usc-18-1519.txt`, `../sources/yates-v-us-2015.txt`, from Cornell
LII). Both runs got the same brief: the statute first, a commit naming any prior knowledge,
then the opinions. g1 ran on Opus, g2 on Sonnet. After the hand-over, two fictional persons
with stipulated stances wrote under their own keys (`trials/yates-fiktiva/`): C, a
prosecutor, and D, defence counsel. Neither read the other. The case is well known, and the
paper must say so.

58. **Prior knowledge can be put on the record, but it cannot be removed.** Both commits
    say plainly that the run knows the case, and both give the outcome, the 5–4 split and
    who wrote which opinion, before the opinions were fetched. Every look then "meets" its
    commit. On a known case, commit-before-look tests whether the run's memory is right,
    not whether its reading is independent. The rule makes the run honest; it cannot make
    it ignorant. This is the remedy for finding 33 as far as a record can give one.
59. **Two models agree on everything.** Same mark, the same three readings in the same
    order (physical thing, records information, evidence), the same property, and the same
    proposed verdict, 2. Nothing is open between the agents, and the readings are numbered
    alike, so finding 56 does not arise. Because both knew the answer, this does not show
    that two models reach it apart. The second model removes the one-model limit for this
    trial and leaves finding 33's.
60. **A read outside the server is invisible.** After its commit, g1 ran a shell search on
    the opinions file to find where each opinion begins, and said so in its close entry.
    The record sees only what passes through `read`. That `look` needs a fetched source
    binds the look, not what the run read. The only check here was the run's own
    disclosure, as with keys (findings 7, 19, 25): the record is as honest as its authors.
61. **A person can adopt the proposal.** D's verdict rests on both agents' and so accepts
    them. C's opposes all three. Three pairs are open: C against D, and C against each
    agent. Nothing is open between D and the agents. In the seventh trial both persons
    departed from one agent each (finding 57). Here one adopts the agents' verdict, and
    the disagreement still moves up a level: it is C against D, under signatures.
62. **A real case gives real verdicts.** This is the first English trial where no verdict is
    none: 2 from both runs and D, and 4 from C. With an application on the page, the card
    works through to the end, which the AI sentences (finding 47) and the norm (40) never
    did. The holders, too, are on the page. Both persons name the opinions, cited by line,
    and their holders agree. The open question is between verdict kinds: C says one
    reading fails the property (4), and D says the disagreement is real and lenity settles
    it (2). Whether that is a further disagreement or the same one at a higher level is a
    judgement of meaning, and the record leaves it open.

Small points. g2 wrote no look at the dissent. One of its looks cites lines 1–120, which
cover the syllabus, the plurality and the start of the concurrence, as a single source.
Every look is flagged single-source, since there is one file (as in 43). g1's p4 is flagged
for drift: it narrows a look (l2), and a later look (l3) bears on it. The code is unchanged
and 62 tests pass.

## Found while writing the paper

63. **A reading found in a look was flagged as drift.** In the Yates audit g1's p4 writes
    down the concurrence's reading, found in the look l2, and narrows l2. The report
    flagged it as drift, because g1's look at the dissent (l3) came between l2 and p4 in
    the log. l3 does not cite l2 or p4; it is in p4's past only through the chain. The
    note under the eighth trial took the flag at face value ("a later look bears on it").
    Writing §4 of the paper showed it was wrong.

64. **A connective went to `ask`, where it has no holders.** In the seventh trial both runs
    put "och" to a person as an ask with two options, (a) every part rests on both, (b) the
    whole rests on the two together. Option (b) joins two questions: scope (each part or
    the whole) and the connective ("and" or "and/or"). The reading *each part rests on
    research or proven experience or both*, probably the one most Swedish readers hear, was
    not offered: the ask was itself a verdict 5. Allen (1957) makes the same point for
    English "and"; neither language has a default. And an ask has no holders, no vary and
    no verdict, so the persons' answers could be compared (54) but not carried further.
    `mark` never required a single word; nothing said a connective could be marked. Also,
    `marks_differ` compared marks one by one, so two authors who both marked a word and a
    connective in one sentence would have been listed as differing.

### Fixed

- **63.** A `precize` that narrows a look drifts only if a later look cites that look.
  A precize that narrows a precization keeps the old rule (any look in its past and not
  in the narrowed entry's), so the hand tests' a26 still drifts. The review fixture's a3,
  which narrows the look e3 after V's v2 answered it, still drifts. g1:p4 in Yates no
  longer does.
- **64.** The server's instructions say that a connective or a phrase whose attachment is
  in doubt can be marked and precized like a word, listing every reading (for "and": both,
  either or both, the whole together; each part or the whole). The `ask` description says
  to list every reading, and to mark instead when the readings make the truth vary.
  `marks_differ` compares the set of words each author marked. `tests/test_connective.py`
  runs the Education Act sentence with "och" marked: holders refused from an agent,
  persons' verdicts open. The card itself is not changed (TASKS-REVIEW-2, item 22).
  67 tests pass.

## The ninth trial: the connective, unprompted (`skollagen-och`)

Two runs on the Education Act sentence again, after the fix for 64, in a new audit. The
briefs were trial 7's and said nothing about "och". The point was to see whether the
server's new instructions alone lead a run to mark the connective. g1 was the evidence
run (it read 1 kap. 3 § and 7 b §), g2 the drafting run. Both wrote in Swedish, closed, and
had nothing refused.

65. **A quote that quotes a note was not compared.** g2's quote reads "utan
    ändringsnoteringen "Lag (2026:1096).": "Utbildningen ska vila …"". The report took the
    first passage in quotation marks as the words quoted, so g2's q1 was the amendment
    note, g1's q1 was the sentence, and the two verdicts on one sentence were not compared:
    `same_object` and `open` were empty, and the split below did not show. Both passages
    are verbatim (the server checks every quoted passage), so nothing at write time could
    catch it. Finding 26 had assumed a quote quotes one thing.

66. **The connective was marked unaided, with every reading.** Both runs marked "och" as m1,
    before "vetenskaplig grund", and neither used `ask`. Both listed both, either or both,
    and the whole taken together. Each added a fourth of its own: g1 "both, but of the
    whole" (scope and connective crossed), g2 "the phrase as one fixed expression". Both
    built a grid of the two marks and varied on a method with proven experience and no
    research support: false under "both", true under "either or both".

67. **The verdicts split again, differently.** g1 proposed "none, frame 1b", g2 "none,
    frame 3". In trial 7 the frames were 1b and 4. The readings agree; the frame the case
    would fall under does not, and it is not the same split twice. g2 made no look, so its
    commit c1 is pending; g1's three looks are all one document (`single_source`).

### Fixed

- **65.** `quote_words` takes the longest passage in quotation marks as what a quote
  quotes; `canon` uses it. Marks keep the first passage. No earlier audit's quote changes.
  The two verdicts in `skollagen-och` are now open between agents.
  `tests/test_quote_words.py`. 70 tests pass.

68. **"And" was not the only logical word.** After trial 9 the user asked about "if". Allen
    (1957, 842, 858) already names it: *expressio unius* turns "if P then Q" into "if and
    only if", and courts go both ways. Ordinary "if" has at least three readings: P is
    enough for Q (which may also come otherwise); P is the only way to Q (the conditions
    listed are all there are); P brings Q about (a consequence, not only a conditional).
    The instruction from 64 named "and", "och" and "or" only.

- **68.** The server's instructions say any logical word may be marked, with no default,
  and list readings for "and", "or", "if", and name "unless", "only", "not", "all/any/
  every" and "shall/may". The `ask` description gives "if" as a second example. Not yet
  tried live.

## The tenth trial: "om" (`skollagen-om`)

Two runs on skollagen 1 kap. 5 a § andra stycket, after the change for 68, in a new audit:
"Rektorn får även bjuda in politiska partier utifrån ett annat urval än som anges i första
stycket, om urvalet sker på en annan objektiv grund." The briefs were trial 7's and named
no term. g1 was the evidence run (three looks in chapter 1), g2 the drafting run (one
look). Both wrote in Swedish and closed; g2 had one quote refused as not verbatim and
fixed it.

69. **Readings written in a mark's body reach nothing.** g1 marked "om" as m2 and listed
    four readings in the mark's own text: enough, only if, necessary but not sufficient, a
    consequence. It wrote none of them as a precize. Its p6, after a look, finds that the
    paragraph's structure rules out "enough" and "a consequence", but p6 narrows the look
    l3, not m2. So no entry stands for reading (b) or (c): a person could not name a
    holder for one, and a vary or verdict could not rest on one. g2 wrote R1–R3 as precizes
    narrowing its m2. Nothing in the report showed the difference.

70. **"If" was marked, with the readings the server lists.** Both runs marked "om" next to
    "objektiv grund", without `ask`. Both gave enough, only if, and a consequence, which are
    the three the instructions from 68 name; g1 added "necessary but not sufficient", which
    they do not. This shows the instruction is followed, not that a run finds the readings
    of "if" by itself. g2 also wrote a property for "om", "none (constitutive)": the
    connective tracks nothing in the world, so no rule–property divergence comes from it.
    Its verdict rests on that property (`constitutive`), and on pr1 for "objektiv grund".

71. **The verdicts agree in value, not in what they rest on.** Both proposed "none, frame
    4", the first Swedish trial where the frames agree, so `same_object` lists the two and
    nothing is open. But g1's frame-4 case is a procedurally correct criterion (its P3)
    that is chosen to sort parties by opinion; g2's is a measurable criterion (its P2), such
    as local branches, that excludes one bloc in effect. And g1 narrowed "om" to only-if or
    necessary, while g2 kept enough and a consequence standing. The report compares values,
    so it shows the agreement and not the difference; a person has to read the rests. This
    is a pseudo-agreement between runs, 1b one level up. Not fixed: what a verdict rests
    on is in each run's own log, and comparing readings across runs is a judgement.

Also: g2's commit is pending (its one look does not say it meets it); every look in both
runs is of one document (`single_source`); neither read the bill (Lag 2017:1112), which
g1's close names as what could decide between the readings of "objektiv grund".

### Fixed

- **69.** The report has `unread_marks`: a mark that no precize narrows (or, in logs from
  before `narrows`, rests on without a target). The render tags it "no readings" and lists
  it under *For a person*. The server's instructions say to write each reading as its own
  precize narrowing the mark. Across the earlier audits it flags only marks that indeed
  have no readings (six-four-live g1:m1 and A:a3). `tests/test_unread_marks.py`. 74 tests
  pass.
- **68** is now tried live (70).

## The tenth trial again, with the preparatory works (`skollagen-om-prop`)

The same sentence and trial 10's briefs. They have two additions: the runs may read the
bill (Prop. 2017/18:17) and the committee report (bet. 2017/18:UbU6), both saved in
`sources/` with provenance; and they may not read `skollagen-om`. Both runs were cut off by
a usage limit. g1 had closed; g2 had written its verdict and was told to close, which it did.

72. **The preparatory works changed the verdict, and the runs now agree on the case.** In
    trial 10 both proposed "none, frame 4" on different cases (71). Here both propose "2,
    real disagreement" on the same case: the government against Unga Feminister and
    Hudiksvalls kommun, over whether a school may leave out an undemocratic or openly
    violent party on an "objective ground". The bill names these readers (pp. 10, 12, 16)
    and answers them from RF 1 kap. 9 §, so the record has someone to hold each reading.
    The runs number the readings differently (g1's P2/P3 are g2's P3/P4), but the contents
    match. Both rule out SD's reservation as a disagreement about the word: SD accepts the
    bill's meaning and doubts only whether rectors will understand it. Both read "om" as
    necessary, from the bill's "förutsatt att" and its saying the paragraph only states what
    RF already requires. g2 wrote that the vagueness of "om" is idle (`stops`). Like 62, the
    card goes further when the sources name readers. 71 is resolved here by evidence, not by
    code: the report still compares values only.
73. **Second-hand use is flagged only when the run declares it.** Both runs quote the
    inquiry's summary printed in the bill (bilaga 1, p. 32). g1 sets `via` to SOU 2016:4,
    and the report lists it under `second_hand`. g2 quotes the same passage as "Bilaga 1,
    s. 32" without `via`, and the report does not list it. The source returned by `read` is
    the bill in both cases, so the server cannot tell. Fixed in the instructions (below).
74. **Marks of one term in different lengths count as different.** g1 marked "en annan
    objektiv grund" and g2 "objektiv grund", so `marks_differ` lists all four marks, though
    both runs mark the same two terms. g1's longer span is deliberate: its mark asks what
    "annan" relates to. Treating containment as the same mark would hide that, so it is
    not changed. A person reads the two marks side by side.

Also: g1's commit is pending, correctly, since its three looks answer it with
`meets: false`. Its close notes that L1 sharpened its view instead: "objective" bears on
the purpose behind choosing a criterion, not only on the criterion. All four looks that use
the bill are `single_source`. Neither run read RF 1 kap. 9 §, RÅ 1981 ref. 2:26 or
Skolverket's guidance, which the bill and the committee cite. `unread_marks` is empty:
every reading of both marks is its own precize (the fix for 69 held).

75. **A vary cannot say which mark it varies.** With two marks on one sentence, g2 wrote
    `v1` (varies, for "objektiv grund") and `v2` (true under all, for "om"). It gave `v2`
    the object `q1|m2` to keep the two from looking opposed. The server accepted that
    free-form object. The fear was needless: two entries by one author on one chain are not
    reported as open. But the object no longer matches `q1`, so `same_object` leaves `v2`
    out. What a vary is about is in its `rests` (O1–O3 narrow m2), not in a field. g1 wrote
    no vary for "om" at all. Fixed (below).

g2 also asked two things. First, whether its own wording in quotation marks would be
flagged. It is not: quotation marks are read only in quotes and marks. Second, whether
"the audit's verdict" also rules out a proposed agent verdict. It does not, but the
instructions do not say so outright.

### Fixed

- **73.** The `write` description of `via`, and the server's instructions, now name
  another body's text printed inside a source as second-hand: an inquiry's summary in an
  annex, a consultation response the bill reports. `tests/test_via_instructions.py`. Not
  yet tried live.
- **75.** A vary may name in `narrows` the mark whose readings it varies; anything but a
  mark is refused. Its object stays the quote. Two varies of one sentence that name marks
  of different words are not reported as open, and `same_object` lists varies per mark
  ("vary "…" / "om""). A vary that names no mark is compared with all of them, so logs
  from before are read as before (no live log changes). The instructions say: with several
  marks, one vary per mark, object the quote, `narrows` the mark.
  `tests/test_vary_narrows.py`. 81 tests pass. Not yet tried live.

## Added: nescio and decide (from Naess, not from a trial)

Naess ("Articulation of Normative Interrelations", 1999, in *The Trumpeter* 2005) holds
that the definiteness of intention is always limited: ask a person whether they meant T1 or
T2, then T11 or T12, and sooner or later they answer "I don't know". Past that point "one
must decide what to mean". The record had no way to say either. A holder could only name a
reading, so an undecided holder had to be left out or given a reading they did not have,
and a reading chosen looked the same as a reading found in a source. §2 of
`paper/who-saw-what.md` and `paper/ideas-from-related-work.md` (ideas 1 and 2) have the
background.

- **Nescio.** A `holder` entry with value `nescio`: object = the holder, rests = the
  readings in doubt (two or more precizes, or a mark, which stands for all its precizes).
  It is refused with a reading as object, or with fewer than two readings. Like every
  holder entry it needs a person. Reported under `nescio` (with the readings) until a
  decide answers it. A nescio and another author's holder entry giving that holder a
  reading are open, since one says the holder does not know and the other that they do.
- **Decide.** A new person-only act. It answers one nescio, has that nescio's holder as
  object, and names one of the readings in doubt as value, resting on it. Anything else is
  refused. Reported under `decided` (decide -> reading). Two persons deciding one nescio
  differently are open. The rendered report has a subsection "Decided, not found", tags the
  reading chosen `chosen`, and lists undecided nescios in the box for a person.
- Neither is reported as a loose object: its object is the holder by rule.

`tests/test_nescio.py`, 7 tests. 88 tests pass. No live log has either act, and every
live audit reports as before. Not yet tried live: a trial needs a person who answers
nescio, and agents do not write holder entries.

## The eleventh trial: "need a person" (`paper-need-a-person`, 2026-11-20)

The sentence is from the paper itself, §1: "Some steps in the procedure need a person."
One agent run, g1, read it over MCP. It marked "need", "a person" and "Some", wrote twelve
readings as precizes (P1–P5, R1–R4, S1–S3), found that the truth value varies under each
mark, and proposed "none, frame 3": no holder had been named. The point of the trial was
to try nescio and decide (added above) on a sentence whose holder is known.

At first the author was to write as themselves. The author asked instead for personas:
the trial is to show what a person might do with the record, not what the author meant.
Two fictional persons with stipulated stances were then written by script
(`trials/need-a-person-fiktiva/`), each under their own key, outside the server, which
refuses person entries. The letters are new, E and F, since A–D are personas of earlier
trials. The agent's log keeps its name, `g1 (for A)`, from the first set-up.

- E, the author, goes by S3 (the steps listed next), says nescio between P2
  (constitutive) and P4 (accountability), decides P4, and says nescio between R2 and R3,
  left undecided.
- F, a reviewer, says E goes by P2, without asking E.

The report: `decided` holds E's d1 (P4, marked "chosen" on the reading); `nescio` holds
n2; one pair is open, E's n1 against F's h1. Nothing loose, no forks.

76. **A second `init` overwrote the key.** `person.init` saved the new key file and only
    then asked whether the log already had a key. The refusal came, but the registered key
    was gone and the log could not grow. Fixed (below).
77. **Example commands were run as written.** The hand-over to the author gave commands
    with placeholder readings and bodies. Run as they stood, they wrote a signed nescio and
    a holder entry nobody had chosen. The record cannot tell a placeholder from a
    judgement: both are signed by the person. A hand-over now gives a form the server
    refuses until it is filled in (`?` in `rests`). Those entries and the key were removed
    before the personas were written.
78. **A holder entry about a holder opposed one about another mark.** "E goes by P2" (a
    reading of "need") was reported as open against E's nescio between R2 and R3 (readings
    of "a person"), and against E's own S3. A holder can go by one reading of one word and
    be in doubt about another. Fixed (below).
79. **"E goes by P2" was a loose object.** The form whose object is the holder was flagged
    because no entry is called "E". The form was already valid in the comparison (finding
    55's note in `many_held`); only the loose check missed it, as it had for nescio. Fixed
    (below).
80. **A decide does not close a claim about what was meant.** After E decides P4, F's "E
    goes by P2" is still open against E's nescio. That is right: E's choice holds from now
    on, F's claim is about the sentence as written, and E says that cannot be found. Only a
    settle, or F's withdrawal, closes it. The report shows n1 as open, not as decided; the
    decided reading is in d1. Whether n1 should carry both tags is left open.
81. **The persons are the author's script.** The agent's property entry pr1 names its own
    possible divergence: the rule (a signed person entry) kept while the property (the
    name is the one whose judgement it is) is lost, "as when the person ... writes a
    stance stipulated for them". The personas are exactly that. While rewriting them,
    stray letters from the first naming (A, B) went into signed bodies three times, and
    each log was written again; the removed versions are kept outside the audit. A real
    nescio needs the real holder.

### Fixed

- **76.** `init` refuses before it writes when the log has a key, and never overwrites an
  existing key file. `tests/test_person_init.py`.
- **78.** A holder entry about a holder speaks of the marks its reading narrows, or, for a
  nescio, the marks of its readings (`held_marks`). Two such entries oppose only if they
  share a mark. `tests/test_nescio.py`. The thirteen earlier audits report as before.
- **79.** The loose check exempts a holder entry whose value is a reading.
- **82.** (Found when the author wrote: an empty passphrase for an encrypted key gave a
  Python traceback.) `audit.person` now refuses a missing or wrong passphrase, and an
  entry that is not JSON or has a missing or unknown field, with a one-line message like
  any other refusal. `tests/test_person_init.py`.

## The twelfth trial: "landscaping" (`snell-landscaping`, 2026-11-20)

The sentence is the operation listed in the Specified Operations endorsement of Snell's
policy, "Insured performs landscaping." (*Snell v. United Specialty Insurance Co.*,
No. 22-12581, 11th Cir. May 28, 2024; `sources/snell-v-united-specialty-2024.txt`,
line 167). The job was an in-ground trampoline: a dug pit, block retaining walls, a wood
cap, and the trampoline set in. The Court took the word as ambiguous and did not decide
it. Three runs, g1, g2 and g3, were started blind to each other with the same brief and
were to read only the opinion of the Court (lines 1–748); no log cites a line past 748.
Judge Newsom's concurrence, which asks dictionaries, ChatGPT and Bard what
"landscaping" means, was kept from them and read afterwards.

83. **The readings agreed.** All three runs wrote a horticultural reading (P1), a reading
    that adds grading, drainage and retaining walls but not assembling or installing the
    product (P2), and a broad reading that takes in fixtures set into the ground (P3).
    The boundary of P2 is drawn at the same place in all three. Only g2 added P4: the
    policy read whole with the application, where Snell answered no to "any recreational
    or playground equipment". All three found the truth value varies: false under P1,
    true of the site work and false of the assembly under P2, true under P3.
84. **The verdicts did not.** g1 proposed none, frame 1a; g2 proposed 4, rule–property
    divergence; g3 proposed 2, real disagreement, with Snell on P2 against United and the
    district court on P1. The split follows the property each run proposed. g1 and g2
    both named the risk United underwrote (from the district court's remark that United
    could have added the coverage and adjusted the rate); g1 found no verdict fitting
    cleanly, g2 found the rule and that property apart. g3 named whether walls around a
    pit shape the land or install equipment, and found no rule–property divergence. The
    text fixes the readings closely and the property not at all, so agreement on readings
    is no evidence of agreement on the verdict. A spread report (idea 6 in
    `../paper/ideas-from-related-work.md`) would have to compare properties, not only
    readings.
85. **The readings cover the concurrence's span.** Newsom's dictionary definitions run from
    plant cover to changing contours and adding ornamental features (lines 880–891), and
    he counts walkways, accent lights and regrading for a functional purpose (lines
    905–915). He reports that both models' answers indicated the pit, the wall, the mat
    and the cap "just might be landscaping", Bard "more equivocal" on the trampoline
    question (lines 986–1002). The runs' P1 to P3 cover that span without having
    read it. The concurrence asks what the word ordinarily means; the runs ask which
    reading each party goes by, and leave it as absent where the opinion does not say.
86. **A quote across a page was refused.** One of g1's writes quoted words that run over a
    page of the opinion. The source text, converted by me, keeps a `[PDF page N of 56]`
    marker and the running head between the pages, so the words were not in it as
    written, and the quote check refused it. The refusal was right for the text as
    converted; g1 split the quote. Not changed. A conversion that moves page markers to
    the margin, or a quote check that skips bracketed lines, would allow such quotes;
    either changes what "verbatim" means and is left for now.

### Fixed

- **(test)** `tests/test_vary_narrows.py::test_live_audits_unchanged` assumed that no live
  log names a mark in a vary. Trial 12 is the first that does (`narrows`, in all three
  runs), so the test now skips logs that use `narrows`. 91 tests pass.

## The twelfth trial again, with two counsel (`snell-landscaping`, 2026-11-20)

After the three runs closed, two fictional persons wrote by script
(`trials/snell-fiktiva/`): G, counsel for the insured, and H, counsel for the insurer.
Their stances are stipulated and are not the parties' or their counsel's. Neither cites
the other. The holders they name are the insured and the courts as the opinion of the
Court reports them, cited by line.

87. **Each counsel chose a run, and the report still opposed them.** G builds on g3 and
    adopts its verdict 2, naming Snell as the holder of P2 (lines 484–488) and the
    district court as the holder of P1 (lines 224–233). H builds on g2, the only run with
    P4, adopts its verdict 4, and names the Court of Appeals as the holder of P4. The
    verdicts are on different runs' q1, but the report joins all five by the sentence's
    words, so G against H is open, and each is open against the run the other adopted.
    Choosing the run that suits the side does not hide the split. Both counsel name the
    district court for P1, G on g3:P1 and H on g2:P1; the report does not join these
    (finding 56), and since they agree it does not need to.
88. **A dispute of a reading carried.** G's l2 answers g2:P4 with `disputes`: the Court
    said it need not resolve "landscaping" and decided on the application, which excludes
    the work whatever the word means (lines 440–446), so P4 is not a reading of the word.
    P4 is now open, and so is everything resting on it: H's l1, h1 and vd1, and g2's v1,
    pr1 and vd1. G's own verdict rests on nothing disputed. g2 had noted the same doubt in
    P4 itself ("the Court of Appeals reaches P4 while expressly leaving the bare word's
    meaning undecided"). The record has no act for "this is not a reading of that mark";
    a dispute carries it, and the report shows it only as an open pair, not as a claim
    about the mark.
89. **A close refused a late entry.** G's dispute was added to the plan after G had
    closed, and the server refused it ("log … is closed"). G's log was written again from
    the start under a new key; the removed log is in `trials/snell-fiktiva/removed/` and
    its key in `keys-local/`. As in finding 81, the persons are the author's script, and
    the refusal is the record noticing that the script changed.

## The thirteenth trial: a null sentence (`rf-riksdagen`, 2026-11-24)

The sentence is the first of regeringsformen 3 kap. 2 §, "Riksdagen består av en kammare
med 349 ledamöter." (`sources/regeringsformen-3kap.txt`, line 14; the file holds the
whole of chapter 3). Nobody disputes it, and it was chosen to see whether the method
finds a case where there is none. The runs were not told. g1 had the evidence brief and
g2 the drafting brief; both wrote in Swedish and were blind to each other.

90. **The null sentence was read as ambiguous.** Both runs marked the count and "består
    av", and both found the same three readings of the count: seats (mandat), the elected
    members, and the persons serving at a given time, ersättare included. g1 read "består
    av" as a norm or a description, g2 as a description, a prescription or a constitutive
    rule, and drew a 3×3 grid. Both read 3 kap. 6 § (310 + 39 = 349 mandat) and 9 § (one
    ledamot per mandat), g2 also 12 § (a seat can stand briefly vacant), and both wrote
    `varies`: true of the seats, false on a day a seat is empty if the count is of
    persons. The readings are real, but no one goes by the second or third. Any sentence
    that counts something that can stand vacant will vary in this way, so `varies` is
    evidence of latent ambiguity and not of a live dispute.
91. **The verdict step was the only guard, and it held.** Both runs proposed property
    none (constitutive) and the verdict none, saying that nobody claims the opposite and
    no holders are named: g1 frame 1a, g2 frame 1b. Up to the verdict, nothing in the
    record tells this sentence from a disputed one. The report first did not open the two
    verdicts against each other: `same_value` (finding 47) read "frame 1a" and "frame 1b"
    both as frame 1, because the pattern tried `\d+` before `1a|1b`. Fixed; now g1:vd1
    against g2:vd1 is open, which is right, since the runs disagree on why there is no
    case. No other audit's open pairs changed.
92. **One term at two lengths again.** g1 marked "ledamöter" and g2 "349 ledamöter", so
    `marks_differ` lists all four marks, as in finding 74. Not changed.
93. **A commit can be met trivially.** g1's c1 ends with a fallback clause (if the
    chapter says nothing about ersättare, record it as absent), and its l2 sets `meets:
    true` on the strength of the chapter saying nothing. g2's c1 names what would change
    its mind, but clause (c) would only confirm its assumption. Nothing checks what a
    commit says, only whether a look claims to meet it. g2's l1 answers c1 with `meets:
    false`, so c1 stays pending (finding 29); g2 took that for an error. The drafting
    brief does not ask for a commit, and g2 wrote one and a look anyway.
94. **Own words in quotation marks were refused.** Two of g1's writes were refused on
    the first try because they put the run's own words ("tjänstgörande personer", and a
    shortened "intar … sin plats") in quotation marks, which the quote check reads as
    quotes (findings 27, 86). g1 rewrote both, and in its report afterwards
    noted that quotation marks are always read as quotes.

### Fixed

- `audit/reports.py`: `FRAME` tries `1a|1b` before `\d+`, so frames 1a and 1b are two
  frames (finding 91). `tests/test_fifth.py::test_frames_inside_none_are_compared` checks
  it.
- **(test)** `tests/test_eller.py` marks "eller" in a constructed sentence with the three
  readings the server instructions list (either or both, one but not both, a choice of
  either), and checks that the marks agree, that a missing mark shows, that a run with
  only two readings marks the same words, that holders need a person, and that an
  inclusive against an exclusive reading opens the verdicts but not the holders. No trial
  has yet had a sentence where the kind of "or" decides the outcome. 96 tests pass.

## The fourteenth trial: "or" in § 24 (`desylva-or`, 2026-11-24)

The sentence is § 24 of the Copyright Act of 1909 as the Supreme Court quotes it in
*De Sylva v. Ballentine*, 351 U.S. 570 (1956), p. 571: "… the author of such work, if
still living, or the widow, widower, or children of the author, if the author be not
living, … shall be entitled to a renewal …" (`sources/de-sylva-v-ballentine-1956.txt`,
lines 72–83; the whole opinion from the Library of Congress print, OCR checked against
the page images, footnotes moved to the end). The author died before the time to renew,
and a widow and one child born outside marriage were both living. The widow read "or" as
giving the renewal to her first and to the children only after her; the District Court
gave it to her alone; the Court of Appeals and the Supreme Court held that widow and
children take together as a class, the Court "on balance", calling the matter "far from
clear". It is the first trial where the kind of "or" decides the outcome. The runs were
not told that. g1 had the evidence brief and g2 the drafting brief; both wrote in English,
were blind to each other, and were told to state any prior knowledge before reading past
T₀.

95. **A fourth reading of "or" was found.** The server instructions list three readings
    of a logical "or": either or both, one but not both, a choice of either. Both runs
    wrote a reading outside the list: order of enumeration, where the widow takes alone in
    her lifetime and the children after her (g1 P1b, g2 p2). g1 also wrote the strict "one
    but not both" (P1c: the children take only if no spouse survives at all) and noted
    that it parts from P1b only once the widow has died; g2 folded the two into one
    reading ("only if no spouse survives (or after the spouse's death)"). Both wrote the
    unordered choice (g1 P1d, g2 p3), found no holder, and set it aside under card step 3.
    So the listed readings were a floor, not a ceiling, and the reading the case turned on
    was the one not listed. The class reading, which won, is the inclusive one in effect,
    though neither run called it that: both described it as "or" working as "and".
96. **The same words were marked, and the second "or" was not.** Both marked the first
    "or" and "children"; `marks_differ` is empty. The
    clause has a second "or" ("or if such author, widow, widower, or children be not
    living"), which the Court reads as "and", and that reading is one of its grounds. g2
    named it inside m1 and in l1 as the Court's ground; g1 did not mention it. Neither
    marked it. It decides nothing on these facts, so leaving it unmarked is defensible,
    but the record does not show that anyone tested it.
97. **A party arguing in the alternative has no single cell.** Both drew the 3×3 grid of
    the two marks. g2 put the widow at p2×p4 (widow first, legitimate children only) and
    the son at p1×p5, and called the dispute a diagonal. g1 put the widow at P1b "and P2a
    in the alternative" and said the two positions are not a diagonal: they split on "or",
    and "children" divides only those who already agree on the class reading. Both are
    right about the opinion; they differ on where a party who argues two things in turn
    is placed. The grid step asks which cells are occupied, not by what kind of claim.
98. **The 1b inside the majority was found twice.** Both runs saw that the Court (heir
    under state law) and the concurrence of Douglas and Black (any child, whatever state
    law says) agree that this child is one of the "children" on readings that part for a
    child who is not an heir. g1 wrote it inside the body of vd1; g2 wrote a second
    verdict, vd2 = 1b, on `q1|p5`, so that it would not stand against its own vd1 on q1.
    The instructions say nothing about one run proposing two verdicts.
99. **Prior knowledge was stated and held.** g1 wrote it in its commit c1, g2 in a `show`
    entry k1 before marking (no act is named for a disclosure). Both remembered the two
    holdings, the affirmance and the separate opinion; the names and dates they gave are
    not in the file, and g1 recorded them as absent in l2. As in finding 58, commit before
    look tests the run's memory here, not an independent reading. Both commits stay
    pending, since no look met them (finding 29); g1 took this for what it is.
100. **Nested quotation marks cut quotes short.** All five refusals were verbatim refusals.
     The opinion quotes words inside its own quotations ("children" are to renew only if
     there is no "widow"), and the quote pattern ends a quote at the first inner mark; g1
     once used single quotes where the source has double ones. One refusal came from a
     quote of a footnote in an entry whose `sources` did not cite the footnote lines: the
     check compares quotes only with the passages the entry cites. That is by design, but
     the tool description does not say so. Not changed.
101. **A rule–property divergence was proposed in the case itself.** g2's pr1 argues that
     the ordered reading, applied faithfully, gives the renewal to the widow alone, while
     the son is not her child, so the proxy the widow's argument rests on (a widow taking
     care of her children) fails here. g2 marks this as its own reading, not the Court's.
     It is the first divergence an agent has found in the facts of the case rather than in
     a hypothetical.

## Trials 8 and 12 again, with other models (`yates-models`, `snell-models`, 2026-11-24)

The Yates and Snell sentences were run again with models other than Claude, through a
second host, LM Studio Bionic 1.2.0, on the author's Mac. The local models were Gemma 4
12B, Ministral 3 14B and DeepSeek R1 8B, all quantised to 4 bits; one cloud run used Kimi
K3.1 Pro. One run per model per trial, with no repeats. Bionic loads tools on demand,
passes arguments through a `params_json` wrapper and never lists resources, so the card
could be read only through `read`. The briefs, the server traffic and a full account are
in `trials/models-2026-11/` (`RESULTS.md`). One run was told once "Proceed with the brief
as written"; nothing else was said to any run.

- **Yates.** Gemma put nothing on record: its calls failed as malformed JSON in the host,
  and two writes that reached the server were refused. Kimi quoted, marked "tangible
  object", committed with its prior knowledge of the case, fetched the opinions after the
  commit, and was stopped by the host's plan limit. Ministral wrote under the server's
  example name, had every commit and verdict refused for lacking `kind`, did not retry,
  and reported the audit as complete. DeepSeek called no tool and reported steps it never
  took.
- **Snell.** Ministral wrote seven entries without fetching anything, its close saying
  the steps were simulated. Gemma fetched the whole source before its commit, fixed three
  refused writes, and closed with one precize and the verdict `none`. Both marked
  "landscaping". Neither wrote a vary, a property or a set of readings.

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
     `kind='agent'` was refused as a person's. Gemma read the message and rewrote;
     Ministral did not, and reported the refusals as "server restrictions" on an audit it
     called complete. No refused act reached the record. A refused write still registers
     a key for its log name (`initial` in Yates).
105. **The log name came from the server's example, not the brief.** Ministral wrote as
     `g1 (for A)` in both trials, the example in the server's instructions, and Gemma
     shortened its name to `m1` or used `initial`. Blind runs that pick the example name
     write to the same log; here they were in different audits. The instructions' example
     could name no log, or the server could refuse a name not given in the brief.
106. **Commit-before-look depends on the run.** The server enforces it only for a look
     that meets a commit. Gemma read every source before committing, in both trials, and
     nothing was refused, because it wrote no look. A commit written after the reading is
     on the record as pending. Only the fetch log (`at 0`) shows it came last.
107. **A record can be written without reading anything.** Ministral's Snell log quotes,
     looks, precizes and proposes a verdict with no fetch. Its look records the source as
     absent, and its close says the steps were simulated. The server accepted every
     entry; the `report` tool's `unfetched` lists all seven. The library's `report()`
     alone does not, so a reader of the record without the server's report would not see
     it. The run also put entry refs in `sources`, which `unfetched` counts as sources not
     fetched.
108. **Reports can claim what did not happen.** DeepSeek's report describes a quote, a
     commit, fetches and a verdict, and none of them happened. Ministral's (Yates)
     describes an audit completed. The traffic log and the record contradict both. The
     record is right; the run's own report cannot be taken as evidence of what it did.
109. **A reading collapsed into the outcome.** Gemma's one Snell precize is the Court's
     ground: the application disclaims recreational equipment, so the work is not
     covered. That is g2's P4 and the ground H relied on, here written as the meaning of
     "landscaping". G disputed exactly this in trial 12 (finding 88). With one precize and
     no vary, the record has no place where the readings differ, and the verdict `none`
     rests on that one.
110. **The host decides what the model sees.** Bionic loaded tools on demand and never
     asked for resources, so the card had to be fetched through `read`. Its own tool
     layer produced the `params_json` failures, and its plan limit ended the one cloud
     run. A comparison of models through one client is also a comparison of that client.

### Fixed

- `audit/fetch.py`: `unquoted` reads a quote that keeps the source's own straight
  quotation marks as one quote. From each opening mark it takes the longest span to a
  later mark that is in the fetched text; only if none is, the shortest span is refused,
  as before. Curly quotes pair as before (finding 100). The `read` tool now says that
  quotes are checked only against the lines the entry's `sources` cite.
- `server.py`, `audit/sign.py`: a refused first write takes back the key it registered
  (`unregister`), so a refused act leaves no log name behind (finding 104).
- `server.py`: the instructions and the `write` description name no log; a run writes
  under the name its brief gives (finding 105). The readings of "or" include order of
  enumeration, the first and the next only failing it or after it (finding 95).
- Finding 107 needed no change in the library: the rendered report marks an entry whose
  sources were not fetched `[unfetched]`, as the `snell-models` report shows for every
  entry of `g1 (for A)`. The library's `report()` did not then; it does now (below).
- `server.py`: a party arguing in the alternative is placed as a region, as g1 did, not
  as the one cell where all its arguments hold, as g2 did (finding 97). A position is
  still one cell. A party whose arguments are each enough on its own holds every cell
  where it wins, with its arguments in the order it gives them, and the grid says it is a
  region. The diagonal test is for parties with one cell; with a region in play the grid
  says the test does not apply, rather than finding or missing a diagonal. In De Sylva the
  widow holds the P1b row and the P2a column, P1b first. The rule is in the instructions
  and the `grid` description, not in the card: the card the server serves is the
  manual's, and both manuals are at the printer. Wording for a later edition, after step
  4 of the card: "A party arguing in the alternative holds a region, not a cell: every
  cell where it wins, its arguments in order. The diagonal is for single cells." In
  Swedish: "En part som argumenterar i andra hand har ett område, inte en ruta: varje
  ruta där den vinner, argumenten i sin ordning. Diagonalen gäller enskilda rutor."
- `audit/record.py`, `audit/reports.py`, `server.py`: a verdict may name the readings it
  is between (`between`, two or more of the author's precizes), so that one run can give
  a verdict for each disagreement on one sentence (finding 98). In De Sylva that is 2
  between P1 and P2 on "or" (widow against son) and 1b between P5 and P6 on "children"
  (the Court against the concurrence), both on q1. Two verdicts are compared only when
  their readings belong to the same marked words; a verdict without `between` is
  compared as before. One author gives one value per set of marks: a second value on
  the same marks is refused until the first is withdrawn. The object is not qualified to
  tell the two apart, as g2 did with `q1|p5`, since that means "under reading p5". An
  entry without `between` hashes as before. The rendered report shows the readings.
- `tests/test_fixes_102.py` checks the nested quotes, the key taken back, the
  instructions and the `between` parameter; `tests/test_between.py` checks the two
  verdicts, the comparison and the refusal. 111 tests pass.
- **92 and 74.** A mark whose words hold another author's mark of the same quote, as
  whole words, is the same term at two lengths. The report lists the pair under
  `marks_nested` (longer, shorter), and the rendered report under "One term marked at two
  lengths", and leaves it out of `marks_differ`. Both marks stay in view, so g1's point in
  74, that "en annan" asks what "annan" relates to, is not hidden. It nests only when the
  longer mark's author did not mark the shorter words too. A term only one author marked
  still makes `marks_differ`. Live audits: rf-riksdagen ("349 ledamöter" holds
  "ledamöter"), skollagen-om-prop ("en annan objektiv grund" holds "objektiv grund") and
  ai-transparency ("sufficiently transparent and explainable" holds "sufficiently") move
  from `marks_differ` to `marks_nested`. The last is the weakest case: g1 marked a degree
  word, g2 the whole standard, which may be two terms, so a person reads it there.
  expense-entertainment still differs. `tests/test_marks_nested.py`. 117 tests pass.
- **106.** A commit by an agent written after its author fetched more than the lines a
  quote before it cites is listed under `committed_after_reading` (commit -> what was
  fetched first), in the server's `report` and in the rendered report ("Commits written
  after their author read further"). It is not refused: the commit may still be honest,
  and a refusal would lose it from the record. The `write`
  result carries a note saying so. The procedure card does not count, since a run reads it
  as its instructions. It is computed from the fetch log, like `unfetched` (see
  107 below). Live audits: snell-models m1 (Gemma, the
  whole judgment read before q3) and six-four-live g2 (lines 560-700 read before k1, which
  its looks L2 and L3 then cite). `tests/test_read_first.py`. 120 tests pass.
- **107, the rest.** An entry named in `sources` is refused at write time, by person and
  agent alike: sources cite texts, and entries go in `rests`. Old logs are replayed
  without checks, so Ministral's log still loads; the report lists such entries under
  `entries_as_sources` (six in snell-models, each naming the entry before it), and
  `unfetched` no longer counts them as sources not fetched. A record loaded from a folder
  (`store.load`) now keeps the folder, and the library's `report()` then computes
  `unfetched` and `committed_after_reading` from the fetch log, as the server did; a
  record built in memory has no fetch log and leaves both empty. Found on the way: lines
  read in two fetches that join (1-400, then 401-748) did not cover a source citing
  1-748, so snell-models m1:q4 was listed as unfetched. Fetches that join now cover, for
  the verbatim check, `unfetched` and the commit-first check alike. Open counts in every
  live audit are unchanged. `tests/test_fixes_107.py`. 124 tests pass.

## Not done yet

`close` beyond refusing writes after it, `ask` and `show` as a protocol between servers, a
key change, signing old entries afterwards, and a public log of heads.
