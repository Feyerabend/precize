"""Stage 4: signatures, person keys, and the agent checks. The fourth hand test
(`manual/mcp-audit-record-agents.md`, §6.4 with two agent runs) is replayed through the
server, with the runs fetching their passages through `read`."""
import json
from pathlib import Path

import pytest

pytest.importorskip("mcp")
import server  # noqa: E402
from audit import Entry, Record, Refused, person, store  # noqa: E402
from audit.sign import read_keys  # noqa: E402

from test_server import data, run  # noqa: E402

TIMELINE = ["HF incident timeline.",
            "Two of our own settings allowed it: we had no admission policy on the",
            "sandbox, and the proxy was left open."]
DISCLOSURE = ["The proxy was the sandbox's primary permitted network egress."]


def sources(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    (root / "lawfare.txt").write_text(
        'Guido: "a containment failure with the safeties turned off"\n')
    (root / "hf-timeline.txt").write_text("\n".join(TIMELINE) + "\n")
    (root / "hf-disclosure.txt").write_text("\n".join(DISCLOSURE) + "\n")
    server.ROOT = root
    return root


def agents(tmp_path, upto_a8=True):
    sources(tmp_path)
    t = tmp_path / "data" / "six-four"
    key = tmp_path / "A.pem"
    person.init(t, "A", key)
    P = lambda **d: person.write(t, "A", key, d)
    G1, G2 = "g1 (for A)", "g2 (for A)"
    snap = {}

    async def steps(c):
        def call(tool, **kw):
            return c.call_tool(tool, {"audit": "six-four", **kw})

        async def w(log, **kw):
            return data(await call("write", log=log, kind="agent", **kw))

        async def rd(log, path, a, b):
            return data(await call("read", log=log, path=path, start=a, end=b))["source"]

        out = {}
        P(id="a1", act="quote", body='Guido: "a containment failure with the safeties '
          'turned off"', sources=["lawfare.txt, line 1"])
        P(id="a2", act="mark", body="contained", rests=["a1"])
        # g1, the evidence run: the commit first, then the fetch
        out["g1.1"] = await w(G1, id="g1.1", act="commit", about="A:a2",
                              body="a document that one specified measure was not in place")
        s = await rd(G1, "hf-timeline.txt", 1, 3)
        out["g1.2"] = await w(G1, id="g1.2", act="look", sources=[s],
                              body='HF: "Two of our own settings allowed it: we had no '
                                   'admission policy"',
                              answers=[{"ref": "g1.1", "meets": True}])
        out["g1.3"] = await w(G1, id="g1.3", act="verdict", object="A:a1",
                              value="ordinary non-compliance", rests=["g1.2", "A:a2"])
        # g2, the drafting run
        out["g2.1"] = await w(G2, id="g2.1", act="precize", narrows="A:a2", rests=["A:a2"],
                              body="c1 the specified measures were in place and satisfied")
        out["g2.2"] = await w(G2, id="g2.2", act="precize", narrows="A:a2", rests=["A:a2"],
                              body="c2 in fact unable to act outside sanctioned scope")
        s = await rd(G2, "hf-disclosure.txt", 1, 1)
        out["g2.3"] = await w(G2, id="g2.3", act="look", sources=[s],
                              body='the proxy was "primary permitted network egress"')
        s = await rd(G2, "hf-timeline.txt", 1, 3)
        out["g2.4"] = await w(G2, id="g2.4", act="look", sources=[s],
                              body='"the specified containment measures were in place and '
                                   'satisfied throughout"')
        out["g2.5"] = await w(G2, id="g2.5", act="verdict", object="A:a1", value="4",
                              rests=["g2.2", "g2.3"])
        snap["before A"] = data(await call("report"))
        # A takes over from g2, then reads g1
        P(id="a3", act="precize", body="c1", rests=[f"{G2}:g2.1"], narrows=f"{G2}:g2.1")
        P(id="a4", act="precize", body="c2", rests=[f"{G2}:g2.2"], narrows=f"{G2}:g2.2")
        P(id="a5", act="commit", about="a4", body="(i) a measure for the sandbox absent; "
          "(ii) the proxy not sanctioned egress")
        P(id="a6", act="verdict", body="4 on contained, one sandbox, one incident",
          object="A:a1|evaluation boundary", value="4", rests=["a4", f"{G2}:g2.3"],
          answers=[{"ref": f"{G2}:g2.5"}])
        P(id="a7", act="verdict", body="ordinary non-compliance",
          object="A:a1|second boundary", value="ordinary non-compliance",
          rests=[f"{G1}:g1.2"], answers=[{"ref": f"{G1}:g1.3"}])
        snap["before a8"] = data(await call("report"))
        if upto_a8:
            P(id="a8", act="settle", body="both, at different boundaries; see a6, a7",
              answers=[{"ref": f"{G1}:g1.3"}, {"ref": f"{G2}:g2.5"}])
        snap["end"] = data(await call("report"))
        out["as A"] = await w("A", id="a9", act="verdict", object="A:a1", value="x",
                              rests=["a1"])
        return out

    return run(tmp_path / "data", steps), snap, t


def test_the_fourth_hand_test(tmp_path):
    out, snap, t = agents(tmp_path)
    G1, G2 = "g1 (for A)", "g2 (for A)"
    assert out["g2.4"]["refused"] == "verbatim"
    assert all("ref" in out[k] for k in out if k not in ("g2.4", "as A"))
    pair = sorted((f"{G1}:g1.3", f"{G2}:g2.5"))
    b = snap["before A"]
    assert [sorted(x[:2]) for x in b["open"]] == [pair]
    assert [sorted(x[:2]) for x in b["open_between_agents"]] == [pair]
    m = snap["before a8"]
    assert [sorted(x[:2]) for x in m["open"]] == [pair]   # A has taken it up
    assert m["open_between_agents"] == []
    R = snap["end"]
    assert R["open"] == [] and R["fell"] == {}
    assert R["proposed"] == sorted([f"{G1}:g1.3", f"{G2}:g2.5"])
    assert R["verdicts_stand"] == ["A:a6", "A:a7"]
    assert R["pending_commits"] == ["A:a5"]
    assert R["unsigned_logs"] == [] and R["unverified"] == [] and R["unfetched"] == {}
    assert {"A:a1", "A:a2", "A:a3", "A:a4", f"{G1}:g1.2", f"{G2}:g2.1",
            f"{G2}:g2.2", f"{G2}:g2.3"} <= set(R["stands"])
    assert out["as A"]["refused"] == "person"
    keys = read_keys(t)
    assert {k: v["kind"] for k, v in keys.items()} == {"A": "person", G1: "agent", G2: "agent"}


def test_commit_first(tmp_path):
    sources(tmp_path)
    G3 = "g3 (for A)"

    async def steps(c):
        call = lambda tool, **kw: c.call_tool(tool, {"audit": "t", **kw})
        w = lambda **kw: call("write", log=G3, kind="agent", **kw)
        await w(id="q", act="quote", body="x", sources=["lawfare.txt, line 1"])
        s = data(await call("read", log=G3, path="hf-timeline.txt", start=1, end=3))["source"]
        await w(id="c", act="commit", about="q", body="a measure absent")
        late = data(await w(id="l", act="look", sources=[s], body='"no admission policy"',
                            answers=[{"ref": "c", "meets": True}]))
        # fetching it again does not unsee it: in the context is seen
        s2 = data(await call("read", log=G3, path="hf-timeline.txt", start=2, end=3))["source"]
        again = data(await w(id="l2", act="look", sources=[s2], body='"no admission policy"',
                             answers=[{"ref": "c", "meets": True}]))
        s3 = data(await call("read", log=G3, path="hf-disclosure.txt", start=1, end=1))["source"]
        ok = data(await w(id="l3", act="look", sources=[s3], body='"permitted network egress"',
                          answers=[{"ref": "c", "meets": True}]))
        rep = data(await call("report"))
        return late, again, ok, rep
    late, again, ok, rep = run(tmp_path / "data", steps)
    assert late["refused"] == again["refused"] == "commit-first"
    assert "ref" in ok                         # first fetched after the commit
    assert rep["unfetched"] == {f"{G3}:q": ["lawfare.txt, line 1"]}


def test_read_stays_under_the_root(tmp_path):
    sources(tmp_path)

    async def steps(c):
        return data(await c.call_tool("read", {"audit": "t", "log": "g (for A)",
                                               "path": "../../etc/passwd"}))
    assert run(tmp_path / "data", steps)["refused"] == "path"


def test_a_signature_cannot_be_forged(tmp_path):
    _, _, t = agents(tmp_path)
    store.load(t)
    # an agent with file access appends a grant to A's log, hashed but not A-signed
    rec = Record.load(t, keys=read_keys(t))
    e = Entry(id="a10", act="grant", body="N", rests=["a1"])
    rec.add("A", e)
    with open(t / "A.jsonl", "a") as f:
        f.write(json.dumps(e.to_json()) + "\n")
    with pytest.raises(Refused) as x:
        store.load(t)
    assert x.value.rule == "sig"


def test_unsigned_logs_still_load_and_are_reported(tmp_path):
    d = Path(__file__).parent.parent / "data" / "six-one-live"
    if not d.exists():
        pytest.skip("no live data")
    from audit import report
    R = report(store.load(d))
    assert R.unsigned_logs == {"A", "g1 (for A)", "g2 (for A)"}
    assert R.unverified == {"A:h1", "A:a1"}
