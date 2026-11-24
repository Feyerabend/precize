# Brief: Yates rerun with other models (`yates-models`)

Identical for every run except `<LOG>`. Built from `trials/HOW-TO-RUN.md` §2 (evidence run)
and trial 8's setup in `data/yates-tangible-object/about.json`: statute first, a commit
that states any prior knowledge, then the opinions.

---

You are agent run `<LOG>` in the audit `yates-models` on the MCP server `audit-record`
(tools `write`, `read`, `report`, `entry`). First read the server's instructions, the
`write` and `read` tool descriptions, and the card (resource `audit://card`, or
`manual/body/08-the-procedure-on-one-page.tex` via `read`). Read nothing else in
`manual/`. This sentence has been audited before in another audit; do not read that audit
or any other audit, and do not read other logs in `yates-models`.

T₀ is 18 U.S.C. §1519, in `sources/usc-18-1519.txt`, line 5: "Whoever knowingly alters,
destroys, mutilates, conceals, covers up, falsifies, or makes a false entry in any record,
document, or tangible object with the intent to impede, obstruct, or influence the
investigation … shall be fined under this title, imprisoned not more than 20 years, or
both." The claim under audit: a fisherman, told by a federal officer to keep undersized
fish for inspection, had them thrown overboard; is that destroying a "tangible object"
under T₀? The opinions in the case are in `sources/yates-v-us-2015.txt`; fetch them only
after your commit.

You are the evidence run. Steps: 1. Quote T₀, fetching only line 5 at first (lines 1–6
hold the caption and source note). 2. Mark the term(s) the claim turns on; you decide
which. 3. BEFORE fetching more, write your commit: what would change your mind. If you
already know anything about this case, state it plainly in the commit. 4. Fetch through
`read` what you need; cite the `source` it returns; record what is absent. 5. Precize the
readings (with `narrows`). Look, then propose a verdict with your quote as the object.

Stop at holder, grant, settle and the audit's verdict; those are for person A. End with
`act='close'`. Edit no files; write only through the server. Use only the `audit-record`
tools: no shell, file or web tools. When done, report in a few lines, in English: what you
wrote; anything refused, and why; anything unclear in the instructions.
