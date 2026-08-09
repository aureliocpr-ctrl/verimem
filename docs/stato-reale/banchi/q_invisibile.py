import json, collections
p = "C:/Users/aurel/.engram/events.jsonl"
uguali = diversi = 0; nomi = collections.Counter()
with open(p, encoding="utf-8", errors="replace") as f:
    for riga in f:
        try: d = json.loads(riga)
        except Exception: continue
        nomi[d.get("name")] += 1
        if d.get("name") != "flow.supersession": continue
        pl = d.get("payload") or {}
        if not isinstance(pl, dict): continue
        if str(pl.get("branch")) == str(pl.get("reason")): uguali += 1
        else: diversi += 1
print("MARK branch == reason: " + str(uguali) + "   branch != reason: " + str(diversi))
print("MARK")
print("MARK === esiste un evento per il conflitto RILEVATO ma NON superseduto? ===")
print("MARK   tutti i nomi di evento nel file (" + str(len(nomi)) + " distinti):")
for k, c in nomi.most_common(30):
    print("MARK     " + str(k).ljust(34) + str(c).rjust(6))
