"""LIVELLO: lo store vivo + la porta di ricerca — in sola lettura.

Il daemon di consolidamento gira, e cio' che produce e' tracciabile e servibile.

    python docs/stato-reale/banchi/ws3-il-consolidamento-gira-e-i-suoi-master-sono-tracciabili.py

⚡ COSTO ZERO: nessun modello, nessuna scrittura, `mode=ro`.

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Terza voce dello stesso giro: dopo il tier Documents, il consolidamento. Le tre
domande vanno tenute separate, perche' confonderle e' il modo standard di
sbagliare:
    ① ESISTE?   un messaggio del gancio dice «worker FIRED» -> dice che e'
                PARTITO, non che ha prodotto qualcosa. Non basta.
    ② GIRA?     si contano le righe che produce, con le date.
    ③ SERVE?    cio' che produce e' poi restituibile? Un fatto senza embedding
                non esce dal recall semantico: e' la differenza fra «prodotto»
                e «servibile».

━━ MISURATO IL 2026-09-04 alle 20:10 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    fatti nel corpus vivo                      17.543

    ① fatti prodotti (topic che finisce in auto-MASTER)   147
       primo   20/06 14:57   project/hippoagent/auto-MASTER
       ultimo  04/09 18:41   verimem/numero-della-patch/auto-MASTER
       non superati  147 / 147     ·  stato: model_claim x147
    ② cluster distinti 147  ·  fatti nei topic toccati  1.724
    ③ master SENZA embedding: 0 / 147   ⇒ tutti servibili

⇒ ① ESISTE, ② GIRA (l'ultimo novanta minuti prima della misura), ③ SERVIBILE.
Nessun difetto: ho fatto le tre domande separate e sono tutte in positivo.

━━ DUE COSE CHE IL PRODOTTO FA BENE, e vanno dette con la stessa precisione ━━
① **I master CITANO cio' che riassumono.** Il master di oggi porta in
   `verified_by` i cinque `fact:<id>` dei sotto-fatti. Un riassunto tracciabile
   non e' una sintesi che sostituisce le fonti: e' un indice che ci riporta.
② **La ricevuta della ricerca dichiara cio' che NON mostra.** Sulla stessa
   interrogazione:
       trattenuti: 137 — «sono stati TRATTENUTI dal gate e non compaiono qui:
       non erano sostenuti dalla loro fonte. Non sono persi.»
       sotto_il_pavimento: pavimento 0,8805 · score migliore 0,8322 —
       «nessun risultato supera la soglia: probabilmente la risposta NON e' in
       memoria. I risultati sono qui sotto, non tagliati — decidi tu.»
   Dichiarare di non aver superato il proprio pavimento, e mostrare comunque i
   risultati lasciando la decisione a chi legge, e' l'opposto del silenzio che
   si legge come assenza.

━━ CIO' CHE RESTA APERTO, e non lo riempio ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
· 147 cluster coprono 1.724 fatti su 17.543: il **9,8%** del corpus. Perche'
  solo un decimo? Se c'e' una soglia di ampiezza sotto la quale non si
  consolida, non l'ho misurata — e senza quel dato «copre poco» sarebbe
  un'accusa, non una misura.
· Tutti i master sono `model_claim` con `grounding_score` nullo: per costruzione
  non hanno una fonte esterna, sono il sistema che riassume se stesso. Coerente
  con la definizione, ma vuol dire che il tier degli entry-point NON e'
  verificato. Se un giorno un master competesse nel ranking con i fatti che
  riassume, andrebbe misurato — non l'ho fatto.

🔴 COME MUORE: se un domani i master risultassero senza embedding, o superati in
massa, o l'ultimo fosse vecchio di settimane, allora il daemon avrebbe smesso e
questa pagina andrebbe rifatta.
"""
from __future__ import annotations

import datetime as dt
import sqlite3

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"


def quando(ts) -> str:
    try:
        return dt.datetime.fromtimestamp(float(ts)).strftime("%d/%m %H:%M")
    except (TypeError, ValueError, OSError):
        return "?"


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        tot = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        righe = con.execute(
            "SELECT topic, created_at, status, superseded_by FROM facts "
            "WHERE topic LIKE '%auto-MASTER' ORDER BY created_at").fetchall()
        senza_emb = con.execute(
            "SELECT COUNT(*) FROM facts WHERE topic LIKE '%auto-MASTER' "
            "AND (embedding IS NULL OR LENGTH(embedding)=0)").fetchone()[0]
        prefissi = {r[0].rsplit("/", 1)[0] for r in righe}
        n_cluster = 0
        if prefissi:
            segna = ",".join("?" * len(prefissi))
            n_cluster = con.execute(
                f"SELECT COUNT(*) FROM facts WHERE topic IN ({segna})",  # noqa: S608
                tuple(prefissi)).fetchone()[0]
    finally:
        con.close()

    print("IL CONSOLIDAMENTO: esiste? gira? cio' che produce e' servibile?\n")
    print(f"  fatti nel corpus vivo        : {tot}")
    print(f"① master prodotti             : {len(righe)}")
    if righe:
        print(f"   primo                      : {quando(righe[0][1])}  {righe[0][0][:48]}")
        print(f"   ultimo                     : {quando(righe[-1][1])}  {righe[-1][0][:48]}")
        print(f"   non superati               : {sum(1 for r in righe if not r[3])}"
              f" / {len(righe)}")
        stati: dict[str, int] = {}
        for r in righe:
            stati[r[2]] = stati.get(r[2], 0) + 1
        print(f"   per stato                  : {stati}")
    print(f"② cluster distinti            : {len(prefissi)}  ·  fatti nei topic"
          f" toccati: {n_cluster}  ({100.0 * n_cluster / max(1, tot):.1f}% del corpus)")
    print(f"③ master SENZA embedding      : {senza_emb} / {len(righe)}")
    print()
    if righe and senza_emb == 0 and all(not r[3] for r in righe):
        print("  ⇒ esiste, gira, ed e' servibile. Nessun difetto trovato:")
        print("    le tre domande erano separate e sono tutte in positivo.")
    else:
        print("  🔴 qualcosa e' cambiato: rileggere il docstring e rifare la pagina.")


if __name__ == "__main__":
    main()
