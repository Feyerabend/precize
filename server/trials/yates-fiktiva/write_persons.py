"""Write the two fictional persons' entries into an audit, each with its own key.

  .venv/bin/python trials/skollagen-fiktiva/write_persons.py AUDIT_DIR KEY_DIR

A key is made and registered for a log the first time (KEY_DIR/<log>.pem); later runs
reuse it. Entries already in a log are skipped, so the script can be run again after a
refusal. Prints each ref, or the refusal, and stops at the first refusal.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from audit import person  # noqa: E402
from audit.record import Refused  # noqa: E402
from audit.store import load  # noqa: E402


def main(folder, keydir):
    folder, keydir = Path(folder), Path(keydir)
    plan = json.loads((Path(__file__).parent / "entries.json").read_text(encoding="utf-8"))
    for log, entries in plan.items():
        if log.startswith("_"):
            continue
        key = keydir / (re.sub(r"[^A-Za-z0-9]+", "-", log).strip("-") + ".pem")
        if not key.exists():
            keydir.mkdir(parents=True, exist_ok=True)
            print(log, "key", person.init(folder, log, key))
        have = {e.id for e in load(folder).logs.get(log, [])}
        for d in entries:
            if d["id"] in have:
                continue
            try:
                e = person.write(folder, log, key, d)
            except Refused as r:
                print("REFUSED", f"{log}:{d['id']}", r)
                return 1
            print(e.ref)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
