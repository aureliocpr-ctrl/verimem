"""Il cricchetto delle copie deve mordere (regola R3).

Un cricchetto che non è mai diventato rosso è un sensore scollegato: qui la
prova sta in due esecuzioni nello stesso file — il repo com'è deve uscire 0, e
il repo con UNA copia in più deve uscire 1. Se il secondo caso resta verde, il
presidio non presidia niente e questo test lo dice.

Eseguito il 09/09/2026 sul tip 20257636:
    python -m pytest tests/test_copie_cricchetto.py -q
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

RADICE = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("copie", RADICE / "scripts" / "copie.py")
copie = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(copie)


@pytest.fixture(scope="module")
def misura_di_oggi():
    return copie.conta(copie.PACCHETTO)


def test_ogni_file_del_pacchetto_e_stato_letto(misura_di_oggi):
    """Un file che non si legge non è un file senza copie: il conteggio sarebbe un minimo."""
    assert misura_di_oggi["non_letti"] == [], (
        "file non letti da ast: il numero delle copie sarebbe un minimo, non un totale"
    )
    assert misura_di_oggi["file_letti"] > 300, misura_di_oggi["file_letti"]


def test_nessun_tetto_e_superato(misura_di_oggi):
    saliti = {
        chiave: (misura_di_oggi["misure"][chiave], tetto)
        for chiave, tetto in copie.TETTI.items()
        if misura_di_oggi["misure"][chiave] > tetto
    }
    assert not saliti, (
        f"una primitiva è stata riscritta invece di essere importata: {saliti}. "
        "Importa quella che esiste, oppure alza il tetto in scripts/copie.py "
        "nello stesso commit, col motivo nel messaggio."
    )


def test_il_debito_degli_status_non_sale(misura_di_oggi):
    """Gli elenchi con `quarantined` e senza `user_belief` (T49) devono scendere, non salire."""
    assert (
        misura_di_oggi["debito_status_senza_user_belief"]
        <= copie.DEBITO_STATUS_SENZA_USER_BELIEF
    ), misura_di_oggi["status_senza_user_belief"]


def test_il_cricchetto_diventa_rosso_su_una_copia_in_piu():
    """IL CONTROLLO POSITIVO: senza questo, i tre test qui sopra passerebbero anche
    se `conta` restituisse zero per un errore di criterio."""
    con_copia = copie.conta(copie.PACCHETTO, copia_finta="_jaccard")
    assert con_copia["misure"]["def__jaccard"] == copie.TETTI["def__jaccard"] + 1
    assert copie.stampa(con_copia, dettaglio=False) == 1


def test_i_tetti_hanno_tutti_un_criterio_scritto():
    """Un tetto senza criterio è una cifra senza formula: il numero da solo non si difende."""
    assert set(copie.TETTI) == set(copie.CRITERI), (
        set(copie.TETTI) ^ set(copie.CRITERI)
    )


def test_conta_legge_davvero_i_file_dal_disco(tmp_path):
    """L'iniezione di `copia_finta` salta il filesystem: questo prova che una copia
    scritta in un file NUOVO verrebbe vista per davvero (altrimenti il cricchetto
    sarebbe cieco proprio sul caso che deve prendere)."""
    finto = tmp_path / "verimem_finto"
    finto.mkdir()
    (finto / "modulo.py").write_text(
        "def _jaccard(a, b):\n"
        "    return 0.0\n"
        "\n"
        "\n"
        "class X:\n"
        "    def _tokens(self, s):\n"
        "        return []\n",
        encoding="utf-8",
    )
    risultato = copie.conta(finto)
    assert risultato["misure"]["def__jaccard"] == 1
    assert risultato["misure"]["def__tokens"] == 1, "un metodo dentro una classe deve contare"
    assert risultato["non_letti"] == []
