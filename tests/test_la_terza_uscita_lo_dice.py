"""Chi esce dalla terza uscita non lo faceva sapere a nessuno.

Il gate ha tre esiti per una scrittura che somiglia a una precedente: ritirare
la vecchia, quarantenare la nuova, o tenerle ENTRAMBE. La terza — la
coesistenza — e' quella giusta quando i due fatti parlano di cose diverse, e
`_entita_diverse` la sceglie facendo `continue`.

⚠️ QUESTO BANCO NASCE DA UNA MIA DIAGNOSI SBAGLIATA, ed e' verde dal primo
giro. Avevo concluso — leggendo il codice e non eseguendolo — che il `continue`
di `_entita_diverse` uscisse PRIMA del ramo `L3-coexistence`, lasciando la
ricevuta muta. Eseguito: il gate emette l'avviso, e il caso di ws6 coesiste
dichiarandolo.

Il presidio resta perche' pin-a un comportamento che nessun test copriva: la
terza uscita e' l'unica delle tre che non cambia lo stato di niente, quindi e'
anche l'unica che puo' diventare silenziosa senza che un test se ne accorga.

Il caso che l'ha reso visibile (trovato da ws6 sulla cura a1c71ee0):

    «Marco leads the payments team.» / «Anna leads the payments team.»

sono due candidati allo STESSO ruolo. Tenerli entrambi e' coerente col
principio di casa — «perdere un fatto vero e' IRREVERSIBILE, tenerne due NO» —
ma tacere no: chi legge la memoria deve poter vedere che c'e' una tensione.

Il ramo `L3-coexistence` esisteva gia' e diceva esattamente questo; non veniva
raggiunto perche' il `continue` esce prima.
"""
from __future__ import annotations

from pathlib import Path

from verimem.client import Memory


def _avvisi(res: dict) -> list[str]:
    return [w.get("layer") for w in (res.get("warnings") or [])]


def test_due_candidati_allo_stesso_ruolo_coesistono_e_la_ricevuta_lo_dice(tmp_path: Path) -> None:
    """Il caso di ws6: entrambi vivi, e il secondo lo dichiara."""
    m = Memory(path=tmp_path / "ruolo.db")
    src = "Marco leads the payments team."
    m.add("Marco leads the payments team.", topic="t/ruolo", source=src)
    res = m.add("Anna leads the payments team.", topic="t/ruolo",
                source="Anna leads the payments team.")
    assert res.get("status") != "quarantined", "il secondo non va quarantinato"
    assert "L3-coexistence" in _avvisi(res), (
        f"la terza uscita non e' dichiarata nella ricevuta: {_avvisi(res)}"
    )


def test_un_aggiornamento_legittimo_non_prende_l_avviso(tmp_path: Path) -> None:
    """Il controllo che puo' fallire: dove il gate RITIRA davvero, non c'e'
    nessuna coesistenza da annunciare. Se questo diventa rosso, l'avviso e'
    diventato rumore su ogni scrittura."""
    m = Memory(path=tmp_path / "agg.db")
    src = "Il file pesa 10 MB."
    m.add("Il file pesa 10 MB.", topic="t/agg", source=src)
    res = m.add("Il file pesa 12 MB.", topic="t/agg", source="Il file pesa 12 MB.")
    assert "L3-coexistence" not in _avvisi(res)


def test_una_scrittura_senza_parenti_non_prende_l_avviso(tmp_path: Path) -> None:
    """Secondo controllo: su un topic vuoto non c'e' nessuna relazione, quindi
    nessun avviso. Guarda che l'avviso non sia incondizionato."""
    m = Memory(path=tmp_path / "solo.db")
    res = m.add("Il servizio di fatturazione e' attivo.", topic="t/solo",
                source="Il servizio di fatturazione e' attivo.")
    assert "L3-coexistence" not in _avvisi(res)
