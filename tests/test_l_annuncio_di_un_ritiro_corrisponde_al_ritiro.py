"""L'INVARIANTE, dopo che lo stesso difetto è tornato TRE volte.

`anti_confab_gate.py` documenta due volte, di se stesso, che l'avviso
`L3-supersession` ha annunciato un ritiro mai avvenuto — la seconda volta
scrivendo «SECONDA VOLTA CHE QUESTO MESSAGGIO DICHIARA UNA COSA CHE NON È
AVVENUTA». Il 21/08 è successo una terza volta: la guardia [C] entrata in
`aeee8305` fa quello che promette — il vecchio resta vivo e il nuovo viene
quarantinato — ma l'avviso continua a dire «the older value is superseded», cioè
l'esatto contrario (misurato da ws5 con un A/B su due SHA, 10:35).

PERCHÉ IL PRESIDIO CHE C'ERA NON L'HA PRESO, che è il punto di questo file.
`test_il_gate_annunciava_un_ritiro_mai_avvenuto.py:47` inchioda la SECONDA
occorrenza sulla sua CAUSA::

    Memory(db, principal="anna").add(...)
    ric = Memory(db, principal="bruno").add(...)      # <-- due autori
    assert "L3-supersession" not in layers

Verifica «con due autori non si annuncia un ritiro». La terza occorrenza ha **un
autore solo** e una causa diversa, quindi gli passa accanto senza sfiorarlo. Un
presidio scritto sul caso copre il caso; ogni causa nuova che produce lo stesso
sintomo entra libera, e la quarta volta arriva.

QUI SI INCHIODA IL LEGAME, NON LA CAUSA — nei due versi:

    l'avviso dice «superseduto»   ⟺   esiste un fatto con superseded_by non-None

Il verso «se avviene, si annuncia» esiste già
(`test_una_supersessione_VERA_si_annuncia_ancora`) e non lo duplico: quello che
manca è l'altro verso, applicato a scenari con cause DIVERSE. Se domani una
quinta strada rompe il legame, questo diventa rosso senza che nessuno debba
prima indovinare quale sia.

⚠️ REGIME: gli scenari usano la rotta LESSICALE numerica — stesso `verified_by`,
cambia solo il numero — perché sotto pytest l'embedder è uno stub su SHA-256
(`conftest`) e la rotta semantica non riconosce più i due fatti come
contraddittori: misurato, fuori da pytest 1 supersessione, sotto pytest 0. Un
presidio su quella rotta passerebbe anche a difetto presente. È la stessa scelta,
e per la stessa ragione, del presidio della guardia [C].
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

FONTE = ["source-doc:magazzino:1"]


def _layers(ricevuta) -> list[str]:
    return [str(w.get("layer")) for w in (ricevuta.get("warnings") or [])]


def _annuncia_un_ritiro(ricevuta) -> bool:
    """L'avviso afferma che il vecchio è stato superseduto?

    Guarda il layer E il testo: il layer da solo cambierebbe significato se
    domani l'avviso venisse rinominato, e la promessa che stiamo presidiando
    sta nella FRASE che l'utente legge.
    """
    for w in (ricevuta.get("warnings") or []):
        if str(w.get("layer")) == "L3-supersession":
            return True
        if "superseded" in str(w.get("reason", "")).lower():
            return True
    return False


def _qualcuno_e_stato_ritirato(db: Path) -> bool:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        riga = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()
        return bool(riga and riga[0])
    finally:
        conn.close()


# --- gli scenari: cause DIVERSE, stesso invariante ------------------------

def _scenario_due_autori(db: Path, monkeypatch) -> dict:
    """SECONDA occorrenza: due principal diversi, i fatti coesistono."""
    Memory(str(db), principal="anna").add(
        "Il magazzino K-77 di Rovigo ha 4200 metri quadrati.", topic="az/mag")
    return Memory(str(db), principal="bruno").add(
        "Il magazzino Z-08 di Ancona ha 2600 metri quadrati.", topic="az/mag")


def _scenario_guardia_C(db: Path, monkeypatch) -> dict:
    """TERZA occorrenza: un autore solo, ma il nuovo è SENZA source e la
    guardia [C] (`aeee8305`) impedisce il ritiro."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = Memory(str(db))
    testo = "The subscription costs 100 euros per month."
    mem.add(testo, topic="pricing/plan", verified_by=FONTE, source=testo,
            validate="full")
    return mem.add("The subscription costs 150 euros per month.",
                   topic="pricing/plan", verified_by=FONTE, validate="full")


def _scenario_ritiro_vero(db: Path, monkeypatch) -> dict:
    """IL CONTROLLO: un ritiro che avviene davvero. Serve a distinguere «il
    legame regge» da «non si annuncia mai niente», che passerebbe l'invariante
    a costo di rendere il prodotto muto."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = Memory(str(db))
    t1 = "The subscription costs 100 euros per month."
    t2 = "The subscription costs 150 euros per month."
    mem.add(t1, topic="pricing/plan", verified_by=FONTE, source=t1, validate="full")
    return mem.add(t2, topic="pricing/plan", verified_by=FONTE, source=t2,
                   validate="full")


@pytest.mark.parametrize("scenario", [
    _scenario_due_autori,
    _scenario_guardia_C,
    _scenario_ritiro_vero,
], ids=["due-autori", "guardia-C", "ritiro-vero"])
def test_se_l_avviso_annuncia_un_ritiro_allora_il_ritiro_e_avvenuto(scenario,
                                                                    monkeypatch):
    """L'INVARIANTE, indipendente dalla causa.

    Non chiede «questo scenario deve/non deve superseder»: chiede che l'avviso
    e il fatto **dicano la stessa cosa**, qualunque cosa sia. Uno scenario che
    domani cambiasse comportamento resterebbe verde finché il messaggio lo
    segue, ed è esattamente ciò che vogliamo presidiare.
    """
    db = Path(tempfile.mkdtemp()) / "inv.db"
    ricevuta = scenario(db, monkeypatch)

    annunciato = _annuncia_un_ritiro(ricevuta)
    avvenuto = _qualcuno_e_stato_ritirato(db)

    assert annunciato == avvenuto, (
        f"l'avviso e il fatto si contraddicono: annunciato={annunciato}, "
        f"avvenuto={avvenuto}. Warning: {_layers(ricevuta)}. "
        f"Un annuncio che non corrisponde al fatto è la classe di difetto che "
        f"questo gate esiste per fermare — ed è la terza volta su questo "
        f"stesso messaggio.")


def test_il_controllo_non_e_soddisfatto_dal_silenzio(monkeypatch):
    """L'invariante da solo si accontenterebbe di un prodotto MUTO: nessun
    avviso mai, nessuna contraddizione mai. Questo lo impedisce — su un ritiro
    vero l'annuncio deve esserci davvero, non solo «non mentire»."""
    db = Path(tempfile.mkdtemp()) / "muto.db"
    ricevuta = _scenario_ritiro_vero(db, monkeypatch)
    assert _qualcuno_e_stato_ritirato(db), (
        "lo scenario di controllo non ritira più nulla: non sta più "
        "controllando ciò per cui è stato scritto")
    assert _annuncia_un_ritiro(ricevuta), (
        f"un ritiro è avvenuto e non viene annunciato: {_layers(ricevuta)}")
