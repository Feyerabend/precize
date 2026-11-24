"""Finding 73: a run quoted an inquiry's summary printed in a bill's annex without `via`.
The server cannot tell (read returned the bill), so the instructions say it."""
import server


def test_instructions_name_text_printed_inside_a_source():
    text = server.mcp.instructions
    assert "second hand" in text and "`via`" in text and "annex" in text


def test_write_doc_names_another_bodys_text():
    src = open(server.__file__).read()
    assert "another body's text printed inside your source" in src
