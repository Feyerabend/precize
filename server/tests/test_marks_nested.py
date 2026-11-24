"""One term marked at two lengths (findings 74 and 92): a mark whose words hold another
author's mark of the same quote, at word bounds, is reported as nested, not as a
different term. Both marks stay in the report."""
from audit import Entry as E, Record, report
from audit.reports import contains

S = '"Riksdagen består av en kammare med 349 ledamöter."'


def run(r, log, words):
    r.add(log, E("q1", "quote", S, kind="agent", sources=["RF 3 kap. 1 §"]))
    for i, w in enumerate(words, 1):
        r.add(log, E(f"m{i}", "mark", f'"{w}"', kind="agent", value=w, rests=["q1"]))


def rec(a, b):
    r = Record()
    run(r, "g1 (for A)", a)
    run(r, "g2 (for A)", b)
    return r


def test_contains_whole_words_only():
    assert contains("349 ledamöter", "ledamöter")
    assert not contains("ledamöterna", "ledamöter")
    assert not contains("ledamöter", "349 ledamöter")


def test_nested_is_not_different():
    R = report(rec(("ledamöter", "består av"), ("349 ledamöter", "består av")))
    assert R.marks_differ == {}
    [pairs] = R.marks_nested.values()
    assert pairs == [("g2 (for A):m1", "g1 (for A):m1")]


def test_different_terms_still_differ():
    R = report(rec(("ledamöter",), ("en kammare",)))
    assert list(R.marks_differ.values()) == [["g1 (for A):m1", "g2 (for A):m1"]]
    assert R.marks_nested == {}


def test_nested_and_a_missing_term_still_differ():
    R = report(rec(("ledamöter", "består av"), ("349 ledamöter",)))
    assert len(R.marks_differ) == 1
    assert len(R.marks_nested) == 1


def test_one_authors_own_marks_do_not_nest():
    R = report(rec(("349 ledamöter", "ledamöter"), ("349 ledamöter", "ledamöter")))
    assert R.marks_differ == {} and R.marks_nested == {}


def test_live_audits():
    from pathlib import Path
    import pytest
    from audit import store
    d = Path(__file__).parent.parent / "data"
    for name in ("rf-riksdagen", "skollagen-om-prop"):
        if not (d / name).exists():
            pytest.skip("no live data")
        R = report(store.load(d / name))
        assert R.marks_differ == {} and len(R.marks_nested) == 1
