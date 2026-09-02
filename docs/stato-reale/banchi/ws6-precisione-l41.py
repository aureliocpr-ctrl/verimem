"""Quante quarantene di L4.1 sono GIUSTE? Un criterio meccanico, non una lettura.

`L4.1` ferma un claim quando porta **un numero che la fonte non contiene**. La sua
precisione non è mai stata quantificata: nel [75](../75-ho-letto-otto-quarantene-e-due-strati-si-contraddicono-sullo-stesso-fatto.md) ne ho letti quindici a mano e ho
trovato **falsi positivi e veri positivi entrambi**, senza un tasso.

⚠️ LEGGERE NON SCALA E DIPENDE DA ME. Ma il criterio di `L4.1` è **verificabile
meccanicamente**: prendo i numeri del claim, prendo i numeri della fonte, e
guardo se ce n'è uno del claim che nella fonte non c'è.

    almeno un numero del claim ASSENTE dalla fonte  -> L4.1 ha ragione
    TUTTI i numeri del claim presenti nella fonte   -> falso positivo CANDIDATO

⚠️ «CANDIDATO», non «falso positivo»: il gate ha ragioni che questo criterio non
vede — un intervallo derivato («fra il 05 e il 08»), un conteggio fatto dal
claim, una cifra scritta a parole nella fonte. Il numero che esce è un
**limite superiore** ai falsi positivi, non la loro misura.

NORMALIZZAZIONE dichiarata: si confrontano i numeri come TESTO normalizzato —
virgola decimale → punto, separatori delle migliaia rimossi, zeri finali dei
decimali tolti (`40.0` == `40`). Senza questo il confronto misurerebbe la forma
della scrittura invece della presenza del valore, che è l'errore che questa casa
ha già pagato sui decimali italiani.

SOLA LETTURA sullo store.
"""
import os
import re
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))

RE_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def normalizza(tok: str) -> str:
    """`1.234,50` → `1234.5` · `40.0` → `40` — la FORMA non deve contare."""
    t = tok.replace(" ", "")
    if "," in t and "." in t:                     # 1.234,50 → 1234.50
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:                                # 176,6 → 176.6
        t = t.replace(",", ".")
    if "." in t:
        interi, _, dec = t.partition(".")
        dec = dec.rstrip("0")
        t = interi + ("." + dec if dec else "")
    return t.lstrip("0") or "0"


RE_ORA = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
RE_DATA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")


def numeri(testo: str, stretto: bool = False) -> set[str]:
    """LARGO conta ogni glifo; STRETTO chiede che il numero stia da solo.

    ⚠️ Il regime LARGO conta il `4` di `ws4` e lo `07` di `20:07` come «il numero
    c'è nella fonte». È un difetto REALE e ha un VERSO: glifi in più nella fonte
    rendono più facile dire «tutti i numeri del claim ci sono» ⇒ **gonfia i falsi
    positivi e toglie ragione a L4.1**. Il regime STRETTO toglie orari e date e
    pretende che il numero non sia incollato a una lettera (`ws4`, `k=200x`).
    La verità sta fra i due: si riporta la FORBICE, non un numero solo.
    """
    t = testo or ""
    if stretto:
        t = RE_ORA.sub(" ", t)
        t = RE_DATA.sub(" ", t)
    fuori = set()
    for m in RE_NUM.finditer(t):
        if stretto:
            prima = t[m.start() - 1] if m.start() else " "
            dopo = t[m.end()] if m.end() < len(t) else " "
            if prima.isalpha() or dopo.isalpha():
                continue                     # `ws4`, `v2`, `200x` non sono numeri liberi
        fuori.add(normalizza(m.group(0)))
    return fuori


con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
righe = con.execute("""
 SELECT id, proposition, grounding_span FROM facts
 WHERE status='quarantined' AND quarantined_by='L4.1'
   AND grounding_span IS NOT NULL AND grounding_span != ''
""").fetchall()
con.close()

print("PRECISIONE DI L4.1 — due regimi, si legge la FORBICE")
print("quarantene di L4.1 con lo span della fonte: %d\n" % len(righe))

esiti = {}
for stretto in (False, True):
    giuste, candidati, senza_numeri = [], [], 0
    for fid, prop, span in righe:
        n_claim = numeri(prop, stretto)
        if not n_claim:
            senza_numeri += 1
            continue
        mancanti = n_claim - numeri(str(span), stretto)
        (giuste if mancanti else candidati).append((fid, sorted(mancanti)[:3], prop))
    esiti["stretto" if stretto else "largo"] = (giuste, candidati, senza_numeri)

for nome in ("largo", "stretto"):
    giuste, candidati, senza = esiti[nome]
    n = len(giuste) + len(candidati)
    print("REGIME %s  (%s)" % (nome.upper(),
          "ogni glifo conta" if nome == "largo" else "niente orari, date, numeri incollati a lettere"))
    print("  L4.1 HA RAGIONE (un numero del claim manca dalla fonte) : %4d = %5.1f%%"
          % (len(giuste), 100.0 * len(giuste) / max(1, n)))
    print("  falso positivo CANDIDATO (tutti i numeri ci sono)       : %4d = %5.1f%%"
          % (len(candidati), 100.0 * len(candidati) / max(1, n)))
    print("  claim senza numeri in questo regime                     : %4d\n" % senza)

sopravvissuti = {f for f, _m, _p in esiti["largo"][1]} & {f for f, _m, _p in esiti["stretto"][1]}
print("CANDIDATI IN ENTRAMBI I REGIMI (i piu' solidi): %d" % len(sopravvissuti))
for fid, _m, prop in esiti["stretto"][1]:
    if fid in sopravvissuti:
        print("  %-14s %s" % (fid, (prop or "").replace("\n", " ")[:72]))

print("\nCONTROLLO POSITIVO — un caso 'L4.1 ha ragione', regime stretto:")
for fid, mancanti, prop in esiti["stretto"][0][:2]:
    print("  %-14s manca dalla fonte: %s" % (fid, mancanti))
    print("      %s" % (prop or "").replace("\n", " ")[:90])

# ── UNA VARIABILE PER VOLTA ────────────────────────────────────────────────
# I due regimi qui sopra cambiano DUE cose insieme: quali numeri si leggono nel
# claim e quali nella fonte. La matrice le separa, e dice quale delle due muove
# il risultato. Senza questa tabella la «forbice» non ha un verso leggibile.
print("\nMATRICE — claim x fonte (numero di falsi positivi CANDIDATI su 154)")
print("                       fonte LARGA   fonte STRETTA")
for c in (False, True):
    riga = []
    for f in (False, True):
        k = sum(1 for _fid, prop, span in righe
                if numeri(prop, c) and not (numeri(prop, c) - numeri(str(span), f)))
        riga.append(k)
    print("  claim %-8s        %4d          %4d" % ("STRETTO" if c else "LARGO", riga[0], riga[1]))

from collections import Counter
rip = Counter((p or "").strip() for _f, p, _s in righe)
doppi = [(n, t) for t, n in rip.items() if n > 1]
print("\nCLAIM QUARANTINATI PIU' DI UNA VOLTA: %d testi distinti, %d fatti"
      % (len(doppi), sum(n for n, _t in doppi)))
for n, t in sorted(doppi, reverse=True)[:5]:
    print("  x%-3d %s" % (n, t.replace("\n", " ")[:72]))
