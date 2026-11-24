"""Finding 106: a commit written after its author fetched more than the quoted lines is
listed (committed_after_reading), not refused. The quote's own lines and the procedure
card do not count."""
import pytest

from audit import Entry as E, Record, fetch

LINES = ["The insured performs landscaping.", "The claim concerns a trampoline.",
         "Landscaping is not defined in the policy."]


def build(tmp_path, read_more_first: bool):
    f = tmp_path / "a"
    r, log = Record(), "g1 (for A)"
    at = 0
    fetch.note(f, log, fetch.CARD, 1, 109, "card", at)
    fetch.note(f, log, "op.txt", 1, 1, LINES[0], at)
    if read_more_first:
        fetch.note(f, log, "op.txt", 2, 3, "\n".join(LINES[1:]), at)
    r.add(log, E("q1", "quote", '"The insured performs landscaping."', kind="agent",
                 sources=["op.txt, lines 1-1"]))
    r.add(log, E("m1", "mark", '"landscaping"', kind="agent", value="landscaping", rests=["q1"]))
    r.add(log, E("c1", "commit", "a definition in the policy would change my mind",
                 kind="agent", about="q1"))
    if not read_more_first:
        fetch.note(f, log, "op.txt", 2, 3, "\n".join(LINES[1:]), 3)
    return f, r


def test_commit_before_reading_is_not_listed(tmp_path):
    assert fetch.read_first(*build(tmp_path, False)) == {}


def test_commit_after_reading_is_listed(tmp_path):
    assert fetch.read_first(*build(tmp_path, True)) == {"g1 (for A):c1": ["op.txt, lines 2-3"]}


def test_server_notes_it_on_write(tmp_path):
    pytest.importorskip("mcp")
    import server
    from test_server import data, run
    root = tmp_path / "src"
    root.mkdir()
    (root / "op.txt").write_text("\n".join(LINES) + "\n")
    server.ROOT = root

    async def steps(c):
        def call(tool, **kw):
            return c.call_tool(tool, {"audit": "t", **kw})
        s = data(await call("read", log="r1", path="op.txt", start=1, end=1))["source"]
        await call("read", log="r1", path="op.txt", start=2, end=3)
        await call("write", log="r1", kind="agent", id="q1", act="quote",
                   body='"The insured performs landscaping."', sources=[s])
        w = data(await call("write", log="r1", kind="agent", id="c1", act="commit",
                            body="a definition would change my mind", about="q1"))
        rep = data(await call("report"))
        return w, rep
    w, rep = run(tmp_path, steps)
    assert "op.txt, lines 2-3" in w["note"]
    assert rep["committed_after_reading"] == {"r1:c1": ["op.txt, lines 2-3"]}
