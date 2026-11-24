"""A person's own writing tool, outside the MCP server (stage 4).

The server holds keys only for agent logs and refuses kind='person'. A person makes a key
once and registers it for their log, then writes with it:

  python -m audit.person init  AUDIT_DIR LOG KEYFILE
  python -m audit.person write AUDIT_DIR LOG KEYFILE '{"id": "a1", "act": "grant", ...}'

The key file stays with the person. Whoever holds it is, for the record, the author of the
log: that is decided here, outside the logs, as the seventh test said it must be.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
from pathlib import Path

from .record import Answer, Entry, Refused
from .sign import load_key, new_key, pub_hex, read_keys, register, save_key
from .store import append


def _pass() -> bytes | None:
    p = os.environ.get("AUDIT_PASSPHRASE")
    if p is None and sys.stdin.isatty():
        p = getpass.getpass("passphrase (empty for none): ")
    return p.encode() if p else None


def init(folder, log, keyfile, passphrase=None):
    """Check first, then save. A second init must not overwrite the key a log is
    registered with: the old key would be lost and the log could not grow."""
    if log in read_keys(Path(folder)):
        raise Refused("key", f"log {log} already has a key; a key change is not built")
    if Path(keyfile).exists():
        raise Refused("key", f"{keyfile} exists; init does not overwrite a key file")
    k = new_key()
    save_key(k, Path(keyfile), passphrase)
    register(Path(folder), log, "person", pub_hex(k))
    return pub_hex(k)


def entry(d: dict) -> Entry:
    d = dict(d)
    d["answers"] = [Answer(a["ref"], bool(a.get("disputes", False)), a.get("meets"))
                    for a in d.get("answers", [])]
    d["kind"] = "person"
    return Entry(**d)


def write(folder, log, keyfile, d: dict, passphrase=None, after=None):
    return append(Path(folder), log, entry(d), load_key(Path(keyfile), passphrase), after)


def main(argv):
    cmd, folder, log, keyfile, *rest = argv
    try:
        if cmd == "init":
            print(init(folder, log, keyfile, _pass()))
        elif cmd == "write":
            e = write(folder, log, keyfile, json.loads(rest[0]), _pass())
            print(json.dumps({"ref": e.ref, "hash": e.hash}))
        else:
            raise SystemExit(__doc__)
    except Refused as r:
        print(json.dumps({"refused": r.rule, "message": str(r)}))
        return 1
    except json.JSONDecodeError as x:
        print(json.dumps({"refused": "entry", "message": f"entry: not JSON ({x})"}))
        return 1
    except TypeError as x:  # a field missing or unknown
        print(json.dumps({"refused": "entry", "message": f"entry: {x}".replace("Entry.__init__() ", "")}))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
