"""Run the audit server and append every stdio message, both ways, to a JSONL file."""
import json, os, subprocess, sys, threading, time
log = open(os.environ["MCP_TEE"], "a", buffering=1)
p = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
def rec(d, line):
    try: m = json.loads(line)
    except Exception: m = line.decode("utf-8", "replace")
    log.write(json.dumps({"t": time.time(), "dir": d, "pid": os.getpid(), "msg": m}) + "\n")
def up():
    for line in sys.stdin.buffer:
        rec("in", line); p.stdin.write(line); p.stdin.flush()
    p.stdin.close()
threading.Thread(target=up, daemon=True).start()
for line in p.stdout:
    rec("out", line); sys.stdout.buffer.write(line); sys.stdout.buffer.flush()
sys.exit(p.wait())
