# A/B della finestra dell'anteprima: riproduce ESATTAMENTE cli.py:865-869
text = ("Testo neutro di riempimento. "*32) + "La sede di Bolzano contiene 777 pallet."
low = text.lower()
atteso = text.index("La sede di Bolzano")

def finestra(query, togli_punteggiatura=False, togli_vuote=False):
    terms = [t for t in query.lower().split() if t.strip()]
    if togli_punteggiatura:
        terms = [t.strip("?.,;:!") for t in terms]
    if togli_vuote:
        terms = [t for t in terms if t not in {"di","la","il","e","a","in","che","quanti","contiene"}]
    pos = min((p for p in (low.find(t) for t in terms) if p >= 0), default=0)
    start = max(0, pos - 90)
    snip = text[start:start+180]
    return pos, start, ("Bolzano" in snip)

q = "Quanti pallet contiene la sede di Bolzano?"
print(f"chunk di {len(text)} caratteri; la risposta inizia a {atteso}\n")
print(f"{'variante':<44} {'pos':>5} {'start':>6}  risposta visibile?")
for etichetta, kw in [
    ("A) come oggi (cli.py:868)",              dict()),
    ("B) tolta la punteggiatura",              dict(togli_punteggiatura=True)),
    ("C) tolte le parole vuote",               dict(togli_vuote=True)),
    ("D) tolte entrambe",                      dict(togli_punteggiatura=True, togli_vuote=True)),
]:
    p, s, ok = finestra(q, **kw)
    print(f"{etichetta:<44} {p:>5} {s:>6}  {'SI' if ok else 'NO'}")

print("\n-- quale termine vince il min(), variante A --")
for t in [x for x in q.lower().split() if x.strip()]:
    print(f"   {t!r:<12} find() = {low.find(t)}")
