"""A vary may name the mark it varies (finding 75). In trial 10' a run with two marks on
one sentence invented the object `q1|m2` to keep its two varies apart."""
from pathlib import Path

import pytest

from audit import Entry as E, Record, Refused, report, store

S = '"Rektorn får även bjuda in partier, om urvalet sker på en annan objektiv grund."'


def two_runs():
    r = Record()
    for a in ("g1 (for A)", "g2 (for A)"):
        r.add(a, E("q1", "quote", S, kind="agent", sources=["sk 186"]))
        r.add(a, E("m1", "mark", '"objektiv grund"', kind="agent", value="objektiv grund", rests=["q1"]))
        r.add(a, E("m2", "mark", '"om"', kind="agent", value="om", rests=["q1"]))
    return r


def test_a_vary_may_narrow_a_mark_only():
    r = two_runs()
    r.add("g1 (for A)", E("v1", "vary", "x", kind="agent", value="varies", object="q1",
                          rests=["m1"], narrows="m1"))
    with pytest.raises(Refused):
        r.add("g1 (for A)", E("v2", "vary", "x", kind="agent", value="varies", object="q1",
                              rests=["q1"], narrows="q1"))


def test_varies_of_different_marks_are_not_opposed():
    r = two_runs()
    r.add("g1 (for A)", E("v1", "vary", "x", kind="agent", value="varies", object="q1",
                          rests=["m1"], narrows="m1"))
    r.add("g2 (for A)", E("v1", "vary", "x", kind="agent", value="true under all", object="q1",
                          rests=["m2"], narrows="m2"))
    R = report(r)
    assert R.open == []
    assert not any(k.startswith("vary") for k in R.same_object)


def test_varies_of_one_mark_across_runs_are_compared():
    r = two_runs()
    r.add("g1 (for A)", E("v1", "vary", "x", kind="agent", value="varies", object="q1",
                          rests=["m2"], narrows="m2"))
    r.add("g2 (for A)", E("v1", "vary", "x", kind="agent", value="true under all", object="q1",
                          rests=["m2"], narrows="m2"))
    R = report(r)
    assert len(R.open) == 1
    keys = [k for k in R.same_object if k.startswith("vary")]
    assert len(keys) == 1 and keys[0].endswith(' / "om"')


def test_a_vary_naming_no_mark_is_compared_with_all():
    r = two_runs()
    r.add("g1 (for A)", E("v1", "vary", "x", kind="agent", value="varies", object="q1",
                          rests=["m1"]))
    r.add("g2 (for A)", E("v1", "vary", "x", kind="agent", value="true under all", object="q1",
                          rests=["m2"], narrows="m2"))
    assert len(report(r).open) == 1


@pytest.mark.skipif(not Path("data").exists(), reason="no live data")
def test_live_audits_unchanged():
    # a live log whose varies name no mark keeps same_object for varies as before
    for d in Path("data").iterdir():
        if d.is_dir() and any(d.glob("*.jsonl")):
            if any('"narrows"' in f.read_text() for f in d.glob("*.jsonl")):
                continue
            R = report(store.load(d))
            assert all("/ \"" not in k for k in R.same_object)
