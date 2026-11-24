"""Signatures (stage 4). Each log has one key. The key's public half is registered in the
audit's `keys.json` with the log's kind. An entry is signed over its hash.

Who an author is cannot be settled inside the logs (the seventh test). The registry is
where that is decided: whoever registers a key for a log is taken to be its author. The
server registers keys only for agent logs. A person registers their own key with
`python -m audit.person`, outside the server, so an agent calling the server cannot sign
as a person.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization as S
from cryptography.hazmat.primitives.asymmetric.ed25519 import (Ed25519PrivateKey,
                                                               Ed25519PublicKey)

from .record import Refused


def new_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def pub_hex(k: Ed25519PrivateKey) -> str:
    return k.public_key().public_bytes(S.Encoding.Raw, S.PublicFormat.Raw).hex()


def sign(k: Ed25519PrivateKey, h: str) -> str:
    return k.sign(bytes.fromhex(h)).hex()


def verify(pub: str, h: str, sig: str | None) -> bool:
    if not sig:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
            bytes.fromhex(sig), bytes.fromhex(h))
        return True
    except Exception:
        return False


def save_key(k: Ed25519PrivateKey, path: Path, passphrase: bytes | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    enc = S.BestAvailableEncryption(passphrase) if passphrase else S.NoEncryption()
    path.write_bytes(k.private_bytes(S.Encoding.PEM, S.PrivateFormat.PKCS8, enc))
    os.chmod(path, 0o600)


def load_key(path: Path, passphrase: bytes | None = None) -> Ed25519PrivateKey:
    try:
        return S.load_pem_private_key(Path(path).read_bytes(), passphrase)
    except (TypeError, ValueError):  # missing, unneeded or wrong passphrase
        from .record import Refused
        raise Refused("key", f"{path}: the passphrase is missing or wrong") from None


# --- the registry -------------------------------------------------------------
def read_keys(folder: Path) -> dict[str, dict]:
    p = Path(folder) / "keys.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def register(folder: Path, log: str, kind: str, pub: str) -> None:
    """Register a log's key. A log keeps its first key. A key change would be an entry
    signed by both keys, which is not built."""
    folder = Path(folder)
    keys = read_keys(folder)
    if log in keys:
        if keys[log] == {"kind": kind, "key": pub}:
            return
        raise Refused("key", f"log {log} already has a key; a key change is not built")
    keys[log] = {"kind": kind, "key": pub}
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "keys.json").write_text(json.dumps(keys, indent=1, sort_keys=True),
                                      encoding="utf-8")


def unregister(folder: Path, log: str) -> None:
    """Take back a key registered for a log that has no entries, as after a refused
    first write (finding 104)."""
    folder = Path(folder)
    if (folder / f"{log}.jsonl").exists():
        raise Refused("key", f"log {log} has entries; its key stays")
    keys = read_keys(folder)
    if keys.pop(log, None) is not None:
        (folder / "keys.json").write_text(json.dumps(keys, indent=1, sort_keys=True),
                                          encoding="utf-8")
