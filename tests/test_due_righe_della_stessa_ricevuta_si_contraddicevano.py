"""Due righe consecutive della stessa ricevuta si contraddicevano sul giudice.

MISURATO ALLA PORTA CLI il 30/08 alle 20:40 — store temporaneo, daemon giu',
modello sul disco, `verimem save --source ...`::

    L4-skipped — ... the local CE judge is warming ... It is NOT missing ...
    not verified — ... no grounding judge is installed ... run `verimem warmup`

La prima riga dice che il giudice **c'e' e sta caricando**; la seconda, subito
sotto, dice che **non e' installato** e manda a scaricarne uno da ~2,3 GB che e'
gia' li'. Un operatore legge le due e non puo' avere ragione in entrambi i modi.

⚠️ E LA CRONACA DEL DIFETTO GEMELLO ERA GIA' NEL FILE. Il 2026-08-21 la stessa
riga era stata curata perche' diceva «no source» a chi la fonte l'aveva passata:
*«la riga PRIMA (L4-skipped) diceva gia' il vero, e le due si contraddicevano
sullo stesso schermo»*. Quella cura ha separato DUE stati — «nessuna fonte» e
«nessun giudice» — e il campo `moat` ne conosce due. **Il giudice pero' ne ha
TRE** (`judge_state()`: `absent` · `warming` · `failed`), e tutti e tre cadono in
`not_run:no_judge`. ⇒ Lo stesso difetto e' tornato **un livello piu' in la'**,
per la stessa ragione: una domanda a tre stati risposta con un campo a due.

🔑 E il commento di quella cura nomina il presidio che non l'ha presa: *«Quel
test guarda il DATO; nessuno guardava la riga STAMPATA, ed e' li' che si
perdeva»*. Adesso qualcuno guarda la riga stampata — ma la guardava in **uno**
stato. Questo file la guarda in **tutti e tre**.

SECONDO DIFETTO, stessa misura: l'avviso `L4-skipped` in stato `warming`
consigliava *«or writing through the CLI, gets the moat verdict»* — e la corsa
che l'ha stampato **era la CLI** (`surface=cli`, `judged=False`). Il rimedio si
autocitava. La CLI e' anch'essa in delegate-only: cio' che fa la differenza non
e' la porta, e' il **daemon** condiviso, che l'avviso non nominava.
"""

from __future__ import annotations

import pytest

from verimem import anti_confab_gate as gate
from verimem.cli import riga_moat_non_verificato

TRE_STATI = ["absent", "warming", "failed"]


@pytest.fixture
def stato(monkeypatch):
    def _set(valore: str) -> None:
        monkeypatch.setattr("verimem.local_grounding.judge_state",
                            lambda: valore)
    return _set


# ------------------------------------------------- LA RIGA DELLA CLI, TRE STATI --
def test_in_warming_la_cli_non_dice_che_il_giudice_manca(stato):
    """IL CUORE: e' la riga che contraddiceva quella sopra."""
    stato("warming")
    riga = riga_moat_non_verificato("not_run:no_judge")
    assert "not installed" not in riga, riga
    assert "warmup" not in riga or "would not help" in riga, (
        f"la riga manda ancora a scaricare un modello gia' presente: {riga}")


def test_in_absent_la_cli_continua_a_dire_di_scaricarlo(stato):
    """⚠️ LA POPOLAZIONE OPPOSTA, senza la quale la prima si soddisfa
    cancellando il rimedio: quando il modello NON c'e', `warmup` e' la cosa
    giusta da dire e deve restare."""
    stato("absent")
    riga = riga_moat_non_verificato("not_run:no_judge")
    assert "warmup" in riga, riga


def test_in_failed_la_cli_manda_alla_diagnosi_non_al_download(stato):
    stato("failed")
    riga = riga_moat_non_verificato("not_run:no_judge")
    assert "doctor" in riga and "warmup" not in riga, riga


@pytest.mark.parametrize("s", TRE_STATI)
def test_i_tre_stati_danno_tre_righe_diverse(s, stato):
    """La ragione per cui la cura del 21/08 non bastava: un campo a due valori
    non puo' rispondere a una domanda che ne ha tre."""
    stato(s)
    righe = {}
    for altro in TRE_STATI:
        stato(altro)
        righe[altro] = riga_moat_non_verificato("not_run:no_judge")
    assert len(set(righe.values())) == 3, righe


def test_senza_fonte_la_riga_resta_quella_di_prima(stato):
    """L'altro ramo non si tocca: chi non ha passato una fonte deve continuare a
    leggere che gliene serve una."""
    stato("warming")
    riga = riga_moat_non_verificato("not_run:no_source")
    assert "--source" in riga and "no source" in riga, riga


# ------------------------------------- L'AVVISO DEL GATE NON SI AUTOCITA PIU' --
def test_l_avviso_in_warming_non_consiglia_la_porta_da_cui_esce(stato):
    """Il rimedio deve nominare la CONDIZIONE (il daemon), non una porta che si
    trova nello stesso stato di quella da cui l'avviso e' uscito."""
    stato("warming")
    avviso = gate._advisory_l4_skipped()
    testo = str(avviso.get("advice", ""))
    assert "writing through the CLI" not in testo, testo
    assert "daemon" in testo, (
        f"il rimedio non nomina la condizione che lo rende vero: {testo}")


def test_l_avviso_in_warming_dice_che_warmup_non_serve(stato):
    """Era la meta' che contraddiceva la riga della CLI: se il modello e' su
    disco, mandare a scaricarlo e' una diagnosi confidente e sbagliata."""
    stato("warming")
    testo = str(gate._advisory_l4_skipped().get("advice", ""))
    assert "NOT missing" in testo and "not help" in testo, testo
