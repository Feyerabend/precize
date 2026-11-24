"""The hand tests, as records.

Each builder writes the entries of one hand test in the order the test gives. Cites are
marked `rests` or `answers`, as the meetings check requires. The first three tests were
written before that split, so the marking here is new hand work; each choice that was not
obvious has a comment.
"""
from audit import Answer, Entry as E, Record


def A(ref, **kw):
    return Answer(ref, **kw)


def six_four(checks=False, invented=False):
    """First test, §6.4. Replayed with checks=False by default: the history it records
    contains a11, a look with no source, which the rules now refuse (see test_six_four)."""
    r = Record(checks=checks)
    add = r.add
    add("A", E("a1", "quote", '"the agents went rogue"', sources=["circulating accounts"]))
    add("A", E("a2", "quote", 'Guido: "a containment failure…"', sources=["Lawfare"]))
    add("A", E("a3", "mark", "go rogue", rests=["a1"]))
    add("A", E("a4", "mark", "contained", rests=["a2"]))
    add("A", E("a5", "precize", "w1 act against its objective", rests=["a3"]))
    add("A", E("a6", "precize", "w2 act outside operators' expectations", rests=["a3"]))
    add("A", E("a7", "precize", "c1 the specified measures were in place", rests=["a4"]))
    add("A", E("a8", "precize", "c2 unable to act outside sanctioned scope", rests=["a4"]))
    add("A", E("a9", "holder", "Guido holds w2/c1", object="Guido", value="w2/c1",
               rests=["a6", "a7"]))
    add("A", E("a10", "grid", "go rogue x contained", rests=["a3", "a4"]))
    add("A", E("a11", "look", "the containment measures were in place throughout",
               sources=[]))  # source: NONE
    add("A", E("a12", "commit", "a document: one specified measure not in place", about="a11"))
    add("A", E("a13", "look", "proxy was primary permitted network egress",
               sources=["HF disclosure"]))
    add("A", E("a14", "property", "could this system act outside its sanctioned scope?",
               rests=["a8"]))
    add("A", E("a15", "verdict", "4 on contained", object="contained", value="4",
               rests=["a11", "a13", "a14"]))
    add("A", E("a16", "verdict", "5 on go rogue", object="go rogue", value="5",
               rests=["a10", "a9"]))
    add("A", E("a17", "look", "within objective; knowingly outside scope", sources=["METR"]))
    add("A", E("a18", "precize", "w3 within objective, outside scope", rests=["a3", "a17"]))
    # Two readers. r1 meets the commit a12. s1 shows a1 is not Lieu's words: it disputes a1.
    add("R1", E("r1", "look", "Two of our own settings allowed it", sources=["HF timeline"],
                answers=[A("A:a12", meets=True)]))
    add("R2", E("s1", "look", 'Lieu said "powerful AI systems can go rogue"',
                sources=["Lawfare"], answers=[A("A:a1", disputes=True)]))
    # A withdraws, having read both. A withdrawal answers its reason; it rests on nothing.
    add("A", E("a19", "withdraw", withdraws="a11", answers=[A("R1:r1")]))
    add("A", E("a20", "withdraw", withdraws="a1", answers=[A("R2:s1")]))
    add("A", E("a21", "quote", 'Lieu: "powerful AI systems can go rogue"',
               sources=["Lawfare"], rests=["R2:s1"]))
    add("A", E("a22", "mark", "go rogue", rests=["a21"]))
    add("A", E("a23", "precize", "w1 (re-entered)", rests=["a22"]))
    add("A", E("a24", "precize", "w2 (re-entered)", rests=["a22"]))
    add("A", E("a25", "precize", "w3 (re-entered)", rests=["a22", "a17"]))
    add("A", E("a26", "precize", "c1' c1 at the evaluation-sandbox boundary",
               rests=["a7"], narrows="a7"))
    add("A", E("a27", "holder", "Lieu holds w1/c2; Guido holds w2/c1", object="Lieu",
               value="w1/c2", rests=["a23", "a24", "a26", "a8"]))
    add("A", E("a28", "grid", "re-entered", rests=["a22", "a4"]))
    add("A", E("a29", "verdict", "4 on contained, evaluation boundary",
               object="contained@evaluation", value="4", rests=["a26", "a13", "a14"]))
    add("A", E("a30", "verdict", "ordinary non-compliance, second boundary",
               object="contained@second", value="ordinary", rests=["R1:r1"]))
    add("A", E("a31", "verdict", "5 on go rogue", object="go rogue", value="5",
               rests=["a28", "a27"]))
    add("A", E("a32", "commit", "(i) a measure absent; (ii) proxy not sanctioned", about="a29"))
    add("A", E("a33", "look", "board rebuilt 8 July via unauthenticated WebDAV",
               sources=["Black Hat, 5 Aug"], answers=[A("a32", meets=False)]))
    if invented:  # the invented scenario: R1 disagrees with a29 without having seen it
        add("R1", E("r2", "look", "the WebDAV passage", sources=["Black Hat talk"]))
        add("R1", E("r3", "verdict", "ordinary non-compliance, evaluation boundary",
                    object="contained@evaluation", value="ordinary", rests=["r2", "r1"]))
    return r


def six_three(checks=True, retreat=False):
    """Second test as corrected by the third: o2 fills an absence in the world, so a13 is
    open against it and not struck. With retreat=True, D withdraws having seen a12."""
    r = Record(checks=checks)
    add = r.add
    add("A", E("a1", "quote", '"The Act censors lawful speech."', sources=["§2.1"]))
    add("A", E("a2", "mark", "censors", rests=["a1"]))
    add("A", E("a3", "precize", "P1 the Act itself requires removal of lawful material",
               rests=["a2"]))
    add("A", E("a4", "precize", "P2 a system whose operation removes lawful material",
               rests=["a2"]))
    add("A", E("a5", "holder", "D reads P2", object="D", value="P2", rests=["a4"]))
    add("A", E("a6", "property", "does this system take down what is unlawful…",
               rests=["a3", "a4"]))
    add("A", E("a7", "look", ">9 bn decisions, ~99 % under terms of service",
               sources=["DG CONNECT, H1 2025"]))
    add("A", E("a8", "look", "Adult Nudity standard prohibits lawful material",
               sources=["Meta, clause"]))
    add("A", E("a9", "look", "no provision found requiring removal of lawful material",
               sources=["DSA, Arts. searched"],
               absent={"in": "world", "what": "a provision requiring removal of lawful material",
                       "where": "the Act"}))
    add("A", E("a10", "recover", "M: the Act entrenched removal under terms of service",
               rests=["a4", "a7"]))
    add("A", E("a11", "commit", "(iii) removal runs at about the pre-Act rate", about="a10"))
    add("D", E("d1", "grant", "M", rests=["A:a10"]))
    add("A", E("a12", "check", "F established of the Act only through M; M granted",
               rests=["D:d1", "a7", "a4"]))
    add("A", E("a13", "verdict", "val(T0|P1) = false", object="T0|P1", value="false",
               rests=["a9", "a3"]))
    add("A", E("a14", "verdict", "val(T0|P2) = true, given M", object="T0|P2", value="true",
               rests=["a12", "a8", "a6"]))
    add("O", E("o1", "look", "removal at about the pre-Act rate", sources=["national study"],
               answers=[A("A:a11", meets=True)]))
    add("O", E("o2", "look", "Art. X requires removal of lawful material",
               sources=["Art. X, passage"], answers=[A("A:a9")]))
    why = [A("O:o1")] + ([A("A:a12")] if retreat else [])
    add("D", E("d2", "withdraw", withdraws="d1", answers=why))
    return r


def review(checks=True, unsplit=False):
    """Third test: the second review. With unsplit=True, v1 *rests* on e1, as a cite did
    before the split; this shows what the split is for."""
    r = Record(checks=checks)
    add = r.add
    add("A", E("e1", "verdict", "4 on §6.3", object="§6.3", value="4"))
    add("A", E("e2", "look", "Appendix C tally of verdict-4 audits", sources=["Appendix C"],
               rests=["e1"]))
    if unsplit:
        add("V", E("v1", "verdict", "not 4", object="§6.3", value="not 4", rests=["A:e1"]))
    else:
        add("V", E("v1", "verdict", "not 4", object="§6.3", value="not 4",
                   answers=[A("A:e1", disputes=True)]))
    add("A", E("a1", "withdraw", withdraws="e1", answers=[A("V:v1")]))
    # a2 takes V's reading over: it rests on v1. So it does not oppose v1.
    add("A", E("a2", "verdict", "none of the five", object="§6.3", value="none",
               rests=["V:v1"]))
    add("A", E("e3", "look", "every widely adopted type system ships an escape hatch",
               sources=["the edition"],
               absent={"in": "world", "what": "a widely adopted type system without one"}))
    add("V", E("v2", "look", "Elm: no any, no user-accessible unsafe", sources=["Elm"],
               answers=[A("A:e3")]))
    # a3 narrows a claim found, not a reading: `narrows` had to be widened to allow a look.
    add("A", E("a3", "precize", "the claim restricted to the six languages named",
               rests=["e3"], narrows="e3", answers=[A("V:v2")]))
    add("A", E("e5", "look", "board down 4 July, rebuilt 8 July", sources=["the talk"]))
    # v3's source is not named in the review. Rule 4 needs a source; the entry is given
    # the only one the review states.
    add("V", E("v3", "look", "8 July belongs to a different event",
               sources=["a secondary source (not named)"], answers=[A("A:e5", disputes=True)]))
    add("A", E("a4", "look", "For now this chronology rests on a single talk",
               sources=["§6.4 as printed"], answers=[A("e5"), A("V:v3")]))
    return r
