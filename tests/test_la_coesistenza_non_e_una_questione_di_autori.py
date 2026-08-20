"""L'avviso della coesistenza attribuiva la decisione a un criterio RITIRATO.

Quando il gate tiene due fatti in tensione invece di ritirarne uno, lo dichiara
con `L3-coexistence`. Il testo diceva::

    the clashing facts come from DIFFERENT declared authors: neither is an
    update of the other, so both stay servable ...

⚠️ MA NESSUN CONFRONTO FRA AUTORI VIENE MAI FATTO su quella via. Le coppie
escono dalla terza uscita per l'asse delle ENTITÀ (`_entita_diverse`: un codice,
una data, un record numerato, un attributo contrastante, un nome proprio), e
l'asse degli autori è stato sostituito da quello. Sul caso canonico del ramo —
«Marco leads the payments team» / «Anna leads the payments team» — Marco e Anna
sono i SOGGETTI dei due fatti, non chi li ha scritti: il messaggio scambia
l'entità nominata DENTRO il fatto con l'autore DEL fatto.

Riprodotto il 20/08 alle 14:51 scrivendo due fatti nello stesso processo, con lo
stesso principal e nessun `verified_by`: il gate ha comunque risposto «DIFFERENT
declared authors».

🔑 PERCHÉ VALE UN PRESIDIO E NON SOLO UNA CORREZIONE. È la SECONDA volta che
questo stesso messaggio dichiara qualcosa che non è avvenuto: il commento sopra
il ramo racconta la prima, quando annunciava «the older value is superseded» con
`supersede_ids` intatto. Un messaggio che nessun test legge può tornare a
mentire una terza volta senza che nessuno se ne accorga — e per un prodotto che
vende memoria verificata, un avviso che confabula è la classe di difetto che il
gate esiste per fermare.
"""
from __future__ import annotations

from pathlib import Path

from verimem.client import Memory


def _consiglio_coesistenza(res: dict) -> str:
    for w in (res.get("warnings") or []):
        if str(w.get("layer")) == "L3-coexistence":
            return str(w.get("advice") or "")
    return ""


def _due_candidati(tmp_path: Path, nome: str) -> dict:
    """Il caso canonico del ramo, scritto da UN SOLO autore."""
    m = Memory(path=tmp_path / f"{nome}.db")
    m.add("Marco leads the payments team.", topic="t/ruolo",
          source="Marco leads the payments team.")
    return m.add("Anna leads the payments team.", topic="t/ruolo",
                 source="Anna leads the payments team.")


def test_l_avviso_non_attribuisce_la_coesistenza_agli_AUTORI(tmp_path: Path) -> None:
    """IL CUORE: i due fatti hanno lo stesso autore, quindi il gate non può
    dire che vengono da autori diversi."""
    consiglio = _consiglio_coesistenza(_due_candidati(tmp_path, "autori"))
    assert consiglio, "il ramo L3-coexistence non e' stato raggiunto"
    basso = consiglio.lower()
    assert "author" not in basso and "autor" not in basso, (
        "l'avviso attribuisce la coesistenza a un confronto fra AUTORI che non "
        f"e' mai stato fatto: {consiglio!r}")


def test_l_avviso_nomina_il_criterio_che_ha_deciso_davvero(tmp_path: Path) -> None:
    """Non basta togliere la parola sbagliata: chi legge la ricevuta deve
    sapere PERCHE' i due fatti convivono."""
    consiglio = _consiglio_coesistenza(_due_candidati(tmp_path, "criterio"))
    assert consiglio, "il ramo L3-coexistence non e' stato raggiunto"
    assert "entit" in consiglio.lower(), (
        f"l'avviso non nomina l'asse che ha deciso: {consiglio!r}")


def test_CONTROLLO_un_aggiornamento_vero_non_prende_l_avviso(tmp_path: Path) -> None:
    """⚠️ Il controllo opposto: dove il gate RITIRA davvero non c'e' nessuna
    coesistenza da annunciare. Senza questo, un avviso incondizionato passerebbe
    i due test qui sopra."""
    m = Memory(path=tmp_path / "agg.db")
    m.add("Il file pesa 10 MB.", topic="t/agg", source="Il file pesa 10 MB.")
    res = m.add("Il file pesa 12 MB.", topic="t/agg", source="Il file pesa 12 MB.")
    assert not _consiglio_coesistenza(res)
