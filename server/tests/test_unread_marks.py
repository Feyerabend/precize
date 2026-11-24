"""A mark whose readings are written only in its own body is flagged (finding 69): no
holder, vary or verdict can name such a reading. Trial 10's g1 marked "om" so."""
from pathlib import Path

import pytest

from audit import Entry as E, Record, report, store

S = '"Rektorn får även bjuda in politiska partier, om urvalet sker på en annan objektiv grund."'


def base():
    r = Record()
    r.add("g1 (for A)", E("q1", "quote", S, kind="agent", sources=["sk 186"]))
    r.add("g1 (for A)", E("m1", "mark", '"om": (a) enough; (b) only if; (c) a consequence',
                          kind="agent", value="om", rests=["q1"]))
    return r


def test_readings_in_the_mark_body_are_flagged():
    assert report(base()).unread_marks == {"g1 (for A):m1"}


def test_a_precize_reads_the_mark():
    r = base()
    r.add("g1 (for A)", E("p1", "precize", "om = only if", kind="agent",
                          rests=["m1"], narrows="m1"))
    assert report(r).unread_marks == set()


def test_a_reading_that_narrows_a_look_does_not_read_the_mark():
    r = base()
    r.add("g1 (for A)", E("l1", "look", "1 kap. 5 a § första stycket: \"samtliga\"",
                          kind="agent", sources=["sk 184"], rests=["m1"]))
    r.add("g1 (for A)", E("p1", "precize", "after l1, om = only if", kind="agent",
                          rests=["l1", "m1"], narrows="l1"))
    assert report(r).unread_marks == {"g1 (for A):m1"}


@pytest.mark.skipif(not Path("data/skollagen-om").exists(), reason="trial 10 not here")
def test_live_trial_10():
    R = report(store.load(Path("data/skollagen-om")))
    assert R.unread_marks == {"g1 (for A):m2"}
