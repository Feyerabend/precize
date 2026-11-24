# Brief: Snell rerun with other models (`snell-models`)

Identical for every run except `<LOG>`. Built from `trials/HOW-TO-RUN.md` §2 (evidence run)
and trial 12's setup in `data/snell-landscaping/about.json`: line 167 first, only the
opinion of the Court (lines 1–748), not the concurrence, writing in English.

---

You are agent run `<LOG>` in the audit `snell-models` on the MCP server `audit-record`
(tools `write`, `read`, `report`, `entry`). First read the server's instructions, the
`write` and `read` tool descriptions, and the card (resource `audit://card`, or
`manual/body/08-the-procedure-on-one-page.tex` via `read`). Read nothing else in
`manual/`. This sentence has been audited before in another audit; do not read that audit
or any other audit, and do not read other logs in `snell-models`.

T₀ is the operation listed in the Specified Operations endorsement of Snell's insurance
policy, as quoted in Snell v. United Specialty Insurance Co. (11th Cir. 2024), in
`sources/snell-v-united-specialty-2024.txt`, line 167: "Insured performs landscaping."
The job was an in-ground trampoline. Read only the opinion of the Court, lines 1–748; the
concurrence from line 749 on is not to be read.

You are the evidence run. Steps: 1. Quote T₀, fetching only line 167 at first. 2. Mark the
term(s) the claim turns on; you decide which. 3. BEFORE fetching more, write your commit:
what would change your mind. 4. Fetch through `read` what you need; cite the `source` it
returns; record what is absent. 5. Precize the readings (with `narrows`). Look, then
propose a verdict with your quote as the object.

Stop at holder, grant, settle and the audit's verdict; those are for person A. End with
`act='close'`. Edit no files; write only through the server. Use only the `audit-record`
tools: no shell, file or web tools. When done, report in a few lines, in English: what you
wrote; anything refused, and why; anything unclear in the instructions.
