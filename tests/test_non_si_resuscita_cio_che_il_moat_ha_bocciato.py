"""Lo strumento di recupero riportava nel recall i bocciati dal moat.

Convergenza di quattro istanze in venti minuti, 2026-08-07:

- **ws4** legge il codice: le tre condizioni di `requalify_quarantined`
  sono L1, injection e admission gate — **L3 e L4 non ci sono**;
- **ws1**: 9 dei suoi 10 quarantinati sono fermati proprio da L4.x;
- **ws5** ritira la raccomandazione che aveva portato per prima;
- **io** avevo scritto in `GOVERNANCE.md` che lo strumento «ha tre
  condizioni di sicurezza», ripetendo la parola `SAFE` del docstring.

Poi ws4 ha fatto il test decisivo, e non serviva il giudice perché **il
verdetto di L4 è già persistito in `grounding_score`**:

    dei 172 recuperabili dalle tre condizioni
      138 hanno gs sotto 40
       17 fra 40 e 70
      ⇒ 155 su 172 = 90,1% erano stati BOCCIATI DAL MOAT

⇒ Lo strumento nato per recuperare i **falsi positivi già curati**
riportava nel recall, nove volte su dieci, fatti che il giudice del
prodotto aveva respinto — «la fonte non lo sostiene».

La cura è la riga che ws4 ha scritto: `grounding_score IS NULL OR
grounding_score >= 70`.

⚠️ Due scelte, entrambe di ws4 e entrambe conservative, che verifico qui:
- **i NULL restano dentro**: «mai giudicato» non è «bocciato», ed è la
  distinzione che questo ramo difende da due giorni;
- **la soglia è 70 e non 40**: la cut di ammissione non è una (misurato
  il 2026-08-05: 40 con il giudice di ripiego, 70 con quello calibrato),
  e prendere la più ALTA significa recuperare di meno — che davanti a un
  dubbio è il verso giusto.

Non è un cambio di politica: lo scopo dichiarato dello strumento è
recuperare «real knowledge that a SINCE-FIXED false positive had hidden».
Un fatto che il moat boccia OGGI non è un falso positivo già curato.
"""
from __future__ import annotations

import pathlib
import sqlite3

import pytest

from verimem.admission_cleanup import requalify_quarantined
from verimem.client import Memory


@pytest.fixture()
def store(tmp_path):
    return Memory(tmp_path / "m.db")


def _quarantina(m: Memory, testo: str, *, gs: float | None) -> str:
    fid = m.add(testo, topic="misure")["id"]
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET status = 'quarantined', "
                    "grounding_score = ? WHERE id = ?", (gs, fid))
    return fid


def _esito(m: Memory) -> dict:
    return requalify_quarantined(
        pathlib.Path(m.semantic.db_path), dry_run=True)


def test_un_bocciato_dal_moat_NON_e_piu_recuperabile(store):
    """Il caso dei 138: gs 3.2 significa che il giudice ha guardato la
    fonte e ha detto di no."""
    _quarantina(store, "the depot in Turin holds 40 crates", gs=3.2)
    assert _esito(store)["recoverable"] == 0


def test_la_BANDA_CONTESA_resta_fuori_perche_la_soglia_e_quella_alta(store):
    """Fra 40 e 70 il destino dipendeva da quale giudice era su. Davanti a
    un dubbio si recupera di meno."""
    _quarantina(store, "the depot in Turin holds 40 crates", gs=55.0)
    assert _esito(store)["recoverable"] == 0


def test_un_MAI_GIUDICATO_resta_recuperabile(store):
    """«Mai giudicato» non è «bocciato»: questi sono esattamente i falsi
    positivi che lo strumento esiste per recuperare."""
    _quarantina(store, "the depot in Turin holds 40 crates", gs=None)
    assert _esito(store)["recoverable"] == 1


def test_un_APPROVATO_dal_moat_resta_recuperabile(store):
    """Il moat dice che la fonte lo sostiene e L1 non scatta più: è il caso
    più chiaro di falso positivo curato."""
    _quarantina(store, "the depot in Turin holds 40 crates", gs=97.0)
    assert _esito(store)["recoverable"] == 1


def test_l_esito_DICHIARA_quanti_ne_ha_esclusi_per_il_verdetto(store):
    """Un conteggio che cala senza spiegazione si legge come «ce n'erano
    meno»: chi guarda deve vedere che la differenza è una scelta."""
    _quarantina(store, "the depot in Turin holds 40 crates", gs=3.2)
    _quarantina(store, "the yard in Milan holds 12 pallets", gs=None)

    out = _esito(store)
    assert out["recoverable"] == 1
    assert out["held_by_moat"] == 1, out
    assert "70" in out["moat_rule"], out


def test_il_dry_run_resta_il_default(store):
    """L'unica ragione per cui questo strumento non ha già fatto danno."""
    fid = _quarantina(store, "the depot in Turin holds 40 crates", gs=None)
    requalify_quarantined(pathlib.Path(store.semantic.db_path))
    with sqlite3.connect(store.semantic.db_path) as con:
        assert con.execute("SELECT status FROM facts WHERE id = ?",
                           (fid,)).fetchone()[0] == "quarantined"
