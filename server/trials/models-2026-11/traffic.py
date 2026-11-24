import json, sys
f = sys.argv[1]; since = float(sys.argv[2]) if len(sys.argv) > 2 else 0
calls = {}
for l in open(f):
    e = json.loads(l)
    if e["t"] < since: continue
    m = e["msg"]
    if not isinstance(m, dict): print(e["dir"], "RAW", str(m)[:200]); continue
    if e["dir"] == "in" and m.get("method") == "tools/call":
        calls[m["id"]] = m["params"]
        a = m["params"].get("arguments", {})
        print(f'{e["t"]:.0f} CALL {m["params"]["name"]}', json.dumps({k: (v if k != "body" else v[:80]) for k, v in a.items()}, ensure_ascii=False)[:300])
    elif e["dir"] == "in" and m.get("method"):
        print(f'{e["t"]:.0f} {m["method"]}')
    elif e["dir"] == "out" and m.get("id") in calls:
        r = m.get("result") or m.get("error")
        s = json.dumps(r, ensure_ascii=False)
        if 'refused' in s or m.get("error") or (isinstance(r, dict) and r.get("isError")):
            print("   -> REFUSED/ERROR", s[:300])
        else:
            print("   -> ok", s[:120])
