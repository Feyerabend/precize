"""Nescio and decide (Naess, "Articulation of Normative Interrelations", 1999/2005).

Ask someone whether they meant T1 or T2, and sooner or later they answer "I don't know".
Past that point "one must decide what to mean". A holder entry with value "nescio" records
the first; a person-only `decide` records the second, so that a report can tell a reading
chosen from a reading found."""
import pytest

from audit import Entry as E, Record, Refused, report
from audit.render import Doc

S = '"Rektorn får även bjuda in partier, om urvalet sker på en annan objektiv grund."'
G = "g1 (for A)"


def readings():
    r = Record()
    r.add(G, E("q1", "quote", S, kind="agent", sources=["sk 186"]))
    r.add(G, E("m1", "mark", '"objektiv grund"', kind="agent", value="objektiv grund", rests=["q1"]))
    for p in ("P1", "P2", "P3"):
        r.add(G, E(p, "precize", f"reading {p}", kind="agent", narrows="m1", rests=["m1"]))
    return r


def nescio(r, log="D", on=(f"{G}:P1", f"{G}:P2")):
    return r.add(log, E("n1", "holder", "D cannot say whether P1 or P2 was meant",
                        value="nescio", object="D", rests=list(on)))


def test_a_nescio_names_two_readings_or_a_mark():
    r = readings()
    with pytest.raises(Refused, match="nescio"):
        r.add("D", E("n0", "holder", "x", value="nescio", object="D", rests=[f"{G}:P1"]))
    r.add("D", E("n1", "holder", "x", value="nescio", object="D", rests=[f"{G}:m1"]))
    assert report(r).nescio == {"D:n1": [f"{G}:P1", f"{G}:P2", f"{G}:P3"]}


def test_a_nescio_is_about_the_holder_not_a_reading():
    r = readings()
    with pytest.raises(Refused, match="nescio"):
        r.add("D", E("n1", "holder", "x", value="Nescio", object=f"{G}:m1",
                     rests=[f"{G}:P1", f"{G}:P2"]))


def test_only_a_person_decides():
    r = readings()
    nescio(r)
    with pytest.raises(Refused, match="person"):
        r.add("g2 (for A)", E("d1", "decide", "x", kind="agent", value=f"{G}:P1", object="D",
                              rests=[f"{G}:P1"], answers=[_a("D:n1")]))


def _a(ref):
    from audit import Answer
    return Answer(ref)


def test_decide_chooses_one_of_the_readings_in_doubt():
    r = readings()
    nescio(r)
    for bad in (dict(value=f"{G}:P3", rests=[f"{G}:P3"]),       # not in doubt
                dict(value=f"{G}:P1", rests=[]),                 # does not rest on it
                dict(value=f"{G}:P1", rests=[f"{G}:P1"], object="E")):  # another holder
        kw = dict(object="D", answers=[_a("D:n1")]) | bad
        with pytest.raises(Refused, match="decide"):
            r.add("D", E("dx", "decide", "x", **kw))
    with pytest.raises(Refused, match="decide"):
        r.add("D", E("dy", "decide", "x", value=f"{G}:P1", object="D", rests=[f"{G}:P1"]))
    r.add("D", E("d1", "decide", "I take P1, since the school must give reasons",
                 value=f"{G}:P1", object="D", rests=[f"{G}:P1"], answers=[_a("D:n1")]))
    R = report(r)
    assert R.decided == {"D:d1": f"{G}:P1"}
    assert R.nescio == {}  # decided
    assert not R.open


def test_two_persons_deciding_differently_are_open():
    r = readings()
    nescio(r)
    r.add("D", E("d1", "decide", "x", value=f"{G}:P1", object="D", rests=[f"{G}:P1"],
                 answers=[_a("D:n1")]))
    r.add("E", E("d1", "decide", "x", value=f"{G}:P2", object="D", rests=[f"{G}:P2"],
                 answers=[_a("D:n1")]))
    assert [(a, b) for a, b, _ in report(r).open] == [("D:d1", "E:d1")]


def test_a_nescio_opposes_another_authors_reading_for_the_holder():
    r = readings()
    nescio(r)
    r.add("A", E("h1", "holder", "D reads P1", value=f"{G}:P1", object="D",
                 rests=[f"{G}:P1"]))
    assert len(report(r).open) == 1


def test_the_rendered_report_shows_both(tmp_path):
    r = readings()
    nescio(r)
    r.add("E", E("n1", "holder", "E cannot say either", value="nescio", object="E",
                 rests=[f"{G}:m1"]))
    r.add("D", E("d1", "decide", "I take P1", value=f"{G}:P1", object="D",
                 rests=[f"{G}:P1"], answers=[_a("D:n1")]))
    r.save(tmp_path)
    doc = Doc(tmp_path)
    tex = doc.build()
    assert "Decided, not found" in tex
    assert "decided" in doc.tags["D:d1"]
    assert "chosen" in doc.tags[f"{G}:P1"]
    assert "loose object" not in doc.tags["D:d1"] + doc.tags["D:n1"]
    assert "nescio" in doc.tags["E:n1"] and "nescio" not in doc.tags["D:n1"]
    assert any("nescio" in k for k, _ in doc.handover())


def test_a_nescio_opposes_only_within_its_mark():
    r = readings()
    r.add(G, E("m2", "mark", '"annan"', kind="agent", value="annan", rests=["q1"]))
    for p in ("Q1", "Q2"):
        r.add(G, E(p, "precize", f"reading {p}", kind="agent", narrows="m2", rests=["m2"]))
    r.add("D", E("n1", "holder", "x", value="nescio", object="D", rests=[f"{G}:Q1", f"{G}:Q2"]))
    r.add("A", E("h1", "holder", "D goes by P1", value=f"{G}:P1", object="D", rests=[f"{G}:P1"]))
    assert report(r).open == []  # D's doubt is about "annan", A's claim about "objektiv grund"
    r.add("A", E("h2", "holder", "D goes by Q1", value=f"{G}:Q1", object="D", rests=[f"{G}:Q1"]))
    assert [(a, b) for a, b, _ in report(r).open] == [("D:n1", "A:h2")]
    assert report(r).loose_objects == set()  # "D goes by P1" names the holder, by rule
