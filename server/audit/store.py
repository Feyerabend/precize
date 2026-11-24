"""An audit on disk: one folder, one JSON Lines file per log, `keys.json`, and the
fetch ledger. Writing goes through `append`, which checks, signs and appends."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import fetch
from .record import Entry, Record, Refused
from .sign import pub_hex, read_keys, sign


def load(folder: Path, logs: list[str] | None = None,
         heads: dict[str, str] | None = None) -> Record:
    folder = Path(folder)
    keys = read_keys(folder)
    rec = Record.load(folder, keys=keys) if folder.exists() else Record(checks=False)
    if logs or heads:
        with tempfile.TemporaryDirectory() as t:
            rec.save(t, heads=heads, logs=logs)
            signed = rec.signed
            rec = Record.load(t, keys=keys)
            rec.signed = signed & set(rec.logs)
    rec.folder = folder   # where the fetch log is, for unfetched and committed_after_reading
    return rec


def append(folder: Path, log: str, e: Entry, key, after: str | None = None) -> Entry:
    """Check e against the record and the log's registered key, sign it, append it."""
    folder = Path(folder)
    reg = read_keys(folder).get(log)
    if not reg or reg["key"] != pub_hex(key):
        raise Refused("key", f"no key registered for {log} matches the signer")
    if reg["kind"] != e.kind:
        raise Refused("kind", f"log {log} is registered as a {reg['kind']}'s")
    rec = load(folder)
    rec.checks = True
    if e.kind == "agent" and e.act == "precize" and not e.narrows:
        raise Refused("narrows", f"{log}:{e.id}: a precize names what it narrows (the "
                      "mark, for first readings)")
    rec.add(log, e, after=after)
    fetch.check(folder, rec, e)
    e.sig = sign(key, e.hash)
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / f"{log}.jsonl", "a", encoding="utf-8") as out:
        out.write(json.dumps(e.to_json(), ensure_ascii=False) + "\n")
    return e
