"""Two disagreements on one sentence (finding 98). In De Sylva the widow and the son part
on "or", and the Court and the concurrence part on "children". A verdict names the
readings it is between, and verdicts are compared only when those readings belong to the
same marked words."""
import pytest

from audit import Entry as E, Record, Refused, report

S = '"the widow, widower, or children of the author"'


def run(r, log, or_value="2", children_value="1b", children=True):
    add = r.add
    add(log, E("q1", "quote", S, kind="agent", sources=["17 U.S.C. § 24"]))
    add(log, E("m1", "mark", '"or"', kind="agent", value="or", rests=["q1"]))
    add(log, E("m2", "mark", '"children"', kind="agent", value="children", rests=["q1"]))
    for pid, m, body in (("p1", "m1", "or = one class: widow and children share"),
                         ("p2", "m1", "or = an order: the widow first, the children after"),
                         ("p5", "m2", "children = heirs under state law"),
                         ("p6", "m2", "children = any child, whatever state law says")):
        add(log, E(pid, "precize", body, kind="agent", rests=[m], narrows=m))
    add(log, E("vd1", "verdict", "widow against son", kind="agent", object="q1",
               value=or_value, between=["p1", "p2"], rests=["p1", "p2"]))
    if children:
        add(log, E("vd2", "verdict", "the Court against the concurrence", kind="agent",
                   object="q1", value=children_value, between=["p5", "p6"],
                   rests=["p5", "p6"]))


def test_two_verdicts_of_one_run_on_two_pairs():
    r = Record()
    run(r, "g1")
    assert report(r).open == []


def test_verdicts_on_different_marks_do_not_oppose():
    r = Record()
    run(r, "g1")
    run(r, "g2", children=False)
    assert report(r).open == []


def test_verdicts_on_the_same_marks_still_oppose():
    r = Record()
    run(r, "g1")
    run(r, "g2", children_value="2")
    assert [x[:2] for x in report(r).open] == [("g1:vd2", "g2:vd2")]


def test_a_verdict_without_between_is_compared_as_before():
    r = Record()
    run(r, "g1", children=False)
    r.add("g2", E("q1", "quote", S, kind="agent", sources=["17 U.S.C. § 24"]))
    r.add("g2", E("vd1", "verdict", "", kind="agent", object="q1", value="1b",
                  rests=["q1"]))
    assert [x[:2] for x in report(r).open] == [("g1:vd1", "g2:vd1")]


def test_one_value_per_set_of_marks():
    r = Record()
    run(r, "g1", children=False)
    with pytest.raises(Refused) as x:
        r.add("g1", E("vd3", "verdict", "", kind="agent", object="q1", value="3",
                      between=["p2", "p1"], rests=["p1"]))
    assert x.value.rule == "between"
    r.add("g1", E("w1", "withdraw", "", kind="agent", withdraws="vd1"))
    r.add("g1", E("vd3", "verdict", "", kind="agent", object="q1", value="3",
                  between=["p2", "p1"], rests=["p1"]))


def test_between_names_precizes_of_a_verdict():
    r = Record()
    run(r, "g1", children=False)
    for bad in (dict(act="look", between=["p1", "p2"]),
                dict(act="verdict", between=["p1"]),
                dict(act="verdict", between=["p1", "m2"])):
        with pytest.raises(Refused) as x:
            r.add("g1", E("z", bad["act"], "", kind="agent", object="q1", value="2",
                          between=bad["between"], sources=["x"], rests=["q1"]))
        assert x.value.rule == "between"


def test_old_hashes_kept():
    from audit.record import _digest
    e = E("q1", "quote", S, kind="agent")
    d = e.to_json()
    d.pop("between")
    assert _digest(e) == _digest(E.from_json(d))
