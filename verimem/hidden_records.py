"""Il fatto nascosto su quel record esiste, e chi fa la domanda non lo sa.

NASCE DA DUE DIFETTI CHE SI ERANO SEMPRE GUARDATI SEPARATI, e sono la stessa
cosa vista da due lati (misurati il 2026-08-04, fuori da pytest):

① IL CATALOGO. Venticinque schede distinte entrano, e ne resta UNA servibile::

       recall(«Quanto zinco contiene il campione S-007?»)
         -> «Il campione S-025 contiene zinco a 35 mg/l»    score 0.8786

   Sbagliata, e confidente: in un registro tutte le frasi hanno la stessa
   forma, quindi il coseno misura la forma e non il contenuto. L'omogeneita'
   del corpus non abbassa il segnale — ALZA la confidenza sull'errore.
   Misurato su registri in tedesco, inglese, francese e spagnolo: 8 su 8.

② L'AGGIORNAMENTO FERMO IN QUARANTENA. Dodici aggiornamenti di stato veri,
   cinque bloccati dal gate, e il vecchio stato resta vivo::

       [VIVO    ] model_claim   «Il ticket T-451 e' aperto...»
       [NASCOSTO] quarantined   «Il ticket e' stato chiuso il 3 marzo.»
       recall(«Il ticket T-451 e' ancora aperto?») -> «e' aperto»   0.8819

   ⚠️ Il gate NON e' chiuso: con `verified_by=['approval:C-12_signed']` nel
   formato che il detector stesso dichiara, 4 fatti su 4 entrano. Il difetto
   non e' che la porta sia sbarrata — e' che chi fa la domanda non sa che
   dietro la risposta c'e' un aggiornamento fermo.

QUESTO MODULO NON DECIDE, DICHIARA. Non tocca il ranking, non cambia cosa si
serve, non annulla nessun ritiro: dice che su quel record esiste un fatto
nascosto. E' l'unica mossa che non chiede di distinguere un catalogo da un
aggiornamento — otto criteri su otto sono caduti provandoci (`62c2a8610c99`),
e nessuno di quei fallimenti era per disattenzione: l'informazione, al momento
della scrittura, non c'e'. Al momento della LETTURA c'e' un terzo elemento che
il write path non ha mai avuto: la domanda.

⚠️ DUE STRADE GIA' MORTE, per non riprovarci:
  * IL SEPARATORE E' OBBLIGATORIO. Senza, l'estrattore prendeva «M1» «B2»
    «P0» «V2» — che nel corpus di casa sono i NOMI DELLE REGOLE — e dichiarava
    un codice nel 54% dei fatti servibili (2891 su 5325). Col separatore: 18%.
    Il prezzo dichiarato: un registro che scrive «S007» attaccato non viene
    visto. E' il verso giusto in cui sbagliare.
  * L'ANCORAGGIO (un codice o una data nel testo) come segno di «fatto del
    mondo» contro «auto-dichiarazione»: sul banco separava 6/6 contro 0/6, sul
    corpus vero **68% contro 66%** — due punti, cioe' niente. Nel corpus reale
    anche le auto-dichiarazioni portano date e SHA, perche' le scrive chi
    lavora su software. L'ancoraggio e' un tratto dello STILE, non della natura
    del claim. Cura ritirata prima di scrivere il codice.

SHA-256, IL-6, COVID-19, HTTP/2 hanno la forma di un codice e non sono
identificativi di record: l'estrattore li prende, e non fanno danno lo stesso,
perche' si dichiara qualcosa SOLO se su quel codice esiste un fatto nascosto.
Misurato: zero falsi positivi su dieci enunciati di quel tipo.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any

#: Un CODICE DI RECORD: sigla, SEPARATORE, cifre. Il separatore e' cio' che lo
#: distingue da una sigla qualsiasi — vedi il docstring sopra per il numero che
#: ha imposto questa scelta.
_CODE_RE = re.compile(r"\b[A-Za-z]{1,8}[-_/]\d{1,6}(?:[-_/]\d{1,6})*\b")

#: Quanti fatti nascosti dichiarare per codice. Il campo serve a dire CHE C'E'
#: qualcosa, non a riversare la catena: un registro di duecento schede ne ha
#: centonovantanove dietro l'ultima, e servirle tutte sarebbe un'altra forma
#: dello stesso danno.
_PER_CODE = 3

#: SOPRA QUESTA SOGLIA IL CODICE NON E' UN IDENTIFICATIVO, E' UN'ETICHETTA.
#:
#: ⚠️ IL TAGLIO `_PER_CODE` NON BASTA, e il corpus vero lo ha dimostrato: limita
#: il VOLUME e non la PERTINENZA. Sui 977 fatti servibili che nominano un
#: codice, senza soglia la dichiarazione arrivava a 2491 nascosti per una sola
#: lettura, perche' `TURN-0` compare in 1471 fatti e `REPORT-2026-05-28` in
#: 1028. Quelli non identificano un record: identificano una categoria, e cio'
#: che uscirebbe e' rumore — due fatti su OMNEX dichiarati a chi legge di
#: `hippo_skills_for`, solo perche' entrambi contengono «TOP-5».
#:
#: La distribuzione e' una legge di potenza (63% dei codici in UN fatto, 3
#: codici sopra i cento): nessuna separazione da leggere, quindi la soglia si
#: sceglie e il prezzo si dichiara. Misurato sul corpus vero::
#:
#:     soglia   query col campo   mediana   massimo   >3 nascosti
#:    nessuna        318             3        2491        137
#:         10        121             2          14         19
#:          5         73             1           5          2
#:
#: A 10 il massimo crolla da 2491 a 14, e le 197 query che perdono la
#: dichiarazione la perdono per `TOP-5`, `TOP-3`, `SESSION_2026_05_12` — cioe'
#: esattamente il rumore. IL PREZZO: una scheda rimisurata piu' di dieci volte
#: non viene piu' dichiarata. E' il verso giusto in cui sbagliare.
#:
#: Costante ASSOLUTA e non frazione del corpus, di proposito: quanti fatti
#: nominano un record non cresce col corpus, cresce con quante volte QUEL
#: record e' stato aggiornato. E' una proprieta' del record.
_MAX_FACTS_PER_CODE = 10


def codes_in(text: str) -> set[str]:
    """I codici di record nominati da un testo, normalizzati a maiuscolo."""
    return {m.group(0).upper() for m in _CODE_RE.finditer(text or "")}


class SqliteRows:
    """L'adattatore verso il database vero: una SELECT mirata per codice.

    Il codice e' il termine di ricerca piu' selettivo che un registro
    possieda, e cercarlo costa un LIKE su una colonna. La scansione completa
    resta per i chiamanti che hanno gia' le righe in mano (i test)."""

    def __init__(self, db_path: Any) -> None:
        self.db_path = str(db_path)

    def rows_for_code(self, code: str) -> list[tuple]:
        con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            cur = con.execute(
                "SELECT id, status, superseded_by, proposition FROM facts "
                "WHERE UPPER(proposition) LIKE ? LIMIT 50",
                (f"%{code.upper()}%",))
            return list(cur.fetchall())
        finally:
            con.close()


def _rows_for(source: Any, code: str) -> list[tuple]:
    """Le righe candidate, da qualunque sorgente il chiamante abbia."""
    if hasattr(source, "rows_for_code"):
        return source.rows_for_code(code)
    if hasattr(source, "rows"):
        return [r for r in source.rows() if code in (r[3] or "").upper()]
    return []


def _why(status: str | None, superseded_by: str | None) -> str | None:
    """Perche' questo fatto non torna da un recall ordinario.

    ⚠️ I DUE MODI NON SONO UNO. `superseded_by IS NULL` non vuol dire «vivo»,
    vuol dire «non ritirato»: un quarantinato e' non-superseduto E invisibile.
    Contarne uno solo mi ha fatto annunciare una vittoria falsa il 2026-08-04
    (25 fatti «vivi» su 25, servibili 1)."""
    if superseded_by:
        return "retired"
    if (status or "") == "quarantined":
        return "quarantined"
    return None


def hidden_records_for(source: Any, *, query: str, served: str,
                       per_code: int = _PER_CODE) -> list[dict[str, str]]:
    """I fatti nascosti sui record che la DOMANDA nomina.

    Si parte dalla domanda e non dalla risposta: e' la domanda a dire di cosa
    si sta parlando, ed e' l'unico elemento che il percorso di scrittura non ha
    mai avuto sotto gli occhi.

    Ritorna una lista di ``{code, id, text, why}`` — vuota, e senza toccare il
    database, quando la domanda non nomina nessun codice. Sul corpus reale sono
    4356 fatti su 5333 a non contenerne uno: per la grande maggioranza delle
    letture questa funzione e' una `set()` vuota e un `return`."""
    codici = codes_in(query)
    if not codici:
        return []
    servito = (served or "").strip()
    out: list[dict[str, str]] = []
    for code in sorted(codici):
        righe = _rows_for(source, code)
        # LA SELETTIVITA' PRIMA DI TUTTO IL RESTO, e senza una query in piu':
        # la SELECT prende gia' fino a 50 righe, quindi contarle qui basta a
        # riconoscere un'etichetta e a scartarla. Vedi `_MAX_FACTS_PER_CODE`
        # per i numeri che hanno imposto questo taglio.
        if len(righe) > _MAX_FACTS_PER_CODE:
            continue
        presi = 0
        for rid, status, superseded_by, proposition in righe:
            testo = (proposition or "").strip()
            if not testo or testo == servito:
                continue
            if code not in testo.upper():
                continue
            motivo = _why(status, superseded_by)
            if motivo is None:
                continue
            out.append({"code": code, "id": rid, "text": testo, "why": motivo})
            presi += 1
            if presi >= per_code:
                break
    return out


__all__ = ["codes_in", "hidden_records_for", "SqliteRows"]
