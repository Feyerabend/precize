"""Stage 2: the fifth test (four readers of three logs) and the sixth (a log shown two
ways). DIFFERS comments mark where the computed report and the hand test part."""
from audit import Entry as E, Record, report
from fixtures import six_three


def read(tmp_path, logs, rec=None, heads=None, name="r"):
    rec = rec or six_three()
    folder = tmp_path / name
    rec.save(folder, heads=heads, logs=logs)
    return report(Record.load(folder))


def opens(R):
    return {frozenset((a, b)) for a, b, _ in R.open}


def row(R):
    """One column of the fifth test's table."""
    def status(ref):
        if ref in R.fell:
            return "fell"
        if ref in R.rests_unread:
            return "rests on unread"
        if any(ref in (a, b) or ref in R.on_open and set(R.on_open[ref]) & {a, b}
               for a, b, _ in R.open):
            return "open"
        if ref in R.pending_commits:
            return "pending"
        if ref in R.met_unanswered:
            return "met, unanswered"
        return "stands"
    return {k: status(f"A:{k}") for k in ("a12", "a13", "a14", "a11")}


def test_fifth_test_table(tmp_path):
    R1 = read(tmp_path, ["A"], name="r1")
    R2 = read(tmp_path, ["A", "D"], name="r2")
    R3 = read(tmp_path, ["A", "O"], name="r3")
    R4 = read(tmp_path, ["A", "D", "O"], name="r4")
    assert row(R1) == {"a12": "rests on unread", "a13": "stands",
                       "a14": "rests on unread", "a11": "pending"}
    assert row(R2) == {"a12": "fell", "a13": "stands", "a14": "fell", "a11": "pending"}
    assert row(R3) == {"a12": "rests on unread", "a13": "open",
                       "a14": "rests on unread", "a11": "met, unanswered"}
    assert row(R4) == {"a12": "fell", "a13": "open", "a14": "fell", "a11": "met, unanswered"}
    # logs known, not read
    # DIFFERS: the hand table says "none" for R1. But a12 cites D:d1, and the hand text
    # for R1 names D:d1 and its log. So R1 knows of D, as R3 does.
    assert R1.logs_not_read == {"D"}
    assert R2.logs_not_read == {"O"}
    assert R3.logs_not_read == {"D"}
    assert R4.logs_not_read == set()


def test_fifth_test_details(tmp_path):
    R1 = read(tmp_path, ["A"], name="r1")
    assert R1.rests_unread["A:a12"] == ["D:d1"]
    R2 = read(tmp_path, ["A", "D"], name="r2")
    assert R2.grant_withdrawals == {"D:d2": "on evidence"}
    assert R2.evidence_unread == {"D:d2": ["O:o1"]}
    R4 = read(tmp_path, ["A", "D", "O"], name="r4")
    assert R4.evidence_unread == {}
    assert R4.heads["D"] == ["D:d2"]


def test_old_head(tmp_path):
    # Case 1 of the sixth test: D hands over a prefix. It is a valid log, and the
    # server cannot tell. It reports the head it read.
    R = read(tmp_path, ["A", "D", "O"], heads={"D": "d1"})
    assert "A:a12" not in R.fell and "A:a12" in R.stands
    assert R.heads["D"] == ["D:d1"] and R.forks == []


def forked():
    """Case 2 of the sixth test: after d1, D shows O a branch with the withdrawal and A
    a branch without it."""
    r = six_three()
    r.add("D", E("s1", "show", "to: O"))              # follows d2
    r.add("D", E("s2", "show", "to: A"), after="d1")  # a second successor of d1
    return r


def test_fork_hidden_from_one_reader(tmp_path):
    r = forked()
    R = read(tmp_path, ["A", "D"], rec=r, heads={"D": "s2"})
    assert R.forks == [] and "A:a12" in R.stands and "A:a14" in R.stands


def test_fork_found_and_read_as_union(tmp_path):
    r = forked()
    a_copy, o_copy = tmp_path / "a", tmp_path / "o"
    r.save(a_copy, heads={"D": "s2"})
    r.save(o_copy, heads={"D": "s1"})
    R = report(Record.load(a_copy, o_copy))  # the two copies compared
    assert R.forks == [("D", "D:d1", ["D:d2", "D:s2"])]
    assert sorted(R.heads["D"]) == ["D:s1", "D:s2"]
    assert {"A:a12", "A:a14"} <= set(R.fell)  # the union: d1 is withdrawn


def test_fork_cited_into_other_branch(tmp_path):
    # A reader alone, with O's log citing into the branch A was not shown.
    r = forked()
    r.add("O", E("o3", "look", "D has withdrawn M", sources=["D's log"], rests=["D:d2"]))
    R = read(tmp_path, ["A", "D", "O"], rec=r, heads={"D": "s2"})
    # DIFFERS, by design of stage 2: the hand test finds the fork here because O passes
    # on d2's signed header with the cite. The server is given only logs, not headers,
    # so it reports d2 as an entry cited and not read, the seventh test's finer grain.
    assert R.forks == []
    assert R.entries_not_read == {"D:d2"}
    assert "O:o3" in R.rests_unread


def test_opposite_claims_across_branches(tmp_path):
    r = six_three()
    r.add("D", E("d3", "holder", "D reads P1", object="D", value="P1"), after="d1")
    r.add("D", E("d4", "holder", "D reads P2", object="D", value="P2"), after="d2")
    R = report(r)
    assert frozenset(("D:d3", "D:d4")) in opens(R)
    # a join closes it: D settles between its own branches
    r.add("D", E("d5", "settle", "P2 stands", answers=[
        __import__("audit").Answer("d3"), __import__("audit").Answer("d4")]))
    assert frozenset(("D:d3", "D:d4")) not in opens(report(r))
