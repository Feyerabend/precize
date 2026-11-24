"""The fix round after the fifth trial (findings 39, 42, 45)."""
from pathlib import Path

import pytest

from audit import report, store
from audit.reports import same_value

DATA = Path(__file__).parent.parent / "data"


def test_none_is_one_value():
    assert same_value("none", "None of the five fits; checkability varies")
    assert same_value("no case: frame printed, finding absent", "none, frame 4")
    assert not same_value("none", "3 equivocation")
    assert same_value("4", "4 rule-property divergence")   # unchanged


def load(audit):
    d = DATA / audit
    if not d.exists():
        pytest.skip("no live data")
    return report(store.load(d))


def test_norm_runs_agree_that_no_verdict_is_reached():
    R = load("ai-transparency")
    assert R.open == [] and R.open_between_agents == []
    assert len(R.same_object) == 2       # still listed as one object, by two authors


def test_wood_porter_stays_open():
    R = load("wood-porter")
    assert [x[:2] for x in R.open] == [("g1 (for A):vd1", "g2 (for A):vd1")]  # 3 vs none


def test_a_first_reading_after_the_looks_is_not_drift():
    assert load("ai-transparency").drift == {}
    assert load("wood-porter").drift == {}


def test_an_ask_to_a_person_is_open():
    assert load("ai-transparency").open_asks == {"g2 (for A):a1"}


# the sixth trial (findings 47, 48)

def test_frames_inside_none_are_compared():
    assert not same_value("none, frame 3", "none, frame 4")
    assert same_value("none, frame 4", "no case: frame 4 printed")
    assert same_value("none", "none, frame 4")      # one frame given: nothing to compare
    # 1a and 1b are two frames, not frame 1 twice (finding 91)
    assert not same_value("none, frame 1a", "none, frame 1b")
    assert same_value("none, frame 1a", "none, frame 1a")


def test_tenant_frames_open():
    R = load("tenant-sanitized")
    assert [x[:2] for x in R.open] == [("g1 (for A):vd1", "g2 (for A):vd1")]
    assert R.marks_differ == {}                      # both marked "sanitized"


def test_expense_marks_differ():
    R = load("expense-entertainment")
    assert list(R.marks_differ.values()) == [["g1 (for A):m1", "g2 (for A):m1"]]
    assert R.open == []                              # both "none, frame 4"


def test_adherence_one_mark():
    assert load("adherence-improvement").marks_differ == {}


# the seventh trial: a report in Swedish

def test_swedish_labels():
    from audit.render import Doc
    d = DATA / "expense-entertainment"
    if not d.exists():
        pytest.skip("no live data")
    sv, en = Doc(d, "sv").build(), Doc(d, "en").build()
    assert "Till en person" in sv and "For a person" not in sv
    assert "polyglossia" in sv and "polyglossia" not in en
    assert "For a person" in en


# after the hand-over: two fictional persons (findings 54, 55)

def _rec():
    from audit.record import Answer, Entry, Record
    r = Record()
    r.add("g", Entry("q1", "quote", '"X is Y."', kind="agent", sources=["s, line 1"]))
    r.add("g", Entry("m1", "mark", '"Y"', kind="agent", rests=["q1"], object="q1"))
    r.add("g", Entry("p1", "precize", "P1", kind="agent", rests=["m1"]))
    r.add("g", Entry("a1", "ask", "which way?", kind="agent", rests=["q1"]))
    return r, Answer, Entry


def test_two_holders_of_one_reading_do_not_oppose():
    r, _, E = _rec()
    r.add("A", E("h1", "holder", "", value="the bill", object="g:p1", rests=["g:p1"]))
    r.add("B", E("h1", "holder", "", value="B", object="g:p1", rests=["g:p1"]))
    R = report(r)
    assert R.open == []
    assert R.same_object == {"holder g:p1": ["A:h1", "B:h1"]}


def test_differing_answers_to_one_ask_are_open():
    r, Ans, E = _rec()
    r.add("A", E("o1", "precize", "", value="(b)", answers=[Ans("g:a1")]))
    r.add("B", E("o1", "precize", "", value="(a)", answers=[Ans("g:a1")]))
    R = report(r)
    assert [x[:2] for x in R.open] == [("A:o1", "B:o1")]
    assert R.open_asks == set() and R.answers_to_compare == {}


def test_same_answers_are_not_open():
    r, Ans, E = _rec()
    r.add("A", E("o1", "precize", "", value="(b)", answers=[Ans("g:a1")]))
    r.add("B", E("o1", "precize", "", value="(B) ", answers=[Ans("g:a1")]))
    assert report(r).open == []


def test_an_answer_to_an_ask_needs_a_value():
    from audit.record import Refused
    r, Ans, E = _rec()
    with pytest.raises(Refused, match="value"):
        r.add("A", E("o1", "precize", "(b)", answers=[Ans("g:a1")]))


def test_skollagen_persons():
    R = load("skollagen-vetenskaplig-grund")
    pairs = {frozenset(x[:2]) for x in R.open}
    assert frozenset(("A (fiktiv skoljurist):vd1", "B (fiktiv evidensförespråkare):vd1")) in pairs
    assert not any("h" in a.split(":")[1] for p in pairs for a in p)   # no holder pair
    assert R.answers_to_compare == {
        q: ["A (fiktiv skoljurist):o1", "B (fiktiv evidensförespråkare):o1"]
        for q in ("g1 (for A):a1", "g2 (for A):a1")}


def test_a_reading_found_in_a_look_is_not_drift():
    """Finding 63: g1:p4 narrows the look l2 that found it; l3 only follows in the chain."""
    assert load("yates-tangible-object").drift == {}
