# make live        serve this folder and open the live page
# make playground  the same server, opened at the playground
# make check       the checks of the live page and the playground
# make test        the Python tests
# make prompt      remake live/prompt.js after server.py or card.txt changes
# PORT=8800 make live  to use another port

PORT ?= 8766
PY   ?= .venv/bin/python
URL  := http://127.0.0.1:$(PORT)

# make pdf RUN=~/Downloads/live-run.json DOCS=live/examples/regeringsbildning NAME=regeringsbildning
#   a run downloaded from the live page, as PDFs: out/NAME.pdf and out/NAME.sv.pdf.
#   DOCS is the folder with the documents the run read; the audit folder is out/runs/NAME.
RUN  ?= $(HOME)/Downloads/live-run.json
DOCS ?= live/examples
NAME ?= live-run

.PHONY: live playground serve check test prompt pdf

live:
	@(sleep 1; open $(URL)/live/) &
	@$(MAKE) --no-print-directory serve

playground:
	@(sleep 1; open $(URL)/playground/) &
	@$(MAKE) --no-print-directory serve

serve:
	@if lsof -nP -iTCP:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
	  echo "Port $(PORT) is already in use. Stop that server, or use another port: PORT=8800 make live"; \
	  exit 1; fi
	@echo "Serving $(CURDIR) at $(URL)/  (Ctrl-C to stop)"
	@python3 -m http.server $(PORT) --bind 127.0.0.1

check:
	node live/check.mjs
	node playground/check.mjs

test:
	$(PY) -m pytest -q

prompt:
	python3 live/export.py

pdf:
	node live/torecord.mjs "$(RUN)" "$(DOCS)" out/runs/$(NAME)
	$(PY) -m audit.render out/runs/$(NAME) out
	$(PY) -m audit.render out/runs/$(NAME) out --lang sv
