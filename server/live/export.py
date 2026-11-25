"""Export what the live page tells the agent: the server's instructions (with the STOP
rules), the tool descriptions of write, read, report and entry, and the card. Taken from
server.py by parsing it, not importing it, so the page says what the server says.

  python3 live/export.py          (writes live/prompt.js)
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent / "server.py"
sys.path.insert(0, str(HERE.parent / "playground"))
from export import card  # noqa: E402  (the same card the playground shows)


def strings(tree: ast.Module) -> dict:
    out, consts = {"tools": {}}, {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    consts[t.id] = node.value.value
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            names = [node.name]
            for d in node.decorator_list:
                if isinstance(d, ast.Call):
                    names += [k.value.value for k in d.keywords if k.arg == "name"]
            if doc:
                out["tools"][names[-1]] = doc
        # mcp = MCPServer("...", instructions=("..." + STOP))
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            for k in node.value.keywords:
                if k.arg == "instructions":
                    out["instructions"] = flat(k.value, consts)
    out["stop"] = consts["STOP"]
    return out


def flat(v: ast.AST, consts: dict) -> str:
    if isinstance(v, ast.Constant):
        return v.value
    if isinstance(v, ast.Name):
        return consts[v.id]
    if isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add):
        return flat(v.left, consts) + flat(v.right, consts)
    raise ValueError(f"cannot read {ast.dump(v)}")


def main() -> None:
    s = strings(ast.parse(SERVER.read_text(encoding="utf-8")))
    keep = {k: s["tools"][k] for k in ("write", "read", "report", "entry")}
    js = ("/* Made by live/export.py from server.py and the card; do not edit by hand. */\n"
          "window.SERVER = " + json.dumps({"instructions": s["instructions"], "stop": s["stop"],
                                           "tools": keep}, ensure_ascii=False, indent=1) + ";\n"
          "window.CARD = " + json.dumps(card(), ensure_ascii=False) + ";\n")
    (HERE / "prompt.js").write_text(js, encoding="utf-8")
    print(f"{len(keep)} tool descriptions, {len(s['instructions'])} characters of instructions"
          f" -> {HERE / 'prompt.js'}")


if __name__ == "__main__":
    main()
