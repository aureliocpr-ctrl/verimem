"""In una memoria di team il fatto di Bruno archiviava quello di Anna.

TROVATO DA ws5 sul multi-utente — l'ultima area vergine — e riprodotto qui in
indipendenza. Due colleghi sulla stessa memoria aziendale, due magazzini
diversi::

    anna  = Memory(principal="anna");   anna.add("Il magazzino K-77 ... 4200 mq")
    bruno = Memory(principal="bruno");  bruno.add("Il magazzino Z-08 ... 2600 mq")

    ARCHIVIATO [anna ] Il magazzino K-77 di Rovigo ha 4200 metri quadrati.
    vivo       [bruno] Il magazzino Z-08 di Ancona ha 2600 metri quadrati.
    vivi: 1 su 2

Anna interroga la memoria sul PROPRIO magazzino e riceve quello di un collega.
Il suo lavoro non e' soltanto perso: e' SOSTITUITO da quello di qualcun altro,
senza un avviso a nessuno dei due.

La colonna `writer_principal` ESISTE, e' popolata correttamente ('anna' su un
fatto, 'bruno' sull'altro), e il percorso che decide i ritiri non la
consultava: `canonical_source_of` leggeva SOLO `verified_by`. E' la nona volta
in una notte che troviamo «il meccanismo c'e', il chiamante non lo alimenta».

⚠️ PERCHE' LA CURA INGENUA CADE, e il corpus vero lo dice::

    fatti 7852 · principal distinti 4
       6253  <NULL>        1454  cli:local
        143  mcp:unbound      2  sdk:local

IL CAMPO CONTIENE DUE COSE DIVERSE: nel banco una PERSONA, nel corpus reale un
CANALE. Guardarlo cosi' com'e' renderebbe «due autori» la stessa persona che
scrive da CLI e aggiorna da MCP — che e' il presidio su cui e' caduta la cura
della `source_signature` il 2026-08-04.

⇒ DUE AUTORI SONO DIVERSI SOLO SE ENTRAMBI DICHIARANO UN'IDENTITA' NON ANONIMA.
Conseguenza voluta: sul corpus di casa la cura e' INERTE (i quattro principal
sono tutti anonimi) e morde solo dove un'identita' c'e' davvero.

⚠️ E L'INNESTO STA IN `is_same_source`, NON in `canonical_source_of`:
quest'ultima vede UN fatto solo e non puo' sapere se l'ALTRO ha dichiarato
un'identita' — servirebbe per il caso «uno dichiara, l'altro no», dove non si
sa nulla e il comportamento deve restare quello di prima.
"""
from __future__ import annotations

import pytest

from verimem.supersession_policy import (
    classify_write_relation,
    declared_identity,
    is_same_source,
)


class _F:
    def __init__(self, prop, t, *, principal=None, verified_by=None):
        self.proposition = prop
        self.created_at = t
        self.asserted_at = None
        self.verified_by = verified_by or []
        self.source_signature = None
        self.writer_principal = principal


def test_due_persone_diverse_non_si_archiviano():
    """IL CUORE: e' la coppia che, in una memoria di team, fa sparire il lavoro
    di un collega senza avvisare nessuno dei due."""
    anna = _F("Il magazzino K-77 di Rovigo ha 4200 metri quadrati.", 100.0,
              principal="anna")
    bruno = _F("Il magazzino Z-08 di Ancona ha 2600 metri quadrati.", 200.0,
               principal="bruno")
    assert not is_same_source(bruno, anna)
    assert classify_write_relation(bruno, anna) == "conflict"


def test_la_stessa_persona_aggiorna_il_proprio_fatto():
    """IL PRESIDIO PRINCIPALE. Se anna corregge il proprio dato, il secondo
    aggiorna il primo: e' il mestiere di una memoria. Una che non ritira piu'
    nulla e' rotta quanto una che ritira tutto."""
    vecchio = _F("Il magazzino K-77 di Rovigo ha 4200 metri quadrati.", 100.0,
                 principal="anna")
    nuovo = _F("Il magazzino K-77 di Rovigo ha 5100 metri quadrati.", 200.0,
               principal="anna")
    assert is_same_source(nuovo, vecchio)
    assert classify_write_relation(nuovo, vecchio) == "evolution"


@pytest.mark.parametrize("a,b", [
    ("cli:local", "mcp:unbound"),
    ("sdk:local", "cli:local"),
    ("mcp:unbound", "mcp:unbound"),
])
def test_i_canali_anonimi_non_sono_identita(a, b):
    """IL PRESIDIO CHE PROTEGGE IL CORPUS ESISTENTE: i quattro principal del
    corpus vero sono TUTTI anonimi, quindi li' la cura non cambia una virgola.
    Se questi diventassero «autori diversi», la stessa persona che scrive da
    due canali smetterebbe di poter aggiornare i propri fatti."""
    vecchio = _F("Il server alfa ha 64 gigabyte di memoria.", 100.0, principal=a)
    nuovo = _F("Il server alfa ha 128 gigabyte di memoria.", 200.0, principal=b)
    assert is_same_source(nuovo, vecchio)
    assert classify_write_relation(nuovo, vecchio) == "evolution"


@pytest.mark.parametrize("altro", ["sdk:local", None, "", "cli:local"])
def test_se_uno_solo_dichiara_non_si_sa_nulla(altro):
    """L'ALTRO PRESIDIO: con un'identita' su un lato solo non si puo' concludere
    che siano due persone diverse, quindi il comportamento resta quello di
    prima. E' lo stesso principio del codice-su-un-lato-solo."""
    vecchio = _F("Il deposito Q-11 di Lecce ha 900 metri quadrati.", 100.0,
                 principal="anna")
    nuovo = _F("Il deposito Q-11 di Lecce ha 1200 metri quadrati.", 200.0,
               principal=altro)
    assert is_same_source(nuovo, vecchio)


def test_stesso_documento_ma_due_persone_resta_un_conflitto():
    """SCRITTO PRIMA CON L'ASPETTATIVA OPPOSTA, e il codice aveva ragione.

    Avevo assunto che dove c'e' `verified_by` decidesse solo lui. Ma due
    persone diverse che citano LO STESSO bilancio e scrivono numeri diversi
    sono una CONTRADDIZIONE, non un aggiornamento: non e' la stessa mano che
    corregge il proprio dato.

    E nel dubbio conta quale errore costa meno:
      * non ritirare -> resta un dato vecchio accanto al nuovo, visibile, e
        `hidden_records` lo dichiara a chi fa la domanda;
      * ritirare     -> il lavoro di anna sparisce senza avviso a nessuno.
    La perdita e' il danno peggiore, ed e' la lezione di tutta questa notte.

    ⚠️ Impatto sul corpus esistente: ZERO. Serve che ENTRAMBI dichiarino
    un'identita', e i quattro principal del corpus vero sono tutti anonimi."""
    a = _F("Il tasso e' al 3 per cento.", 100.0,
           principal="anna", verified_by=["doc:bilancio"])
    b = _F("Il tasso e' al 4 per cento.", 200.0,
           principal="bruno", verified_by=["doc:bilancio"])
    assert not is_same_source(b, a)


def test_la_stessa_persona_che_cita_lo_stesso_documento_aggiorna():
    """Il presidio dell'altro verso: la stessa mano, la stessa fonte, un
    valore nuovo -> aggiorna, come deve."""
    a = _F("Il tasso e' al 3 per cento.", 100.0,
           principal="anna", verified_by=["doc:bilancio"])
    b = _F("Il tasso e' al 4 per cento.", 200.0,
           principal="anna", verified_by=["doc:bilancio"])
    assert is_same_source(b, a)
    assert classify_write_relation(b, a) == "evolution"


def _vivi(db):
    import sqlite3
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rr = con.execute("SELECT status,superseded_by,writer_principal,proposition "
                     "FROM facts").fetchall()
    # ⚠️ SERVIBILI, non «non superseduti»: un quarantinato e' non-superseduto E
    # invisibile. Contare solo `superseded_by IS NULL` qui avrebbe detto «2 su
    # 2» mentre uno dei due era in quarantena — l'errore che il 04/08 e' costato
    # tre ore e un annuncio falso.
    return [r for r in rr if r["superseded_by"] is None
            and (r["status"] or "") != "quarantined"], rr


@pytest.mark.parametrize("pa,pb,attesi", [
    ("anna", "bruno", 2),      # due persone: devono convivere
    ("anna", "anna", 1),       # la stessa persona aggiorna: ritira
    ("cli:local", "mcp:unbound", 1),   # canali anonimi: invariato
    ("anna", "sdk:local", 1),  # uno solo dichiara: invariato
])
def test_END_TO_END_sul_prodotto_vero(tmp_path, pa, pb, attesi):
    """LA MISURA CHE CONTA, e le altre non bastavano.

    Con `is_same_source` gia' corretta e venti test verdi su questa pagina, il
    prodotto continuava a perdere un fatto: il candidato del confronto non
    portava `writer_principal`, quindi il cancello leggeva sempre `None`. E
    curato UN percorso su due, la perdita si spostava soltanto — da «anna
    ritirata» a «bruno quarantinato».

    Un difetto di funzione e' un'ipotesi finche' non e' girato end-to-end."""
    from verimem.client import Memory

    db = tmp_path / "team.db"
    Memory(str(db), principal=pa).add(
        "Il magazzino K-77 di Rovigo ha 4200 metri quadrati.", topic="az/mag")
    Memory(str(db), principal=pb).add(
        "Il magazzino Z-08 di Ancona ha 2600 metri quadrati."
        if pa != pb else
        "Il magazzino K-77 di Rovigo ha 5100 metri quadrati.", topic="az/mag")
    vivi, tutti = _vivi(db)
    assert len(vivi) == attesi, (
        f"{pa}/{pb}: attesi {attesi} servibili, trovati {len(vivi)} su "
        f"{len(tutti)} — " + " · ".join(
            f"[{r['status']}|{r['writer_principal']}] {r['proposition'][:30]}"
            for r in tutti))


@pytest.mark.parametrize("valore,atteso", [
    ("anna", "anna"),
    ("Anna", "anna"),
    ("  anna  ", "anna"),
    ("mcp:alice", "mcp:alice"),
    ("cli:local", None),
    ("mcp:unbound", None),
    ("sdk:local", None),
    ("", None),
    (None, None),
])
def test_quali_valori_sono_una_identita(valore, atteso):
    assert declared_identity(valore) == atteso
