"""Finding 107: an entry named in `sources` is refused at write time and listed in old
logs, not counted as unfetched; the library's report() shows unfetched and
committed_after_reading when the record is loaded from a folder; two fetches that join
cover the lines between them."""
import pytest

from audit import Entry as E, Record, Refused, fetch, report, store

S = '"The insured performs landscaping."'


def test_entry_as_source_is_refused():
    r = Record()
    r.add("g1", E("q1", "quote", S, kind="agent", sources=["op.txt, line 1"]))
    with pytest.raises(Refused) as x:
        r.add("g1", E("m1", "mark", '"landscaping"', kind="agent", value="landscaping",
                      rests=["q1"], sources=["q1"]))
    assert x.value.rule == "sources"
    with pytest.raises(Refused):
        r.add("g1", E("m1", "mark", '"landscaping"', kind="agent", value="landscaping",
                      rests=["q1"], sources=["g1:q1"]))


def test_old_logs_list_it_and_unfetched_skips_it(tmp_path):
    r = Record(checks=False)
    r.add("g1", E("q1", "quote", S, kind="agent", sources=["op.txt, line 1"]))
    r.add("g1", E("m1", "mark", '"landscaping"', kind="agent", value="landscaping",
                  rests=["q1"], sources=["q1"]))
    R = report(r)
    assert R.entries_as_sources == {"g1:m1": ["q1"]}   # as written
    assert fetch.unfetched(tmp_path, r) == {"g1:q1": ["op.txt, line 1"]}


def test_library_report_reads_the_fetch_log(tmp_path):
    f = tmp_path / "a"
    r = Record()
    r.add("g1", E("q1", "quote", S, kind="agent", sources=["op.txt, line 1"]))
    r.save(f)
    R = report(store.load(f))
    assert R.unfetched == {"g1:q1": ["op.txt, line 1"]}
    fetch.note(f, "g1", "op.txt", 1, 1, S.strip('"'), 0)
    assert report(store.load(f)).unfetched == {}
    assert report(r).unfetched == {}          # a record built in memory has no fetch log


def test_joined_fetches_cover():
    fs = [{"path": "op.txt", "a": 1, "b": 400}, {"path": "op.txt", "a": 401, "b": 748}]
    assert len(fetch._covering(fs, "op.txt, lines 1-748")) == 2
    assert fetch._covering(fs[:1] + [{"path": "op.txt", "a": 402, "b": 748}],
                           "op.txt, lines 1-748") == []
    assert len(fetch._covering(fs, "op.txt, lines 10-20")) == 1
