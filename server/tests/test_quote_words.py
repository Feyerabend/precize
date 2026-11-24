"""A quote that also quotes a note names the sentence it quotes (finding 65): in trial 9,
g2 put the amendment note in quotation marks before T0, and the two runs' verdicts on
one sentence were not compared."""
import pytest

from audit import Entry as E, Record, report
from audit.reports import quote_words

S = "Utbildningen ska vila på vetenskaplig grund och beprövad erfarenhet."


def test_the_longest_passage_is_the_quote():
    body = f'T0, ordagrant och utan ändringsnoteringen "Lag (2026:1096).": "{S}"'
    assert quote_words(body) == S.lower().rstrip(".")


def test_two_frames_on_one_sentence_are_compared():
    r = Record()
    r.add("g1 (for A)", E("q1", "quote", f'T0: "{S}" Noten "Lag (2026:1096)." ingår inte.', sources=["sk 183"],
                          kind="agent"))
    r.add("g2 (for A)", E("q1", "quote", f'Utan noten "Lag (2026:1096).": "{S}"', sources=["sk 183"],
                          kind="agent"))
    for log, v in (("g1 (for A)", "none, frame 1b"), ("g2 (for A)", "none, frame 3")):
        r.add(log, E("vd1", "verdict", v, kind="agent", object=f"{log}:q1", value=v,
                     rests=["q1"]))
    R = report(r)
    assert any(len(v) == 2 for k, v in R.same_object.items() if k.startswith("verdict"))
    pairs = {frozenset(x[:2]) for x in R.open}
    assert frozenset(("g1 (for A):vd1", "g2 (for A):vd1")) in pairs


def test_live_trial_9_split_shows():
    from pathlib import Path
    from audit import store
    d = Path(__file__).parent.parent / "data" / "skollagen-och"
    if not d.exists():
        pytest.skip("no live data")
    R = report(store.load(d))
    pairs = {frozenset(x[:2]) for x in R.open}
    assert frozenset(("g1 (for A):vd1", "g2 (for A):vd1")) in pairs
