"""'Or' marked like a word (findings 64, 68), with the three readings the server lists:
either or both, one but not both, a choice of either. The sentence is made up for the
test; it is not quoted from any source."""
import pytest

from audit import Entry as E, Record, Refused, report

S = '"Den sökande ska ha examen i juridik eller ekonomi."'
ELLER = [("e1", "eller = either or both: a degree in law, in economics, or in both"),
         ("e2", "eller = one but not both: a degree in exactly one of the two"),
         ("e3", "eller = a choice of either: the authority picks which degree it asks for")]


def run(r, log, words=("examen", "eller"), readings=ELLER):
    add = r.add
    add(log, E("q1", "quote", S, kind="agent", sources=["constructed for the test"]))
    for i, w in enumerate(words, 1):
        add(log, E(f"m{i}", "mark", f'"{w}"', kind="agent", value=w, rests=["q1"]))
    if "eller" in words:
        m = f"m{words.index('eller') + 1}"
        for pid, body in readings:
            add(log, E(pid, "precize", body, kind="agent", rests=[m], narrows=m))
        add(log, E("v1", "vary", "an applicant with both degrees qualifies under e1, "
                   "not under e2", kind="agent", object=f"{log}:q1", value="varies",
                   rests=[pid for pid, _ in readings]))


def record():
    r = Record()
    run(r, "g1 (for A)")
    run(r, "g2 (for A)")
    return r


def test_or_marks_agree():
    assert report(record()).marks_differ == {}


def test_a_missing_or_mark_shows():
    r = record()
    run(r, "g3 (for A)", words=("examen",))
    [refs] = report(r).marks_differ.values()
    assert "g3 (for A):m1" in refs and "g1 (for A):m2" in refs


def test_two_readings_only_still_marks_the_same_words():
    # a run that lists only inclusive and exclusive marked the same word: not a mark
    # difference; the missing reading shows in the readings, not in marks_differ
    r = record()
    run(r, "g3 (for A)", readings=ELLER[:2])
    assert report(r).marks_differ == {}


def test_or_readings_need_a_person_for_holders():
    r = record()
    with pytest.raises(Refused):
        r.add("g1 (for A)", E("h1", "holder", "A holds e2", kind="agent",
                              object="g1 (for A):e2", value="A"))


def test_inclusive_against_exclusive_is_open():
    r = record()
    r.add("A", E("h1", "holder", "the applicant reads eller as e1",
                 object="A", value="g1 (for A):e1", rests=["g1 (for A):e1"]))
    r.add("B", E("h1", "holder", "the authority reads eller as e2",
                 object="B", value="g1 (for A):e2", rests=["g1 (for A):e2"]))
    r.add("A", E("vd1", "verdict", "qualifies", object="g1 (for A):q1", value="qualifies",
                 rests=["A:h1", "g1 (for A):v1"]))
    r.add("B", E("vd1", "verdict", "does not qualify", object="g1 (for A):q1",
                 value="does not qualify", rests=["B:h1", "g1 (for A):v1"]))
    pairs = {frozenset(x[:2]) for x in report(r).open}
    assert frozenset(("A:vd1", "B:vd1")) in pairs
    assert frozenset(("A:h1", "B:h1")) not in pairs
