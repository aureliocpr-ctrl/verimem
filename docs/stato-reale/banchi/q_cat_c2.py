import json, collections
p = "C:/Users/aurel/.engram/events.jsonl"
coh, sup_ids, kinds = [], set(), collections.Counter()
for riga in open(p, encoding="utf-8", errors="replace"):
    try: d = json.loads(riga)
    except Exception: continue
    n, pl = d.get("name"), d.get("payload") or {}
    if not isinstance(pl, dict): continue
    if n == "coherence_warning":
        coh.append(pl); kinds[pl.get("kind")] += 1
    elif n == "flow.supersession":
        sup_ids.add(str(pl.get("loser_id"))); sup_ids.add(str(pl.get("winner_id")))
print("MARK coherence_warning per tipo: " + str(dict(kinds)))
print("MARK supersessioni avvenute: " + str(len(sup_ids)) + " id coinvolti")
print("MARK")
print("MARK === CATEGORIA (c): rilevato e NON agito ===")
senza = [c for c in coh if str(c.get("fact_id")) not in sup_ids and str(c.get("other_fact_id")) not in sup_ids]
print("MARK   coherence_warning totali:                    " + str(len(coh)))
print("MARK   di cui SENZA nessuna supersessione dei due:   " + str(len(senza)))
print("MARK === le righe, tutte (sono poche: si guardano) ===")
for c in senza[:14]:
    print("MARK   " + str(c.get("kind")).ljust(16) + str(c.get("topic"))[:20].ljust(22) + str(c.get("details"))[:52])
