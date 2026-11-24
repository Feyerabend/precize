"""Findings 11-14 of the live trial (§6.1, "Bitcoin is money."), replayed in small."""
from pathlib import Path

from audit import Entry as E, Record, report
from audit.reports import document

G = "g1 (for A)"
M = "manual/body/06-four-audits.tex"


def trial(via=None):
    r = Record()
    r.add(G, E("q1", "quote", 'T0 "Bitcoin is money."', kind="agent", sources=[f"{M} §6.1, line 35"]))
    r.add(G, E("m1", "mark", "money", kind="agent", rests=["q1"]))
    # finding 11: the first readings narrow the mark
    r.add(G, E("p2", "precize", "legal tender", kind="agent", rests=["m1"], narrows="m1"))
    r.add(G, E("n1", "recover", "N", kind="agent", rests=["p2"]))
    r.add(G, E("c1", "commit", "what would change my mind", kind="agent", about="n1"))
    r.add(G, E("l1", "look", "the decree as reformed", kind="agent", rests=["c1"],
               sources=[f"{M} §6.1, lines 81-88", f"{M} §6.1, lines 90-100"], via=via))
    r.add(G, E("vd1", "verdict", "proposed", kind="agent", object="T0", value="hollowed",
               rests=["l1", "p2"]))
    r.add(G, E("x1", "close", "handed over", kind="agent"))
    return r


def test_precize_narrows_its_mark():
    assert trial().get(f"{G}:p2").narrows == f"{G}:m1"


def test_two_passages_of_one_document_are_one_source():
    assert document(f"{M} §6.1, lines 81-88") == M
    assert document("IRS Notice 2014-21, p. 2") == "IRS Notice 2014-21"
    R = report(trial())
    assert f"{G}:l1" in R.single_source


def test_second_hand():
    R = report(trial(via=M))
    assert R.second_hand == {f"{G}:l1": M}
    assert report(trial()).second_hand == {}


def test_awaiting_grant_and_what_rests_on_it():
    r = trial()
    R = report(r)
    assert R.awaiting_grant == {f"{G}:n1": []}  # vd1 rests on p2 and l1, not on n1
    assert f"{G}:x1" not in R.stands            # close claims nothing
    r2 = Record()
    r2.add("A", E("q", "quote", "x", sources=["s, p. 1"]))
    r2.add("A", E("n", "recover", "N", rests=["q"]))
    r2.add("A", E("v", "verdict", "v", object="T", value="t", rests=["n"]))
    assert report(r2).awaiting_grant == {"A:n": ["A:v"]}
    r2.add("D", E("g", "grant", "N", rests=["A:n"]))
    assert report(r2).awaiting_grant == {}


def test_old_logs_still_load(tmp_path):
    # entries written before `via` existed keep their hashes
    data = Path(__file__).parent.parent / "data" / "six-one-live"
    if data.exists():
        assert len(Record.load(data).logs[G]) == 11


def test_stop_rules_in_server_instructions():
    import pytest
    pytest.importorskip("mcp")
    import server
    assert "hand over to a person" in server.mcp.instructions


def test_one_log_one_kind():
    import pytest
    from audit import Refused
    r = Record()
    r.add("A", E("q", "quote", "x", sources=["s, p. 1"]))
    with pytest.raises(Refused) as x:
        r.add("A", E("v", "verdict", "v", kind="agent", object="T", value="t", rests=["q"]))
    assert x.value.rule == "kind"


def test_object_as_ref_shows_the_dispute():
    r = trial()
    r.add("g2 (for A)", E("vd1", "verdict", "false", kind="agent",
                          object=f"{G}:q1|P2", value="false", rests=[f"{G}:l1"]))
    r.add("g3 (for A)", E("vd1", "verdict", "hollowed", kind="agent",
                          object=f"{G}:q1 | P2", value="hollowed", rests=[f"{G}:l1"]))
    R = report(r)
    assert ("g2 (for A):vd1", "g3 (for A):vd1", f"{G}:q1|P2: false / hollowed") in R.open
    assert R.loose_objects == {f"{G}:vd1"}  # the first run's object "T0" names no entry


def test_vary_takes_the_cards_outcomes_and_stops():
    import pytest
    from audit import Refused
    r = trial()
    with pytest.raises(Refused) as x:
        r.add("V", E("v", "vary", "moves", object=f"{G}:q1", value="moves", rests=[f"{G}:m1"]))
    assert x.value.rule == "vary"
    r.add("V", E("v", "vary", "false on all", object=f"{G}:q1", value="false under all",
                 rests=[f"{G}:m1"]))
    assert report(r).stops == {"V:v": "false on every reading: stop, report it in that form"}


def test_constitutive_reading():
    r = trial()
    r.add("V", E("k", "property", "no property: legal tender is what the statute says",
                 value="none (constitutive)", rests=[f"{G}:p2"]))
    r.add("V", E("n", "verdict", "no divergence on P2", object=f"{G}:q1|P2", value="none",
                 rests=["k"]))
    assert report(r).constitutive == {"V:k": ["V:n"]}
