import os, json, glob
print("MARK === (1) COSA C'E' NELL'AMBIENTE DI QUESTO PROCESSO ===")
v = {k: os.environ[k] for k in os.environ if k.startswith(("ENGRAM_", "HIPPO_", "VERIMEM_"))}
print("MARK   variabili impostate: " + str(len(v)))
for k in sorted(v): print("MARK     " + k.ljust(34) + "= " + v[k][:40])
print("MARK")
print("MARK === (2) COSA IMPOSTA IL SERVER MCP (~/.mcp.json e settings) ===")
for p in (os.path.expanduser("~/.mcp.json"), os.path.expanduser("~/.claude/settings.json"),
          os.path.expanduser("~/.claude.json")):
    if not os.path.exists(p): print("MARK   " + p + "  -> assente"); continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("MARK   " + p + "  -> ERR " + type(e).__name__); continue
    trovati = {}
    def scava(o, path=""):
        if isinstance(o, dict):
            for k, val in o.items():
                if k.startswith(("ENGRAM_", "HIPPO_", "VERIMEM_")) and isinstance(val, str):
                    trovati[k] = val
                else: scava(val, path + "/" + str(k))
        elif isinstance(o, list):
            for x in o: scava(x, path)
    scava(d)
    print("MARK   " + os.path.basename(p) + "  -> " + str(len(trovati)) + " variabili")
    for k in sorted(trovati): print("MARK     " + k.ljust(34) + "= " + str(trovati[k])[:40])
