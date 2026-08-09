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


def names_code(text: str, code: str) -> bool:
    """Questo testo nomina QUESTO record — non uno che gli somiglia.

    ⚠️ SERVE IL CONFINE DI PAROLA, e la sottostringa non basta: «S-1» E'
    contenuto in «S-10» e in «S-100». Con il solo `in`, un registro numerato
    S-1...S-100 avrebbe trattato tre schede diverse come lo stesso record —
    che e' esattamente il difetto che questo modulo esiste per riparare, e
    l'avrei reintrodotto dal lato della cura.

    E' anche il verso in cui sbagliava il LIKE: `%ROUND-1%` prende «ROUND-10»
    (misurato: 15 differenze su 60 codici veri fra LIKE e FTS)."""
    if not text or not code:
        return False
    return re.search(rf"(?<![0-9A-Za-z]){re.escape(code)}(?![0-9A-Za-z])",
                     text, re.IGNORECASE) is not None


class SqliteRows:
    """L'adattatore verso il database vero: una SELECT mirata per codice.

    USA `facts_fts` QUANDO C'E', e c'era gia': indice FTS5 su `facts`,
    allineato (7810 = 7810) e mantenuto da tre trigger (insert/delete/update).
    Nessuno lo interrogava da qui. Misurato sul corpus vero, 7813 righe::

        tempo medio per codice     LIKE 127.06 ms     FTS 0.57 ms

    e la distanza cresce, perche' il LIKE e' una SCANSIONE: su un corpus
    sintetico da 500k righe stava a 594 ms mentre l'FTS restava a 0.38.
    Un prodotto che vuole reggere corpus grandi non puo' pagare mezzo secondo
    per codice a ogni lettura.

    ⚠️ LE DUE RICERCHE NON DANNO GLI STESSI CANDIDATI: su 60 codici veri, 45
    identici e 15 diversi. Le differenze vanno in due versi opposti, e uno dei
    due era un DIFETTO MIO:

      * il LIKE trova DI PIU' del dovuto perche' cerca sottostringhe:
        ``%ROUND-1%`` prende anche «ROUND-10». In un registro numerato
        S-1...S-100, cercare S-1 avrebbe restituito S-10, S-11, S-100.
      * l'FTS trova di piu' perche' ignora la punteggiatura: «OPUS-4-7»
        diventa la frase «opus 4 7» e prende «Opus 4.7» (7 -> 50 risultati).

    Entrambi gli eccessi muoiono nel filtro di `hidden_records_for`, che esige
    il codice ESATTO dentro il testo. Ecco perche' quel filtro deve girare
    PRIMA del conteggio per la soglia: contare i candidati grezzi userebbe il
    numero gonfiato dell'FTS e scarterebbe codici buoni.

    Il LIKE resta come ripiego quando `facts_fts` non c'e' (database vecchi,
    store minimali): stesso risultato, piu' lento."""

    _SQL_FTS = (
        "SELECT f.id, f.status, f.superseded_by, f.proposition "
        "FROM facts_fts JOIN facts f ON f.id = facts_fts.fact_id "
        "WHERE facts_fts MATCH ? LIMIT 50"
    )
    _SQL_LIKE = (
        "SELECT id, status, superseded_by, proposition FROM facts "
        "WHERE UPPER(proposition) LIKE ? LIMIT 50"
    )

    def __init__(self, db_path: Any) -> None:
        self.db_path = str(db_path)

    def rows_for_code(self, code: str) -> list[tuple]:
        con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            try:
                # La phrase query e' fra virgolette: senza, i token del codice
                # verrebbero cercati separati e «S-007» diventerebbe «s OR 007».
                return list(con.execute(self._SQL_FTS, (f'"{code}"',)))
            except sqlite3.OperationalError:
                # niente facts_fts (o sintassi FTS rifiutata): si ripiega.
                return list(con.execute(self._SQL_LIKE, (f"%{code.upper()}%",)))
        finally:
            con.close()


def _rows_for(source: Any, code: str) -> list[tuple]:
    """Le righe candidate, da qualunque sorgente il chiamante abbia.

    Recupero GREZZO e volutamente largo: ne' l'FTS ne' il LIKE danno i
    candidati esatti, e a stringere ci pensa `names_code` in
    `hidden_records_for`, dove il filtro gira PRIMA del conteggio."""
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
        # ⚠️ IL FILTRO PRIMA DEL CONTEGGIO, e l'ordine non e' un dettaglio.
        # Ne' l'FTS ne' il LIKE danno i candidati esatti: il primo ignora la
        # punteggiatura («OPUS-4-7» prende «Opus 4.7», 7 righe -> 50), il
        # secondo cerca sottostringhe («ROUND-1» prende «ROUND-10»). Contare i
        # candidati GREZZI userebbe quei numeri gonfiati e scarterebbe codici
        # buoni come se fossero etichette.
        righe = [r for r in _rows_for(source, code)
                 if names_code(r[3] or "", code)]
        # LA SELETTIVITA': sopra la soglia il codice non identifica un record.
        # Vedi `_MAX_FACTS_PER_CODE` per i numeri che l'hanno imposta.
        if len(righe) > _MAX_FACTS_PER_CODE:
            continue
        presi = 0
        for rid, status, superseded_by, proposition in righe:
            testo = (proposition or "").strip()
            if not testo or testo == servito:
                continue
            motivo = _why(status, superseded_by)
            if motivo is None:
                continue
            out.append({"code": code, "id": rid, "text": testo, "why": motivo})
            presi += 1
            if presi >= per_code:
                break
    return out


def withheld_notice(hits: list[dict[str, Any]]) -> str:
    """La riga che dice a chi risponde: su questo record c'e' dell'altro.

    ⚠️ NON PASSA IL TESTO DEL FATTO NASCOSTO, e la scelta e' di merito. Un
    quarantinato e' stato filtrato in scrittura apposta: darlo in pasto a chi
    formula la risposta lo servirebbe come evidenza e tradirebbe la garanzia
    che questo prodotto vende. Passano solo il CODICE, il NUMERO e il PERCHE'.

    Il valore non e' servire il contenuto trattenuto — e' togliere la
    CONFIDENZA a una risposta sbagliata. Senza questa riga il prodotto
    risponde «il ticket e' aperto» a 0.8819 mentre l'aggiornamento che dice il
    contrario sta in quarantena, e chi legge non ha modo di sospettarlo.

    Stringa VUOTA quando non c'e' niente da dichiarare: il prompt resta
    byte-identico a prima, che e' il caso della grande maggioranza delle
    letture (4356 fatti su 5333 non contengono nemmeno un codice)."""
    conteggio: dict[str, dict[str, int]] = {}
    for h in hits or ():
        for n in h.get("hidden_records") or ():
            per_code = conteggio.setdefault(n["code"], {})
            per_code[n["why"]] = per_code.get(n["why"], 0) + 1
    if not conteggio:
        return ""
    pezzi = []
    for code in sorted(conteggio):
        dettaglio = ", ".join(f"{n} {why}"
                              for why, n in sorted(conteggio[code].items()))
        pezzi.append(f"{code}: {dettaglio}")
    return ("\n\nWITHHELD — the store holds facts about these records that are "
            "NOT in the list above (" + " · ".join(pezzi) + "). Do not answer "
            "with certainty about them; say what is uncertain.")


__all__ = ["codes_in", "names_code", "hidden_records_for",
           "withheld_notice", "SqliteRows"]
