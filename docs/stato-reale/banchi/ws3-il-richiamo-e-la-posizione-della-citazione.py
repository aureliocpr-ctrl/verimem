"""Il muro del richiamo: una citazione ESATTA dalla CODA della proposizione basta a ritrovarla?

Cella W3-1 di 00-ESAME (misurata da Aldo il 06/09, msg 6180c13a733088f7): lo
stesso fatto, tre query — «moat evoluzione ON di default 19 luglio mandato» → 0,
«non cose spente atomica e perfetta» (sette parole prese TESTUALMENTE dalla coda
del fatto) → 0, «MOAT CONTRADDIZIONE EVOLUZIONE ON DI DEFAULT» (la testa) → 2.
La lezione di casa dice «serve una parola DEL fatto»; questa cella dice di piu':
anche una citazione esatta puo' non bastare, a seconda di DOVE sta nel testo.

TESI (falsificabile): l'embedding di un fatto lungo e' dominato dalla sua testa
(titolo, nome del topic, maiuscole), la coda pesa poco; il ramo lessicale non la
salva quando le parole della coda sono comuni. Una variabile per volta: la
POSIZIONE della citazione, a parita' di lunghezza (7 parole) e di fatto.

DISEGNO: 30 fatti vivi lunghi (>= 300 caratteri, non superseded, con
grounding_score, topic diversi), scelti a seme fisso PRIMA di guardarli. Per
ciascuno tre query di 7 parole consecutive: TESTA (le prime 7 parole di
contenuto), MEZZO (le 7 attorno al centro), CODA (le ultime 7). Per ogni query
`verimem recall` (la porta del prodotto, non una funzione interna) con k=10;
esito = il fatto compare nei 10? Si stampa QUALE fatto cade, non solo quanti.
Controllo positivo: la proposizione INTERA come query deve ritrovare >= 28/30
(se no, il righello e' rotto e non c'e' verdetto).

PREDIZIONI, depositate in questo commit PRIMA di eseguire:
  P-R1  TESTA >= 24/30 ritrovati.
  P-R2  CODA <= TESTA − 8: la posizione pesa almeno 8 fatti su 30. Se CODA e'
        entro 3 da TESTA, la tesi e' falsificata: il caso di Aldo era un fatto
        particolare (titolo in maiuscolo), non una regola.
  P-R3  MEZZO sta fra le due.
  Controllo: la stessa misura con `recall_explain` (ramo lessicale e semantico
  letti separatamente) su 5 dei 30, per dire quale dei due rami perde la coda.

NON ESEGUIBILE sotto lo STOP ai banchi (lead, 07:58): il recall carica
l'embedder. Da eseguire a «RAM ok» con la RAM letta prima, nessun warm del
giudice (ENGRAM_GROUNDING_WRITE non serve: e' solo lettura), ENGRAM_ENCODE_SERVICE=0.
Store di Aurelio: SOLO lettura (recall), nessuna scrittura.
"""
from __future__ import annotations

import os
import random
import re
import sqlite3
import subprocess
import sys

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
N_FATTI = 30
K = 10
STOP = set("""
    della delle dello degli dalla dalle dallo dagli nella nelle nello negli sulla
    sulle sullo sugli come dopo prima anche solo sono stato stata stati state
    essere avere hanno viene vengono questo questa questi queste quello quella
    ogni tutti tutte with that this from into have been were will than then
    which there their they them what when where does
""".split())


def parole_di_contenuto(testo: str) -> list[str]:
    return [t for t in re.findall(r"[A-Za-zÀ-ÿ][\w'-]{2,}", testo) if t.lower() not in STOP]


def tre_query(prop: str) -> dict[str, str] | None:
    p = parole_di_contenuto(prop)
    if len(p) < 21:
        return None
    c = len(p) // 2
    return {"TESTA": " ".join(p[:7]), "MEZZO": " ".join(p[c - 3:c + 4]), "CODA": " ".join(p[-7:])}


def recall(query: str) -> str:
    """La porta del prodotto: `verimem recall`, k=10, testo grezzo della risposta."""
    env = dict(os.environ, ENGRAM_ENCODE_SERVICE="0")
    r = subprocess.run([sys.executable, "-m", "verimem", "recall", query, "--limit", str(K)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=180, env=env)
    if r.returncode != 0:
        return f"EXIT={r.returncode}\n{r.stderr[-300:]}"
    return r.stdout


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT id, proposition, topic FROM facts WHERE superseded_by IS NULL "
        "AND grounding_score IS NOT NULL AND length(proposition) >= 300").fetchall()
    print(f"candidati (vivi, giudicati, >= 300 char): {len(righe)}")
    rnd = random.Random(20260906)
    rnd.shuffle(righe)
    scelti, topics = [], set()
    for fid, prop, topic in righe:
        if topic in topics or tre_query(prop) is None:
            continue
        topics.add(topic)
        scelti.append((fid, prop))
        if len(scelti) == N_FATTI:
            break
    print(f"scelti: {len(scelti)} (topic distinti, >= 21 parole di contenuto)\n")

    esiti = {"INTERA": [], "TESTA": [], "MEZZO": [], "CODA": []}
    for fid, prop in scelti:
        q = tre_query(prop)
        q["INTERA"] = prop[:400]
        riga = [fid]
        for nome in ("INTERA", "TESTA", "MEZZO", "CODA"):
            out = recall(q[nome])
            trovato = fid[:12] in out or prop[:60] in out
            esiti[nome].append(trovato)
            riga.append(f"{nome[0]}{'✓' if trovato else '✗'}")
        print("  ", " ".join(riga), "|", prop[:70].replace("\n", " "))
    n = len(scelti)
    tot = {k: sum(v) for k, v in esiti.items()}
    print(f"\ncontrollo positivo INTERA: {tot['INTERA']}/{n}  {'ok' if tot['INTERA'] >= n - 2 else '🔴 righello rotto: NESSUN VERDETTO'}")
    if tot["INTERA"] < n - 2:
        return 1
    print(f"TESTA {tot['TESTA']}/{n} · MEZZO {tot['MEZZO']}/{n} · CODA {tot['CODA']}/{n}")
    print(f"P-R1 TESTA >= 24: {'REGGE' if tot['TESTA'] >= 24 else '🔴 FALSIFICATA'}")
    d = tot["TESTA"] - tot["CODA"]
    print(f"P-R2 CODA <= TESTA − 8 (differenza {d}): "
          f"{'REGGE' if d >= 8 else ('🔴 FALSIFICATA: la posizione non pesa' if d <= 3 else 'indeciso')}")
    print(f"P-R3 MEZZO fra le due: {'REGGE' if tot['CODA'] <= tot['MEZZO'] <= tot['TESTA'] else 'CADE'}")
    print("caduti solo in CODA:", ", ".join(f for f, t, c in zip([s[0] for s in scelti], esiti["TESTA"], esiti["CODA"], strict=True) if t and not c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
