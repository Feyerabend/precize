"""A second init refused (live trial, 2026-11-20): it must leave the key file alone."""
import pytest

from audit import Refused
from audit import person


def test_a_second_init_keeps_the_key(tmp_path):
    key = tmp_path / "k.pem"
    pub = person.init(tmp_path / "audit", "A", key)
    before = key.read_bytes()
    with pytest.raises(Refused, match="key"):
        person.init(tmp_path / "audit", "A", key)
    assert key.read_bytes() == before
    with pytest.raises(Refused, match="key"):
        person.init(tmp_path / "audit", "B", key)
    assert key.read_bytes() == before
    from audit.sign import load_key, pub_hex
    assert pub_hex(load_key(key, None)) == pub


def test_a_wrong_passphrase_is_refused_not_a_traceback(tmp_path):
    key = tmp_path / "k.pem"
    person.init(tmp_path / "audit", "A", key, b"right")
    for bad in (None, b"wrong"):
        with pytest.raises(Refused, match="passphrase"):
            person.write(tmp_path / "audit", "A", key,
                         {"id": "x", "act": "look", "body": "x"}, bad)
