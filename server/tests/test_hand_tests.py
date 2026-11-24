"""The hand tests, computed. Where the computed report differs from the hand test, the
test asserts what the server computes and says, in a comment marked DIFFERS, how the hand
test differs. Those are the findings of stage 1."""
import pytest

from audit import Entry as E, Record, Refused, report
from fixtures import review, six_four, six_three


def opens(R):
    return {frozenset((a, b)) for a, b, _ in R.open}


# --- §6.4 -------------------------------------------------------------------------
def test_six_four_a11_refused():
    r = Record()
    with pytest.raises(Refused) as x:
        r.add("A", E("a11", "look", "the containment measures were in place"))
    assert x.value.rule == "source"


def test_six_four_strict_replay_stops_at_a11():
    # DIFFERS: the hand test reports both that a11 is refused at write time and that
    # a15 fell because a11 was withdrawn. In one record only one can be true. Under the
    # rules, a11 is never written, so a12 and a15 cannot cite it, and the eight-entry
    # cascade is the book's history, not what the server would have recorded.
    with pytest.raises(Refused) as x:
        six_four(checks=True)
    assert x.value.rule == "source"


def test_six_four_cascade():
    R = report(six_four())
    assert R.withdrawn == {"A:a1", "A:a11"}
    assert set(R.fell) == {f"A:a{n}" for n in (3, 5, 6, 9, 10, 15, 16, 18)}
    assert R.fell["A:a15"] == ["A:a11"]
    assert R.fell["A:a16"][-1] in R.withdrawn


def test_six_four_stands():
    R = report(six_four())
    hand = {f"A:a{n}" for n in (2, 4, 7, 8, 13, 14, 17, *range(21, 34))} | {"R1:r1", "R2:s1"}
    # DIFFERS: the hand list leaves out a12, the commit about the withdrawn a11. Nothing
    # it rests on fell (a commit is *about*, not resting on), so it stands. The hand test
    # leaves it in neither list.
    assert R.stands == hand | {"A:a12"}
    assert R.verdicts_stand == {"A:a29", "A:a30", "A:a31"}


def test_six_four_drift_open_pending():
    R = report(six_four())
    assert "A:a26" in R.drift and "R1:r1" in R.drift["A:a26"]
    assert R.open == []
    assert R.pending_commits == {"A:a32"}
    assert R.met_unanswered == set()  # r1 met a12, and a19 answers r1
    # DIFFERS: the hand test names one single-source finding, a33. Computed from the
    # fields, every look with one source is single-source: a13, a17, r1, s1, a33 and the
    # rest. Which of them matter was the author's judgment; the fields cannot say.
    assert "A:a33" in R.single_source and len(R.single_source) > 1


def test_six_four_invented_open():
    R = report(six_four(invented=True))
    assert frozenset(("A:a29", "R1:r3")) in opens(R)


# --- §6.3 -------------------------------------------------------------------------
def test_six_three():
    R = report(six_three())
    assert set(R.fell) == {"A:a12", "A:a14"}
    assert R.grant_withdrawals == {"D:d2": "on evidence"}
    assert opens(R) == {frozenset(("A:a9", "O:o2"))}
    assert R.on_open["A:a13"] == ["A:a9"]
    assert R.met_unanswered == {"A:a11"}
    assert R.verdicts_stand == {"A:a13"}


def test_six_three_retreat():
    R = report(six_three(retreat=True))
    assert R.grant_withdrawals == {"D:d2": "under the check"}
    assert set(R.fell) == {"A:a12", "A:a14"}  # the cascade is the same either way


def test_check_without_grant_refused():
    r = Record()
    r.add("A", E("a1", "look", "x", sources=["s"]))
    with pytest.raises(Refused) as x:
        r.add("A", E("a2", "check", "scope", rests=["a1"]))
    assert x.value.rule == "grant-first"


def test_grant_by_agent_refused():
    r = Record()
    r.add("A", E("a1", "look", "x", sources=["s"]))
    r.add("A", E("a2", "recover", "M", rests=["a1"]))
    with pytest.raises(Refused) as x:
        r.add("g1", E("g1.1", "grant", "M", kind="agent", rests=["A:a2"]))
    assert x.value.rule == "person"


def test_withdraw_others_refused():
    r = six_three()
    with pytest.raises(Refused) as x:
        r.add("A", E("a99", "withdraw", withdraws="D:d1"))
    assert x.value.rule == "own-only"


# --- the review -------------------------------------------------------------------
def test_review_split():
    R = report(review())
    assert R.withdrawn == {"A:e1"}
    assert set(R.fell) == {"A:e2"}
    assert {"V:v1", "A:a2"} <= R.verdicts_stand
    # with the old, unsplit cite, v1 would fall with the verdict it denies
    U = report(review(unsplit=True))
    assert "V:v1" in U.fell


def test_review_open_and_drift():
    R = report(review())
    assert "A:a3" in R.drift and "V:v2" in R.drift["A:a3"]
    # DIFFERS, or at least unclear: the hand test says e3 is open "until A answers", and
    # that A answered by narrowing. In the rules a narrowing is not a settle and not a
    # withdrawal, so e3 against v2 stays open.
    assert opens(R) == {frozenset(("A:e3", "V:v2")), frozenset(("A:e5", "V:v3"))}
    assert "A:e5" in R.single_source


def test_review_e4_refused():
    r = review()
    with pytest.raises(Refused):
        r.add("A", E("e4", "look", "103–119 circulates widely"))


# --- storage ----------------------------------------------------------------------
def test_save_load_roundtrip(tmp_path):
    r = six_three()
    r.save(tmp_path)
    back = Record.load(tmp_path)
    assert set(back.by_ref) == set(r.by_ref)
    assert report(back).fell == report(r).fell


def test_load_detects_tampering(tmp_path):
    six_three().save(tmp_path)
    p = tmp_path / "D.jsonl"
    p.write_text(p.read_text().replace('"body": "M"', '"body": "not M"', 1))
    with pytest.raises(Refused) as x:
        Record.load(tmp_path)
    assert x.value.rule == "hash"
