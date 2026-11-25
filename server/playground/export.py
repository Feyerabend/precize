"""Export the trials for the playground: each audit's logs, public keys and about.json,
written as one script file the page loads (playground/trials.js), so the page runs from
disk with no server.

Reads only <audit>/*.jsonl, keys.json (public halves) and about.json, and the card. Never the private
keys in .keys/ or the fetched texts in .fetched/.

  .venv/bin/python playground/export.py [AUDIT ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
CARD = HERE.parent.parent / "manual/body/08-the-procedure-on-one-page.tex"   # as the server serves it


def card() -> str:
    if not CARD.exists():   # the server's copy: the same card under a three-line heading
        t = (HERE.parent / "card.txt").read_text(encoding="utf-8")
        return t.split("\n\n", 2)[2] if t.startswith("The procedure on one sheet") else t
    t = CARD.read_text(encoding="utf-8")
    return t.split("\\begin{card}\n", 1)[1].split("\\end{card}", 1)[0].rstrip() + "\n"


def audit(folder: Path) -> dict:
    logs = {}
    for p in sorted(folder.glob("*.jsonl")):
        logs[p.stem] = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()
                        if line.strip()]
    read = lambda n: json.loads((folder / n).read_text(encoding="utf-8")) if (folder / n).exists() else {}
    return {"name": folder.name, "about": read("about.json"), "keys": read("keys.json"), "logs": logs}


def main(names: list[str]) -> None:
    folders = [DATA / n for n in names] if names else sorted(
        p for p in DATA.iterdir() if p.is_dir() and any(p.glob("*.jsonl")))
    out = [audit(f) for f in folders]
    out.sort(key=lambda a: a["about"].get("order", 999))
    js = ("window.TRIALS = " + json.dumps(out, ensure_ascii=False, indent=0) + ";\n"
          "window.CARD = " + json.dumps(card(), ensure_ascii=False) + ";\n")
    (HERE / "trials.js").write_text(js, encoding="utf-8")
    print(f"{len(out)} audits -> {HERE / 'trials.js'}")


if __name__ == "__main__":
    main(sys.argv[1:])
