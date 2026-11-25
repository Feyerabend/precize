"""Print the Python report of every audit in data/ as JSON, for check.mjs to compare
with the JS port. The record is read with its public keys and no fetch log."""
import json, sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from audit.record import Record
from audit.reports import report
from audit.sign import read_keys

SKIP = {"unfetched", "committed_after_reading"}   # need the fetch log, not ported


def plain(R):
    out = {}
    for k, v in asdict(R).items():
        if k in SKIP:
            continue
        if isinstance(v, set):
            v = sorted(v)
        elif k in ("open", "open_between_agents", "forks"):
            v = sorted((json.loads(json.dumps(x)) for x in v), key=json.dumps)
        out[k] = v
    return out


if "--one" in sys.argv:   # one audit folder, not a folder of audits
    d = Path(sys.argv[1])
    print(json.dumps(plain(report(Record.load(d, keys=read_keys(d)))), ensure_ascii=False))
    sys.exit()
res = {}
for d in sorted(Path(sys.argv[1]).iterdir()):
    if d.is_dir() and any(d.glob("*.jsonl")):
        rec = Record.load(d, keys=read_keys(d))
        res[d.name] = plain(report(rec))
print(json.dumps(res, ensure_ascii=False))
