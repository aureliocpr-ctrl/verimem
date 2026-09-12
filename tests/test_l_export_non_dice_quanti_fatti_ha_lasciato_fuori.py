"""`hippo_facts_export_all` promette «the entire fact corpus» e ne porta 10.000.

MISURATO ALLA PORTA il 2026-09-09, store temporaneo, nessun modello (il fatto
vero entra dalla porta, i restanti sono cloni scritti in SQL: qui si misura la
LETTURA, non la scrittura)::

    nello store              11 201 fatti vivi
    l'export ne porta            10 000
    la ricevuta dice         n_total: 10000      <- il numero dei portati,
                                                    col nome del totale

⇒ **Chi esporta la memoria per farne un backup ne riceve una parte e la
ricevuta non gliene dà notizia.** La promessa dello schema del tool
(`mcp_server.py:7167`) è testuale: *«Returns the entire fact corpus (or
filtered by topic) as JSON dicts ready for backup / migration»*. Il tetto sta
in `mcp_server.py:12060`, `list_facts(limit=10000, offset=0)`, e `list_facts`
ordina `created_at DESC`: **il taglio non è casuale, cade sui più VECCHI** —
in una memoria a lungo termine è la parte che l'utente non può riscrivere.

🔑 IL CAMPO CHE DOVREBBE DIRE IL TOTALE DICE I SERVITI. `facts_export.py:38`
scrive `"n_total": len(rows)`: chi legge la ricevuta vede un corpus di 10.000
fatti e non ha modo di sapere che ne esistono 11.201. Non è un numero
sbagliato — è il numeratore col nome del denominatore.

📌 STESSA FORMA GIÀ PAGATA, e la cura precedente sta due righe sopra il
difetto: il commento del 2026-07-30 in `facts_export.py:31-34` dice «un export
che lascia indietro metà del fatto è una perdita di dati silenziosa» e ha reso
INTERO ogni fatto esportato. Ha curato la larghezza; la profondità — quanti
fatti escono — è rimasta muta. È la lezione di
`test_la_porta_non_diceva_quale_pavimento_aveva_usato.py`: *far funzionare un
meccanismo e far dire alla porta cosa ha fatto sono due lavori diversi, e il
secondo non viene gratis col primo.*

⚠️ COSA QUESTA CURA NON FA, dichiarato: non alza il tetto e non cambia nessun
valore già presente nella ricevuta (`schema_version`, `n_total`, `facts`
restano quello che erano — l'ultimo test di questo file lo presidia). Aggiunge
i campi che rendono la perdita LEGGIBILE.

Ticket: piano di ripresa 09/09 §5 riga 2 (ws6). Ramo `aldo/tetto-e-supersede`.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid

import pytest

from verimem import mcp_server

#: Il tetto scritto nel codice del server (`mcp_server.py:12060`). Non è un
#: parametro: se cambia lì, questo banco deve fallire e non passare in silenzio.
TETTO = 10000

#: Quanti fatti stanno OLTRE il tetto in questo banco. Piccolo di proposito:
#: il difetto non ha bisogno di un corpus grande per mostrarsi, ha bisogno di
#: un corpus che superi il tetto anche di uno.
OLTRE = 1200

FATTO = "La penale del contratto Rossi e' 120 euro al giorno."


def _chiama(nome: str, args: dict) -> dict:
    return json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)


def _clona(db_path: str, quanti: int) -> None:
    """Scrive `quanti` fatti clonando la riga già presente.

    Si scrive in SQL e non dalla porta perché qui si misura la LETTURA: far
    passare 11.200 scritture dal gate misurerebbe il gate e costerebbe minuti.
    I cloni sono PIÙ RECENTI del fatto vero e stanno su un altro topic: è il
    traffico che arriva dopo, ed è ciò che spinge il fatto vero fuori dalla
    finestra. Così il banco può chiedersi anche che fine fa il suo topic.
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    riga = dict(con.execute("SELECT * FROM facts LIMIT 1").fetchone())
    cols = list(riga.keys())
    base = riga["created_at"]
    righe = []
    for i in range(quanti):
        r = dict(riga)
        r["id"] = uuid.uuid4().hex[:12]
        r["proposition"] = f"fatto clonato numero {i}"
        r["topic"] = "tetto/traffico"
        r["created_at"] = base + 1 + i
        righe.append(tuple(r[c] for c in cols))
    con.executemany(
        f"INSERT INTO facts ({','.join(cols)}) "
        f"VALUES ({','.join('?' * len(cols))})",
        righe,
    )
    con.commit()
    con.close()


def _apparecchia(tmp_path, monkeypatch, quanti: int):
    """Store isolato con `quanti` fatti in tutto. Rende (n_nello_store, db)."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    for alias in ("ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.delenv(alias, raising=False)
    # un fatto vero DALLA PORTA: fa nascere lo store e prova che il data dir
    # isolato è quello che il server usa davvero (i due DB, trappola nota)
    _chiama("hippo_remember", {"proposition": FATTO, "topic": "tetto/export"})
    sm = mcp_server._ag().semantic
    db = str(sm.db_path)
    if quanti > 1:
        _clona(db, quanti - 1)
    n = sm.count()
    # CONTROLLO POSITIVO: se lo store non contenesse davvero ciò che credo,
    # ogni asserzione qui sotto misurerebbe il vuoto e passerebbe lo stesso.
    assert n == quanti, f"lo store ha {n} fatti, ne volevo {quanti}"
    return n, db


@pytest.fixture
def oltre_il_tetto(tmp_path, monkeypatch):
    return _apparecchia(tmp_path, monkeypatch, TETTO + OLTRE + 1)


@pytest.fixture
def sotto_il_tetto(tmp_path, monkeypatch):
    return _apparecchia(tmp_path, monkeypatch, 12)


def test_la_ricevuta_dice_quanti_fatti_sono_rimasti_fuori(oltre_il_tetto):
    """IL CUORE: l'export dichiara il tetto che ha applicato.

    Tre cose che chi fa un backup deve poter leggere: quanti ne esistono,
    quanti ne ha in mano, e che c'è stato un taglio.
    """
    n_nello_store, _ = oltre_il_tetto
    d = _chiama("hippo_facts_export_all", {})

    assert d.get("capped") is True, sorted(d.keys())
    assert d.get("n_in_store") == n_nello_store, d.get("n_in_store")
    assert d.get("cap") == TETTO, d.get("cap")
    assert len(d["facts"]) == TETTO, len(d["facts"])


def test_il_taglio_cade_sui_piu_vecchi_e_la_ricevuta_lo_dice(oltre_il_tetto):
    """CHI cade, non solo quanti: `list_facts` ordina `created_at DESC`.

    In una memoria a lungo termine il taglio silenzioso sui più vecchi è il
    peggiore dei tagli: è la parte che l'utente non può riscrivere. Il banco
    prova che il fatto più vecchio NON esce, e che la ricevuta ammette il
    taglio invece di far sembrare quel fatto inesistente.
    """
    _, db = oltre_il_tetto
    con = sqlite3.connect(db)
    piu_vecchio = con.execute(
        "SELECT id FROM facts ORDER BY created_at ASC LIMIT 1").fetchone()[0]
    con.close()

    d = _chiama("hippo_facts_export_all", {})
    esportati = {f["id"] for f in d["facts"]}
    assert piu_vecchio not in esportati, "il banco non supera più il tetto"
    assert d.get("capped") is True, sorted(d.keys())


def test_l_export_di_un_topic_vecchio_non_torna_vuoto(oltre_il_tetto):
    """PERDITA TOTALE, non parziale — e su questa il tetto non basta dirlo.

    Il tetto si applica PRIMA del filtro per topic: `list_facts(limit=10000)`
    prende i 10.000 più recenti (`mcp_server.py:12060`) e solo dopo
    `export_all_facts` filtra per topic in Python (`facts_export.py:28`).
    Un topic scritto prima del traffico recente torna **vuoto**, e la ricevuta
    dice `n_total: 0` — indistinguibile da «quel topic non esiste».

    `list_facts` ha già il parametro `topic`: la cura è passarglielo.
    """
    d = _chiama("hippo_facts_export_all", {"topic": "tetto/export"})
    assert len(d["facts"]) == 1, (d["n_total"], "il topic vecchio è sparito")
    assert d["facts"][0]["proposition"] == FATTO, d["facts"][0]


def test_sotto_il_tetto_nessun_allarme(sotto_il_tetto):
    """⚠️ LA POPOLAZIONE OPPOSTA: se `capped` fosse sempre True, un export
    completo e uno tagliato tornerebbero indistinguibili — lo stesso difetto
    spostato di un passo."""
    n_nello_store, _ = sotto_il_tetto
    d = _chiama("hippo_facts_export_all", {})

    assert d.get("capped") is False, sorted(d.keys())
    assert d.get("n_in_store") == n_nello_store, d.get("n_in_store")
    assert len(d["facts"]) == n_nello_store, len(d["facts"])


def test_se_la_lettura_fallisce_la_ricevuta_lo_dice(sotto_il_tetto, monkeypatch):
    """R4 — L'ALTRO SILENZIO DELLA STESSA PORTA, e ha già fatto danno una volta.

    Il chiamante avvolge la lettura in `except Exception: pass` con `facts_all`
    inizializzato a `[]`: se `list_facts` solleva, l'export risponde `n_total:
    0, facts: []` — **indistinguibile da un corpus vuoto**. Non è un'ipotesi:
    è l'incidente del CYCLE #10, raccontato nel docstring di
    `SemanticMemory.list_facts` — il metodo non esisteva, ogni chiamata dava
    `AttributeError`, e 28 tool MCP hanno reso `facts=[]` in silenzio finché
    qualcuno non è andato a guardare.

    ⇒ Chi fa un backup deve poter distinguere «non hai fatti» da «non sono
    riuscito a leggerli». Il campo si chiama `scan_error` ed è `null` quando
    tutto è andato bene (la convenzione delle porte gemelle: `null` = niente
    da dichiarare, mai un valore inventato).

    📌 Lo stesso nome è proposto a @ws2 per i due ripieghi di
    `_fatti_per_il_recupero` (PR #17), così l'utente trova la stessa parola su
    ogni porta invece di una diversa per file.
    """
    def _esplode(*a, **k):
        raise RuntimeError("il database è chiuso")

    monkeypatch.setattr(mcp_server._ag().semantic, "list_facts", _esplode)
    d = _chiama("hippo_facts_export_all", {})

    assert d.get("scan_error"), sorted(d.keys())
    assert "RuntimeError" in d["scan_error"], d["scan_error"]
    assert d["facts"] == [], len(d["facts"])


def test_senza_errori_il_campo_e_null(sotto_il_tetto):
    """⚠️ LA POPOLAZIONE OPPOSTA: se `scan_error` portasse sempre una stringa,
    un export riuscito e uno fallito tornerebbero indistinguibili — lo stesso
    difetto spostato di un passo."""
    d = _chiama("hippo_facts_export_all", {})
    assert "scan_error" in d, sorted(d.keys())
    assert d["scan_error"] is None, d["scan_error"]


def test_i_campi_di_prima_sono_ancora_li(sotto_il_tetto):
    """La cura è ADDITIVA: chi legge oggi `n_total` o `facts` continua a
    leggerli, con lo stesso significato. `n_total` resta il numero delle righe
    esportate — nome infelice, ma cambiarlo romperebbe chi lo consuma."""
    d = _chiama("hippo_facts_export_all", {})
    for campo in ("schema_version", "n_total", "facts"):
        assert campo in d, sorted(d.keys())
    assert d["n_total"] == len(d["facts"]), (d["n_total"], len(d["facts"]))
