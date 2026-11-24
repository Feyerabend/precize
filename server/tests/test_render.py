"""The audit as a document: LaTeX from the record, PDF if an engine is found."""
from pathlib import Path

import pytest

from audit import render
from audit.render import Doc, esc

pytest.importorskip("mcp")
import server  # noqa: E402
from test_server import data, run  # noqa: E402
from test_stage4 import agents  # noqa: E402

LIVE = Path(__file__).parent.parent / "data" / "six-four-live"


def test_escape():
    assert esc(r'50% of $x_1 & {y} #2 ~ \z') == (
        r"50\% of \$x\_1 \& \{y\} \#2 \textasciitilde{} \textbackslash{}z")
    assert esc('T0 "go rogue" and "x') == "T0 “go rogue” and ”x"


def test_the_fourth_hand_test_as_a_document(tmp_path):
    _, _, t = agents(tmp_path)
    d = Doc(t)
    tex = d.build()
    # every entry is in the appendix, with an anchor its mentions link to
    for e in d.rec.entries():
        assert r"\hypertarget{" + render.anchor(e) + "}" in tex
    box = tex.split(r"\begin{handover}")[1].split(r"\end{handover}")[0]
    assert "Commits no look meets yet" in box and render.tt("A:a5") in box
    assert "Proposed verdicts no person" not in box   # A answered both, and settled
    v = tex.split(r"\section{Verdicts}")[1].split(r"\section{")[0]
    assert v.index("The audit's verdicts") < v.index("Settled") < v.index("Proposed by agents")
    assert r"\warn{pending}" in tex
    assert "refused" not in tex   # a refused entry is not on the record


def test_the_server_renders_outside_the_record(tmp_path):
    _, _, t = agents(tmp_path)
    server.OUT = tmp_path / "out"
    before = sorted(p.name for p in t.iterdir())

    async def steps(c):
        return data(await c.call_tool("render", {"audit": "six-four"}))
    out = run(tmp_path / "data", steps)
    assert Path(out["tex"]).parent == tmp_path / "out"
    assert sorted(p.name for p in t.iterdir()) == before


@pytest.mark.skipif(render.engine() is None, reason="no TeX engine")
def test_compiles_to_pdf(tmp_path):
    if not LIVE.exists():
        pytest.skip("no live data")
    r = render.render(LIVE, tmp_path)
    assert r["pdf"], r.get("error")
    assert Path(r["pdf"]).read_bytes()[:5] == b"%PDF-"
