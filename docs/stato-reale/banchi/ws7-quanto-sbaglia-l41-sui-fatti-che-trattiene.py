"""Dei fatti che L4.1 trattiene col giudice a favore, quanti sono FALSI ALLARMI?

Segue da LANT-80: i 38 trattenuti-col-giudice-a-favore sono fermati da L4.1,
tutti. Ma «trattenuto» non vuol dire «sbagliato»: L4.1 chiede se il VALORE del
claim sta nella fonte, e in LANT-66 ho verificato che su un mio fatto aveva
ragione (avevo passato una source rigenerata, e il numero era davvero cambiato).

⇒ La domanda che decide quanto costa L4.1 e' misurabile SENZA giudizio umano:
   **il valore che L4.1 dichiara assente e' davvero assente dalla source?**

   assente davvero  -> L4.1 ha ragione, il claim era sbagliato
   presente         -> FALSO ALLARME: il numero c'era e non l'ha visto

Uso la funzione del prodotto (`valori_non_nella_fonte`) per rifare il giudizio,
e poi cerco il valore nella source con un confronto LETTERALE indipendente. Se
i due disaccordano, e' il caso interessante.

Store in SOLA LETTURA, nessuna scrittura.
"""
import re
import sqlite3

from verimem.config import CONFIG
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
cols = {r[1] for r in con.execute("PRAGMA table_info(facts)")}
CAMPO_FONTE = next((c for c in ("source", "source_text", "grounding_span") if c in cols), None)
CAMPO_TESTO = next((c for c in ("content", "text", "proposition", "fact") if c in cols), None)
print(f"  colonne usate: testo={CAMPO_TESTO!r} fonte={CAMPO_FONTE!r}")
if not (CAMPO_FONTE and CAMPO_TESTO):
    raise SystemExit("  colonne non trovate: " + ", ".join(sorted(cols)))

righe = con.execute(
    f"SELECT {CAMPO_TESTO}, {CAMPO_FONTE} FROM facts "
    f"WHERE status='quarantined' AND grounding_score>=80 "
    f"AND created_at >= strftime('%s','now') - 172800").fetchall()
print(f"  fatti da esaminare: {len(righe)}\n")

ha_ragione = falso_allarme = senza_fonte = non_giudicabile = 0
esempi_fa: list[tuple[str, str]] = []
for testo, fonte in righe:
    if not fonte or not testo:
        senza_fonte += 1
        continue
    assenti = valori_non_nella_fonte(testo, fonte)
    if not assenti:
        #: ⚠️ NON e' un falso allarme: `grounding_span` e' TRONCATO a 400 char
        #: (misurato da @ws2 in W2-31), quindi rigiudicando su di esso uso una
        #: fonte PIU' CORTA dell'originale. Contarlo come errore di L4.1
        #: sarebbe attribuire al prodotto un difetto del mio righello — la
        #: prima versione di questo banco lo faceva, e dava 24% invece di 17%.
        non_giudicabile += 1
        continue
    #: controllo LETTERALE indipendente: la cifra c'e' nella fonte, scritta?
    presenti = [a.testo for a in assenti if re.search(rf"(?<!\d){re.escape(a.testo)}(?!\d)", fonte)]
    if presenti:
        falso_allarme += 1
        esempi_fa.append((testo[:70], f"il valore {presenti[0]!r} E' nella fonte, alla lettera"))
    else:
        ha_ragione += 1

tot = ha_ragione + falso_allarme
print(f"  L4.1 HA RAGIONE (il valore manca davvero):  {ha_ragione}")
print(f"  FALSO ALLARME  (il valore c'e'):            {falso_allarme}")
print(f"  senza fonte salvata:                        {senza_fonte}")
print(f"  NON GIUDICABILI (span troncato a 400 char): {non_giudicabile}"
      "   <- non contati: sarebbe un difetto del righello, non di L4.1")
if tot:
    print(f"\n  ⇒ tasso di falso allarme di L4.1 su questa popolazione: "
          f"{falso_allarme}/{tot} = {100*falso_allarme/tot:.0f}%")
for t, perche in esempi_fa[:5]:
    print(f"\n     · «{t}…»\n       {perche}")
print("\n  ⚠️  il confronto letterale non vede le riformulazioni («13,4» contro «13.4»)")
print("     ⇒ questo conteggio SOTTOSTIMA i falsi allarmi, non li gonfia.")
