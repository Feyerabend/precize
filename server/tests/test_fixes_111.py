"""Finding 111: a mark's value that quotes its word with its context marks the word."""
from pathlib import Path

import pytest

from audit import report, store
from audit.record import Entry, Record
from audit.reports import marked_words

DATA = Path(__file__).parent.parent / "data"
Q = '"the widow, widower, or children of the author shall be entitled"'


def test_value_with_context_marks_the_first_quoted_word():
    e = Entry("m1", "mark", "", value='"or" in "the widow, widower, or children"')
    assert marked_words(e) == "or"
    assert marked_words(Entry("m1", "mark", "", value='"sanitized"')) == "sanitized"
    assert marked_words(Entry("m1", "mark", "", value="objektiv grund")) == "objektiv grund"


def _two_runs(value_a, value_b):
    r = Record()
    for g in ("g1", "g2"):
        r.add(g, Entry("q1", "quote", Q, kind="agent", sources=["s, line 1"]))
    r.add("g1", Entry("m1", "mark", 'The "or" in "the widow, widower, or children".',
                      kind="agent", rests=["q1"], object="q1"))
    r.add("g2", Entry("m1", "mark", "", value='"or" in "the widow, widower, or children"',
                      kind="agent", rests=["q1"], object="q1"))
    for g in ("g1", "g2"):
        r.add(g, Entry("P1", "precize", "class", kind="agent", rests=["m1"], narrows="m1"))
        r.add(g, Entry("P2", "precize", "order", kind="agent", rests=["m1"], narrows="m1"))
    r.add("g1", Entry("V1", "verdict", "", kind="agent", value=value_a, object="q1",
                      rests=["P1", "P2"], between=["P1", "P2"]))
    r.add("g2", Entry("V1", "verdict", "", kind="agent", value=value_b, object="q1",
                      rests=["P1", "P2"], between=["P1", "P2"]))
    return report(r)


def test_same_word_marked_two_ways_does_not_differ():
    R = _two_runs("2", "2")
    assert R.marks_differ == {} and R.marks_nested == {}
    assert R.open == []


def test_verdicts_on_the_same_word_are_compared():
    R = _two_runs("2", "1")
    assert [x[:2] for x in R.open] == [("g1:V1", "g2:V1")]


def test_desylva_rerun():
    d = DATA / "desylva-or-2"
    if not d.exists():
        pytest.skip("no live data")
    R = report(store.load(d))
    assert R.marks_differ == {} and R.marks_nested == {}
    assert R.open == []
