"""A connective can be marked like a word (finding 64): its readings get holders, vary and
verdicts, which an ask does not. Built on the Education Act sentence."""
import pytest

from audit import Entry as E, Record, Refused, report

S = '"Utbildningen ska vila på vetenskaplig grund och beprövad erfarenhet."'
OCH = [("o1", "och = both: every part rests on research and on proven experience"),
       ("o2", "och = either or both: every part rests on research, on experience, or both"),
       ("o3", "och = the whole on the two together: experience covers what research does not")]


def run(r, log, words=("vetenskaplig grund", "och")):
    add = r.add
    add(log, E("q1", "quote", S, kind="agent", sources=["skollagen 1 kap. 5 §"]))
    for i, w in enumerate(words, 1):
        add(log, E(f"m{i}", "mark", f'"{w}"', kind="agent", value=w, rests=["q1"]))
    if "och" in words:
        m = f"m{words.index('och') + 1}"
        for pid, body in OCH:
            add(log, E(pid, "precize", body, kind="agent", rests=[m], narrows=m))
        add(log, E("v1", "vary", "true under o2, false under o1 for a school using "
                   "proven methods without research support", kind="agent",
                   object=f"{log}:q1", value="varies", rests=["o1", "o2", "o3"]))


def record():
    r = Record()
    run(r, "g1 (for A)")
    run(r, "g2 (for A)")
    return r


def test_connective_marks_agree():
    R = report(record())
    assert R.marks_differ == {}


def test_a_missing_connective_mark_shows():
    r = record()
    run(r, "g3 (for A)", words=("vetenskaplig grund",))
    R = report(r)
    [refs] = R.marks_differ.values()
    assert "g3 (for A):m1" in refs and "g1 (for A):m2" in refs


def test_connective_readings_need_a_person_for_holders():
    r = record()
    with pytest.raises(Refused):
        r.add("g1 (for A)", E("h1", "holder", "A holds o2", kind="agent",
                              object="g1 (for A):o2", value="A"))


def test_persons_differ_on_the_connective_and_it_is_open():
    r = record()
    r.add("A", E("h1", "holder", "the school lawyer reads och as o2",
                 object="A", value="g1 (for A):o2", rests=["g1 (for A):o2"]))
    r.add("B", E("h1", "holder", "the evidence advocate reads och as o1",
                 object="B", value="g1 (for A):o1", rests=["g1 (for A):o1"]))
    r.add("A", E("vd1", "verdict", "1b", object="g1 (for A):q1", value="1b",
                 rests=["A:h1", "g1 (for A):v1"]))
    r.add("B", E("vd1", "verdict", "4", object="g1 (for A):q1", value="4",
                 rests=["B:h1", "g1 (for A):v1"]))
    R = report(r)
    pairs = {frozenset(x[:2]) for x in R.open}
    assert frozenset(("A:vd1", "B:vd1")) in pairs
    # each says which reading they go by, of themselves: two objects, so not opposed
    assert frozenset(("A:h1", "B:h1")) not in pairs
