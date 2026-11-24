"""The fix round after the third trial (findings 26, 27, 30)."""
from pathlib import Path

import pytest

pytest.importorskip("mcp")
import server  # noqa: E402
from audit import store  # noqa: E402
from audit.fetch import plain  # noqa: E402

from test_server import data, run  # noqa: E402

TEX = ["His words were \\emph{powerful AI systems can go",
       "rogue}.\\footnote{Quoted in Klonick, \\emph{Lawfare}; see \\S\\ref{sec:B.3}.}",
       "% a comment that is not text",
       "Guido calls it \\emph{a containment failure with the safeties turned",
       "off}."]


def setup(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    (root / "s.tex").write_text("\n".join(TEX) + "\n")
    server.ROOT = root


def test_plain():
    t = plain("\n".join(TEX))
    assert "\\" not in t and "{" not in t and "comment" not in t and "sec:" not in t
    assert "powerful AI systems can go\nrogue." in t


def test_same_words_one_object_and_markup_out(tmp_path):
    setup(tmp_path)

    async def steps(c):
        call = lambda tool, **kw: c.call_tool(tool, {"audit": "t", **kw})
        w = lambda log, **kw: call("write", log=log, kind="agent", **kw)
        out = {}
        for g in ("g1 (for A)", "g2 (for A)", "g3 (for A)"):
            s = data(await call("read", log=g, path="s.tex", start=1, end=2))["source"]
            # quoted across \emph{...} and a line break: checked with the markup out
            out[g, "q"] = data(await w(g, id="q1", act="quote", sources=[s],
                                       body='T0 "powerful AI systems can go rogue."'))
        out["v1"] = data(await w("g1 (for A)", id="v1", act="verdict", object="q1",
                                 value="4 rule-property divergence", rests=["q1"]))
        out["v2"] = data(await w("g2 (for A)", id="v2", act="verdict", object="q1",
                                 value="4", rests=["q1"]))
        out["v3"] = data(await w("g3 (for A)", id="v3", act="verdict", object="q1",
                                 value="ordinary non-compliance", rests=["q1"]))
        out["p"] = data(await w("g1 (for A)", id="c1", act="precize", body="c1",
                                rests=["q1"]))
        await w("g1 (for A)", id="m1", act="mark", body="go rogue", rests=["q1"])
        out["cite"] = data(await w("g1 (for A)", id="c2", act="precize", narrows="m1",
                                   rests=["m1"], sources=["s.tex, lines 1-2"],
                                   body='c2, after Guido: "safeties turned off"'))
        out["plain"] = data(await call("read", log="g1 (for A)", path="s.tex",
                                       start=4, end=5, plain=True))
        out["rep"] = data(await call("report"))
        return out
    out = run(tmp_path / "data", steps)
    for k in [k for k in out if k[1:] == ("q",)]:
        assert "ref" in out[k], (k, out[k])
    R = out["rep"]
    v1, v2, v3 = "g1 (for A):v1", "g2 (for A):v2", "g3 (for A):v3"
    assert R["same_object"] == {'verdict "powerful ai systems can go rogue"': [v1, v2, v3]}
    opened = {frozenset(x[:2]) for x in R["open"]}
    assert opened == {frozenset((v1, v3)), frozenset((v2, v3))}   # "4" is "4 ..."
    assert R["open_between_agents"] and R["loose_objects"] == []
    assert out["p"]["refused"] == "narrows"
    assert out["cite"]["refused"] == "verbatim"   # a precize's quotation is checked too
    assert out["plain"]["text"] == ("Guido calls it a containment failure with the "
                                    "safeties turned\noff.")


def test_third_trial_shows_one_object():
    d = Path(__file__).parent.parent / "data" / "six-four-live"
    if not d.exists():
        pytest.skip("no live data")
    from audit import report
    R = report(store.load(d))
    assert R.same_object['verdict "powerful ai systems can go rogue"'] == [
        "g1 (for A):v1", "g2 (for A):v1"]
    assert R.open == []   # both "4", and A settled them
