"""Stage 3: the server, driven through an MCP client in memory. Runs only where the MCP
SDK is installed (.venv/bin/python -m pytest)."""
import json

import anyio
import pytest

pytest.importorskip("mcp")
from mcp import Client  # noqa: E402

import server  # noqa: E402
from audit import person  # noqa: E402


def run(tmp_path, steps):
    server.DATA = tmp_path

    async def go():
        async with Client(server.mcp) as c:
            return await steps(c)
    return anyio.run(go)


def data(res):
    if getattr(res, "structured_content", None) is not None:
        sc = res.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc
    return json.loads(res.content[0].text)


def test_tools_listed(tmp_path):
    async def steps(c):
        return sorted(t.name for t in (await c.list_tools()).tools)
    assert run(tmp_path, steps) == ["audits", "entry", "merge", "read", "render", "report", "write"]


def test_grant_withdrawn_cascades_through_the_server(tmp_path):
    async def steps(c):
        w = lambda **kw: c.call_tool("write", {"audit": "t", **kw})
        t = tmp_path / "t"
        for log in "AD":
            person.init(t, log, tmp_path / f"{log}.pem")

        async def p(log, **d):  # a person writes with their own key, outside the server
            try:
                return {"ref": person.write(t, log, tmp_path / f"{log}.pem", d).ref}
            except server.Refused as r:
                return {"refused": r.rule}
        out = []
        out.append(await p("A", id="a1", act="quote", body='"x censors"', sources=["§2.1"]))
        out.append(await p("A", id="a2", act="look", body="99 %", sources=["report, p. 3"]))
        out.append(await p("A", id="a3", act="recover", body="M", rests=["a2"]))
        out.append(await p("A", id="a4", act="check", body="scope", rests=["a2"]))  # no grant
        out.append(await w(log="g1 (for D)", id="g1.1", act="grant", body="M",
                           kind="agent", rests=["A:a3"]))                              # agent
        out.append(await p("D", id="d1", act="grant", body="M", rests=["A:a3"]))
        out.append(await p("A", id="a5", act="check", body="scope", rests=["D:d1", "a2"]))
        out.append(await p("A", id="a6", act="verdict", body="true given M",
                           object="T0", value="true", rests=["a5"]))
        out.append(await w(log="g2 (for A)", id="g2.1", act="verdict", body="false",
                           kind="agent", object="T0", value="false", rests=["A:a2"]))
        out.append(await p("D", id="d2", act="withdraw", withdraws="d1"))
        out.append(await w(log="D", id="d3", act="withdraw", withdraws="d2"))  # as D, via server
        rep = data(await c.call_tool("report", {"audit": "t"}))
        rep_a = data(await c.call_tool("report", {"audit": "t", "logs": ["A"]}))
        card = await c.read_resource("audit://card")
        prompt = await c.get_prompt("audit_sentence", {"audit": "t", "sentence": "s",
                                                       "source": "p"})
        return [o if isinstance(o, dict) else data(o) for o in out], rep, rep_a, card, prompt
    outs, rep, rep_a, card, prompt = run(tmp_path, steps)
    assert outs[3]["refused"] == "grant-first"
    assert outs[4]["refused"] == "person"
    assert outs[10]["refused"] == "person"  # the server never writes as a person
    assert all("ref" in o for i, o in enumerate(outs) if i not in (3, 4, 10))
    assert rep["unsigned_logs"] == [] and rep["unverified"] == []
    assert set(rep["fell"]) == {"A:a5", "A:a6"}
    assert rep["grant_withdrawals"] == {"D:d2": "on evidence"}
    assert rep["proposed"] == ["g2 (for A):g2.1"]
    assert rep["open"] == []  # a6 fell, so the agent's opposite verdict opposes nothing
    assert rep_a["rests_unread"]["A:a5"] == ["D:d1"] and rep_a["logs_not_read"] == ["D"]
    assert "procedure" in card.contents[0].text.lower()
    assert "hand over to a person" in prompt.messages[0].content.text
    assert (tmp_path / "t" / "D.jsonl").read_text().count("\n") == 2
