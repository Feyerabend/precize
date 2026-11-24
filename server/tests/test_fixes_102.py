"""Fixes after the other-models trials (findings 95, 100, 104, 105): nested quotation
marks in the verbatim check, a refused first write leaves no key, and the server's
instructions name no log and list the order reading of "or"."""
import pytest

pytest.importorskip("mcp")
import server  # noqa: E402
from audit.fetch import unquoted  # noqa: E402
from audit.sign import read_keys  # noqa: E402

from test_server import data, run  # noqa: E402

OPINION = ('the "children" are to renew only if there is no "widow" living at the '
           'time,',)


def test_nested_quotes_are_one_quote():
    body = 'the Court: "the "children" are to renew only if there is no "widow""'
    assert unquoted(body, OPINION) is None


def test_two_plain_quotes_still_checked():
    assert unquoted('"children" and "widow"', OPINION) is None
    assert unquoted('"children" and "orphan"', OPINION) == "orphan"


def test_a_false_quote_with_inner_marks_is_refused():
    body = '"the "children" may renew whenever they like"'
    assert unquoted(body, OPINION) is not None


def test_curly_quotes_as_before():
    assert unquoted("“children”", OPINION) is None
    assert unquoted("“grandchildren”", OPINION) == "grandchildren"


def test_refused_first_write_leaves_no_key(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    (root / "op.txt").write_text(OPINION[0] + "\n")
    server.ROOT = root

    async def steps(c):
        def call(tool, **kw):
            return c.call_tool(tool, {"audit": "t", **kw})
        s = data(await call("read", log="r1", path="op.txt", start=1, end=1))["source"]
        bad = data(await call("write", log="r1", kind="agent", id="q1", act="quote",
                              body='"the widow may renew"', sources=[s]))
        gone = "r1" not in read_keys(tmp_path / "t")
        pem = (tmp_path / "t" / ".keys" / "r1.pem").exists()
        good = data(await call("write", log="r1", kind="agent", id="q1", act="quote",
                               body='"children"', sources=[s]))
        return bad, gone, pem, good
    bad, gone, pem, good = run(tmp_path, steps)
    assert bad["refused"] == "verbatim"
    assert gone and not pem
    assert good["ref"] == "r1:q1"
    assert "r1" in read_keys(tmp_path / "t")


def test_instructions_name_no_log_and_list_the_order_reading():
    text = server.mcp.instructions
    assert "g1 (for A)" not in text
    assert "in order, the first and the next only failing it or after it" in text


def test_instructions_place_an_alternative_as_a_region():
    text = server.mcp.instructions
    assert "holds a region" in text and "say it does not apply" in text


def test_write_takes_between(tmp_path):
    async def steps(c):
        tools = {t.name: t for t in (await c.list_tools()).tools}
        return tools["write"].input_schema["properties"]
    assert "between" in run(tmp_path, steps)
