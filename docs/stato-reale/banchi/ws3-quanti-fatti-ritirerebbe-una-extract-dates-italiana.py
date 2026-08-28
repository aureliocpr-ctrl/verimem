"""Se `extract_dates` imparasse l'italiano, quanti fatti VIVI ritirerebbe?

Reperto aperto (`bf3d696e`): `extract_dates` vede l'inglese e l'ISO e **non
vede l'italiano** — né «12 marzo 2027», né «12/03/2027», né «marzo 2027».
Conseguenza: `date_conflict` **non può scattare su testo italiano**.

Avevo scritto, e lo mantengo::

    «Non tocco extract_dates stasera. E' usata da date_conflict e dallo scanner
     retroattivo: allargarla alle date italiane cambia il comportamento di un
     rilevatore di conflitti su TUTTO il corpus, e un rilevatore che comincia a
     vedere date che prima non vedeva puo' iniziare a RITIRARE fatti che oggi
     convivono. Su una coda di revisione gia' a 1057 contro soglia 500 e' il
     tipo di cura che va misurata PRIMA, non dopo.»

Questo banco **è** quella misura. **Non cura niente**: simula la cura fuori dal
prodotto e conta quanti fatti oggi vivi diventerebbero candidati a un conflitto
di data.

IL METODO, e i suoi due pezzi sono presi dal prodotto:
  · `date_conflict` chiede lo **stesso soggetto** — usa `distinctive_tokens`,
    che importo dal prodotto invece di reinventarlo;
  · e chiede date **disgiunte** con lo **stesso anno** (anni diversi sono della
    regola year-disjoint, non sua).
Le date italiane le estraggo con una regex **locale a questo banco**, che è la
cura *simulata*: se sbaglia lei, sbaglia la stima — ed è un limite, non un
dettaglio.

LA PREDIZIONE, scritta prima di eseguire: **sotto 30 coppie** in tutto il
corpus. Sopra 200 la cura non si fa senza una decisione di Aurelio: significa
centinaia di ritiri su fatti che oggi convivono.

CONTROLLO CHE DEVE POTER FALLIRE: se la mia regex italiana non trova NESSUNA
data nel corpus, non sto misurando il raggio di una cura ma una regex rotta, e
il banco non stampa una stima.

    sola lettura (`mode=ro`) · percorso chiesto a `CONFIG.semantic_db`
    NESSUNA scrittura sullo store di Aurelio

    python docs/stato-reale/banchi/ws3-quanti-fatti-ritirerebbe-una-extract-dates-italiana.py
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict

_MESI_IT = ("gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
            "settembre|ottobre|novembre|dicembre")
#: la cura SIMULATA: le tre forme italiane che `extract_dates` oggi non vede.
_IT_TESTUALE = re.compile(
    r"\b(\d{1,2})\s*(?:[°º]\s*)?(?:" + _MESI_IT + r")\b(?:,?\s{1,3}(\d{4}))?",
    re.IGNORECASE)
_IT_NUMERICA = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_MESE_N = {m: i + 1 for i, m in enumerate(_MESI_IT.split("|"))}
_UNA_RIGA = re.compile(r"\s+")


def _date_it(testo: str) -> set[tuple[int | None, int, int | None]]:
    out: set[tuple[int | None, int, int | None]] = set()
    for m in _IT_TESTUALE.finditer(testo):
        mese = None
        for nome, n in _MESE_N.items():
            if nome in m.group(0).lower():
                mese = n
                break
        if mese is None:
            continue
        anno = int(m.group(2)) if m.group(2) else None
        out.add((anno, mese, int(m.group(1))))
    for m in _IT_NUMERICA.finditer(testo):
        giorno, mese = int(m.group(1)), int(m.group(2))
        # ⚠️ GUARDIA DI VALIDITA', aggiunta dopo aver LETTO i candidati invece
        # di contarli. Senza, «la finestra 01-15/08» — un INTERVALLO, non una
        # data — veniva letta come giorno 01, MESE 15, anno 2008, e «15-24/08»
        # come mese 24. Due date-spazzatura diverse diventavano una coppia
        # candidata a conflitto. 🔑 Il testo tecnico e amministrativo italiano e'
        # pieno di intervalli scritti cosi', e una cura VERA scritta come questa
        # simulazione avrebbe lo stesso difetto: un riconoscitore di date senza
        # controllo di validita' INVENTA date dagli intervalli.
        if not (1 <= mese <= 12 and 1 <= giorno <= 31):
            continue
        a = int(m.group(3))
        if a < 100:
            a += 2000
        out.add((a, mese, giorno))
    return out


def main() -> int:
    from verimem.config import CONFIG
    from verimem.quantity_match import distinctive_tokens, extract_dates

    db = str(CONFIG.semantic_db)
    print("  REGIME, dichiarato E misurato:")
    print(f"    store: {db}")
    print("    SOLA LETTURA (mode=ro) · nessuna scrittura · store di Aurelio")
    print("    NESSUNA CURA nel prodotto: la cura e' SIMULATA in questo file.")

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        righe = list(con.execute(
            "SELECT id, topic, proposition FROM facts "
            "WHERE superseded_by IS NULL AND proposition IS NOT NULL"))
    finally:
        con.close()
    print(f"    fatti VIVI (superseded_by IS NULL): {len(righe)}")

    per_topic: dict[str, list[tuple[str, str, set]]] = defaultdict(list)
    con_data_it = 0
    gia_viste = 0
    for fid, topic, prop in righe:
        d_it = _date_it(prop or "")
        if not d_it:
            continue
        con_data_it += 1
        if extract_dates(prop or ""):
            gia_viste += 1        # il prodotto la vede gia': non e' un guadagno
        per_topic[topic or "(senza topic)"].append((fid, prop, d_it))

    print("\n  ══ LA POPOLAZIONE ══")
    print(f"     fatti con una data ITALIANA (regex simulata) .. {con_data_it}"
          f"   ({100.0 * con_data_it / max(len(righe), 1):.1f}% dei vivi)")
    print(f"     ► di cui il prodotto ne vede gia' una .......... {gia_viste}"
          f"   (fatti, non date: qui non c'e' guadagno)")
    print(f"     topic che ne contengono almeno uno ............ {len(per_topic)}")

    if con_data_it == 0:
        print("\n     CONTROLLO CADUTO: nessuna data italiana trovata ⇒ misuro una")
        print("     regex rotta, non il raggio di una cura. NESSUNA STIMA.")
        return 1

    coppie = 0
    esempi: list[tuple[str, str, str]] = []
    for topic, fatti in per_topic.items():
        for i in range(len(fatti)):
            for j in range(i + 1, len(fatti)):
                _fa, pa, da = fatti[i]
                _fb, pb, db_ = fatti[j]
                if da & db_:
                    continue                    # data condivisa: nessun movimento
                if not (distinctive_tokens(pa) & distinctive_tokens(pb)):
                    continue                    # soggetti non correlati
                # stesso anno (o anno non detto): gli anni diversi sono della
                # regola year-disjoint, non di date_conflict
                if not any((ya is None or yb is None or ya == yb)
                           for ya, _ma, _dda in da for yb, _mb, _ddb in db_):
                    continue
                coppie += 1
                if len(esempi) < 40:
                    esempi.append((topic, pa, pb))

    print("\n  ══ IL RAGGIO DELLA CURA ══")
    print(f"     coppie che diventerebbero CANDIDATE a un conflitto di data:"
          f" {coppie}")

    if esempi:
        print("\n  ESEMPI (vanno LETTI: una coppia candidata non e' un errore):")
        # ⚠️ DUE BUG MIEI, dallo stesso episodio di escaping: la regex era
        # `\\s+` — un BACKSLASH LETTERALE seguito da `s`, non uno spazio — quindi
        # la normalizzazione non ha mai funzionato; e un backslash dentro una
        # f-string e' SINTASSI NON VALIDA su Python 3.10, cioe' questo banco non
        # si sarebbe nemmeno PARSATO su una versione della matrice CI. Non tocca
        # i conteggi, solo la stampa — ma un banco che non gira da altri non e'
        # un banco. Sostituzione fuori dalla f-string.
        for topic, pa, pb in esempi:  # TUTTE: si leggono, non si contano
            a1 = _UNA_RIGA.sub(" ", pa)
            b1 = _UNA_RIGA.sub(" ", pb)
            print(f"     · topic {topic[:40]}")
            print(f"       A: {a1[:76]}")
            print(f"       B: {b1[:76]}")

    print("\n  ══ VERDETTO sulla PREDIZIONE ══")
    print(f"     previsto: SOTTO 30 coppie   ·   misurato: {coppie}")
    if coppie < 30:
        print("     RETTA: il raggio e' piccolo e leggibile a mano ⇒ la cura si")
        print("     puo' proporre portando le coppie, non solo il numero.")
    elif coppie < 200:
        print("     SBAGLIATA nella taglia, ma sotto 200: proponibile dichiarando")
        print("     quante coppie tocca, e dopo averle LETTE.")
    else:
        print("     FALSIFICATA: sopra 200. La cura NON si fa senza una decisione")
        print("     di Aurelio — sono centinaia di ritiri su fatti che oggi")
        print("     convivono, su una coda gia' oltre la soglia.")

    print("\n  ⚠️ LIMITI: la regex italiana e' MIA e simula la cura — se sbaglia")
    print("     lei, sbaglia la stima. «Candidata a conflitto» NON e' «ritirata»:")
    print("     `date_conflict` ha altre guardie (soggetti nominati disgiunti,")
    print("     qualificatori di contrasto) che qui non applico ⇒ il numero e' un")
    print("     TETTO SUPERIORE. Il confronto e' fra fatti VIVI dello stesso")
    print("     topic: due fatti correlati in topic diversi mi sfuggono. E il")
    print("     corpus si muove: siamo in otto a scrivere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
