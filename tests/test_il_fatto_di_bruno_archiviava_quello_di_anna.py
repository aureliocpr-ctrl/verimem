"""Due record distinti non si archiviano a vicenda — e l'AUTORE non c'entra.

STORIA, perche' e' la parte utile e sta in due mosse.

**Mossa 1 (ws5, multi-utente).** Due colleghi sulla stessa memoria aziendale,
due magazzini DIVERSI::

    ARCHIVIATO [anna ] Il magazzino K-77 di Rovigo ha 4200 metri quadrati.
    vivo       [bruno] Il magazzino Z-08 di Ancona ha 2600 metri quadrati.

Anna chiede del PROPRIO magazzino e riceve quello di un collega. Cura scritta:
due `writer_principal` dichiarati e diversi non si ritirano a vicenda.

**Mossa 2 (ws5 di nuovo, tre ore dopo): quella cura era l'asse SBAGLIATO.**
La matrice completa, che il mio banco non aveva::

    caso                        vivi  atteso  con l'asse AUTORE
    un autore,  due entita'       1      2    x  il buco storico, non chiuso
    due autori, due entita'       2      2    ok
    un autore,  aggiornamento     1      1    ok
    due autori, aggiornamento     2      1    REGRESSIONE

anna scrive «Il paziente Rossi pesa 70 chilogrammi», bruno corregge «78», e
restavano vivi entrambi: **la correzione di un collega smetteva di sovrascrivere
il dato sbagliato**. E togliendo l'asse dal solo gate, senza toglierlo da
`supersession_policy`, il risultato peggiorava ancora — la correzione finiva in
QUARANTENA e restava servito il valore vecchio.

🔑 «Autori diversi» non implica «cose diverse». Due persone che parlano dello
STESSO paziente parlano della stessa cosa. L'asse che conta e' L'ENTITA', e
l'autore ne era un proxy debole: `anti_confab_gate._entita_diverse` confronta i
CODICI DI RECORD e copre anche il caso anna/bruno per cui la cura era nata.

⚠️ E SO PERCHE' IL CRITERIO DEL CODICE REGGE OGGI, mentre il 2026-08-04 era
stato scritto, misurato e RITIRATO: allora l'unica alternativa a `evolution`
era `conflict`, cioe' la QUARANTENA, e la perdita cambiava solo nome. Oggi c'e'
la terza uscita — coesistenza — che allora non esisteva.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.anti_confab_gate import _entita_diverse
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


# ---------------------------------------------------------------- l'asse vero

@pytest.mark.parametrize("a,b,diverse", [
    ("Il magazzino K-77 di Rovigo ha 4200 metri quadrati.",
     "Il magazzino Z-08 di Ancona ha 2600 metri quadrati.", True),
    ("Il paziente P-9 pesa 70 chilogrammi.",
     "Il paziente P-9 pesa 78 chilogrammi.", False),
    # un codice su un lato solo: non si sa nulla
    ("Il magazzino K-77 ha 4200 metri quadrati.",
     "Il magazzino di Ancona ha 2600 metri quadrati.", False),
    # nessun codice — ERA il buco storico (la cella 6), e dal 2026-08-05 è
    # CHIUSO: non dai codici ma dalle ENTITÀ del grafo. `extract_entities_lite`
    # estrae «Rossi» e «Bianchi» come due `proper` separati, nello stesso
    # `add()` che archivia il fatto. La riga qui sotto diceva `False` con la
    # nota «questo criterio NON chiude»: il criterio è cresciuto.
    ("Il paziente Rossi pesa 70 chilogrammi.",
     "Il paziente Bianchi pesa 95 chilogrammi.", True),
    # e il verso opposto resta il presidio: STESSA entità, valore nuovo
    ("Il paziente Rossi pesa 70 chilogrammi.",
     "Il paziente Rossi pesa 78 chilogrammi.", False),
])
def test_l_asse_e_l_entita_non_l_autore(a, b, diverse):
    assert _entita_diverse(_F(b, 200.0), _F(a, 100.0)) is diverse


def test_l_autore_NON_decide_piu():
    """⛔ IL PRESIDIO DEL RITIRO. Se questo torna a fallire, qualcuno ha
    rimesso l'asse dell'autore in `is_same_source` e la correzione di un
    collega ha smesso di sovrascrivere il dato sbagliato."""
    anna = _F("Il paziente Rossi pesa 70 chilogrammi.", 100.0, principal="anna")
    bruno = _F("Il paziente Rossi pesa 78 chilogrammi.", 200.0, principal="bruno")
    assert is_same_source(bruno, anna), (
        "l'identita' di chi scrive non deve decidere un ritiro")
    assert classify_write_relation(bruno, anna) == "evolution"


def test_declared_identity_resta_ed_e_corretta():
    """La funzione non e' stata cancellata: distinguere un CANALE da una
    PERSONA serve a chi MOSTRA la provenienza. Non serve a decidere un ritiro."""
    assert declared_identity("anna") == "anna"
    assert declared_identity("Anna") == "anna"
    assert declared_identity("mcp:alice") == "mcp:alice"
    for anonimo in ("cli:local", "mcp:unbound", "sdk:local", "", None):
        assert declared_identity(anonimo) is None


# ------------------------------------------------------------------ il banco

def _servibili(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rr = con.execute("SELECT status,superseded_by,writer_principal,proposition "
                     "FROM facts").fetchall()
    # ⚠️ SERVIBILI, non «non superseduti»: un quarantinato e' non-superseduto E
    # invisibile. E il conteggio da solo non basta — vedi il test qui sotto.
    return [r for r in rr if r["superseded_by"] is None
            and (r["status"] or "") != "quarantined"], rr


@pytest.mark.parametrize("pa,pb,a,b,attesi", [
    # due record DISTINTI: convivono, chiunque li abbia scritti
    (None, None,
     "Il magazzino K-77 di Rovigo ha 4200 metri quadrati.",
     "Il magazzino Z-08 di Ancona ha 2600 metri quadrati.", 2),
    ("anna", "bruno",
     "Il magazzino K-77 di Rovigo ha 4200 metri quadrati.",
     "Il magazzino Z-08 di Ancona ha 2600 metri quadrati.", 2),
    # LO STESSO record che cambia valore: ritira, chiunque lo aggiorni
    (None, None,
     "Il magazzino K-77 di Rovigo ha 4200 metri quadrati.",
     "Il magazzino K-77 di Rovigo ha 5100 metri quadrati.", 1),
    ("anna", "bruno",
     "Il paziente P-9 pesa 70 chilogrammi.",
     "Il paziente P-9 pesa 78 chilogrammi.", 1),
])
def test_END_TO_END_sul_prodotto_vero(tmp_path, pa, pb, a, b, attesi):
    """LA MISURA CHE CONTA. Con `is_same_source` corretta e venti test verdi
    sulla funzione, il prodotto continuava a perdere un fatto: un difetto di
    funzione e' un'ipotesi finche' non e' girato end-to-end."""
    from verimem.client import Memory

    db = tmp_path / "team.db"
    Memory(str(db), principal=pa).add(a, topic="az/x")
    Memory(str(db), principal=pb).add(b, topic="az/x")
    vivi, tutti = _servibili(db)
    assert len(vivi) == attesi, (
        f"{pa}/{pb}: attesi {attesi} servibili, trovati {len(vivi)} — " +
        " · ".join(f"[{r['status']}|{r['writer_principal']}] "
                   f"{r['proposition'][:30]}" for r in tutti))


def test_la_correzione_di_un_collega_SOSTITUISCE_il_dato_sbagliato(tmp_path):
    """⚠️ IL CONTEGGIO NON BASTA, e qui e' dove mi ha ingannata.

    Con l'asse autore tolto dal solo gate, «due autori, aggiornamento» dava
    `1 vivo, atteso 1` — verde — e il fatto vivo era QUELLO SBAGLIATO::

        VIVO        [model_claim] anna   «Rossi pesa 70 kg»   <- il vecchio
        non servito [quarantined] bruno  «Rossi pesa 78 kg»   <- la correzione

    Un test che conta i sopravvissuti e non guarda CHI sopravvive lascia
    passare l'esatto contrario di quello che voleva presidiare."""
    from verimem.client import Memory

    db = tmp_path / "corr.db"
    Memory(str(db), principal="anna").add(
        "Il paziente Rossi pesa 70 chilogrammi.", topic="az/p")
    Memory(str(db), principal="bruno").add(
        "Il paziente Rossi pesa 78 chilogrammi.", topic="az/p")
    vivi, tutti = _servibili(db)
    assert len(vivi) == 1, [r["proposition"] for r in tutti]
    assert "78" in vivi[0]["proposition"], (
        "sopravvive il valore VECCHIO: la correzione non ha sostituito nulla")
