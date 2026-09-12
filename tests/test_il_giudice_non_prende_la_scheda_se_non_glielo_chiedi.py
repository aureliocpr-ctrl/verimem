"""T63a — si deve poter dire al giudice di NON prendere la scheda.

IL FATTO CHE HA PRODOTTO QUESTO BANCO, misurato il 2026-09-11 su una macchina
con una sola scheda da 8 GB:

    nove processi del prodotto con un contesto CUDA aperto
    7836 MiB occupati su 8151 (96 %)   utilizzo di calcolo: 0 %
    ⇒ 315 MiB liberi: la prossima allocazione di chiunque fallisce

Nessuno stava calcolando: la scheda era stata presa all'avvio e non restituita.
E non per una scelta sbagliata, ma perche' UNA SCELTA NON C'ERA: due punti
decidevano da soli e non esisteva modo di contraddirli.

⚠️ QUESTO BANCO NON CARICA TORCH, e non e' pigrizia: importarlo costa ~2,6 GB
per processo. Verifica due cose che si possono verificare a costo zero — la
FUNZIONE di scelta, e il fatto che i due punti del prodotto la USINO davvero.
La verifica che nessun processo tenga VRAM si fa dall'esterno con
`nvidia-smi --query-compute-apps`: sta nel ticket, non qui, perche' in CI non
c'e' nessuna scheda e un banco che li' non puo' accendersi direbbe verde senza
aver guardato niente.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from verimem._device import ENV_DEVICE, device_richiesto, scegli_device

#: I punti del prodotto che caricano un modello e devono passare dalla scelta.
MODULI = ("verimem/local_grounding.py", "verimem/local_relation.py")


def _radice() -> Path:
    return Path(__file__).resolve().parents[1]


def _chiamate_dirette_a_cuda(sorgente: str) -> list[int]:
    """Le righe dove `torch.cuda.is_available()` viene CHIAMATA.

    Cerca con `ast`, non con una sottostringa: dopo la cura quel nome compare
    ancora nel file — passato come callable a `scegli_device` — e un criterio
    testuale direbbe rosso su codice gia' curato.
    """
    fuori: list[int] = []
    for nodo in ast.walk(ast.parse(sorgente)):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        if isinstance(f, ast.Attribute) and f.attr == "is_available":
            interno = f.value
            if isinstance(interno, ast.Attribute) and interno.attr == "cuda":
                fuori.append(nodo.lineno)
    return fuori


@pytest.mark.parametrize("modulo", MODULI)
def test_il_prodotto_non_interroga_la_scheda_di_sua_iniziativa(modulo: str) -> None:
    """IL RED: prima della cura questi due file chiamano `is_available()` da
    soli, quindi il contesto CUDA nasce PRIMA che qualcuno possa dire di no.
    Chiedere «c'e' una scheda?» inizializza il runtime: la domanda non e'
    gratis, e va fatta solo quando la risposta puo' cambiare qualcosa.
    """
    percorso = _radice() / modulo
    righe = _chiamate_dirette_a_cuda(percorso.read_text(encoding="utf-8"))
    assert not righe, (
        f"{modulo} chiama torch.cuda.is_available() alle righe {righe}: "
        "la scheda viene inizializzata prima che la configurazione possa "
        f"dire di no. Passa da scegli_device() e onora {ENV_DEVICE}.")


def test_chi_chiede_la_cpu_non_fa_nemmeno_la_domanda() -> None:
    """Il cuore: con 'cpu' il callable NON deve essere chiamato.

    Se lo fosse, la cura sarebbe finta — il contesto nascerebbe lo stesso e la
    VRAM resterebbe occupata esattamente come prima.
    """
    chiamate: list[int] = []

    def cuda_disponibile() -> bool:
        chiamate.append(1)
        return True

    assert scegli_device(cuda_disponibile, {ENV_DEVICE: "cpu"}) == "cpu"
    assert chiamate == [], (
        "con 'cpu' il prodotto ha comunque interrogato la scheda: interrogarla "
        "la inizializza, quindi questa cura non toglierebbe un solo MiB")


def test_auto_si_comporta_come_prima() -> None:
    """Il default non cambia nulla: chi non configura niente non se ne accorge."""
    assert scegli_device(lambda: True, {}) == "cuda"
    assert scegli_device(lambda: False, {}) == "cpu"
    assert device_richiesto({}) == "auto"


def test_cuda_chiesta_e_assente_e_un_errore_non_un_ripiego() -> None:
    """Chi chiede 'cuda' conta su prestazioni: se non c'e', deve saperlo subito.

    Un ripiego silenzioso sulla CPU si scopre da un rallentamento inspiegato,
    e costa piu' di un errore letto all'avvio.
    """
    with pytest.raises(RuntimeError, match="non e' disponibile"):
        scegli_device(lambda: False, {ENV_DEVICE: "cuda"})


def test_un_valore_che_non_capiamo_ferma_invece_di_indovinare() -> None:
    with pytest.raises(ValueError, match="non e' un valore ammesso"):
        device_richiesto({ENV_DEVICE: "gpu"})


#: I costruttori che il device lo scelgono DA SOLI se non glielo dici.
COSTRUTTORI_CHE_SCELGONO = ("SentenceTransformer", "CrossEncoder")


def _costruttori_senza_device(sorgente: str) -> list[tuple[int, str]]:
    """Le chiamate a quei costruttori PRIVE del keyword `device`.

    Cerca con `ast` i keyword della chiamata: `device=` in mezzo agli argomenti
    non si vede con una sottostringa, e una sottostringa lo troverebbe anche in
    un commento.
    """
    fuori: list[tuple[int, str]] = []
    for nodo in ast.walk(ast.parse(sorgente)):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        nome = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
        if nome not in COSTRUTTORI_CHE_SCELGONO:
            continue
        if not any(k.arg == "device" for k in nodo.keywords):
            fuori.append((nodo.lineno, nome))
    return fuori


def test_nessun_modello_sceglie_la_scheda_al_posto_nostro() -> None:
    """LA META' DEL PROBLEMA CHE IL GREP NON TROVA.

    `SentenceTransformer(m)` senza `device=` prende la scheda per conto suo: nel
    nostro codice la parola «cuda» non compare mai, eppure il contesto nasce —
    e il processo entra nella lista di chi tiene la VRAM. Cercando «cuda» nei
    sorgenti avevo trovato DUE punti; i punti veri erano il doppio, e questa
    cella e' nata proprio da quel conteggio sbagliato.

    `device=None` (il default di `auto`) lascia decidere alla libreria come
    prima: dichiararlo non cambia il comportamento, rende possibile cambiarlo.
    """
    nudi: list[str] = []
    for percorso in sorted((_radice() / "verimem").rglob("*.py")):
        for riga, nome in _costruttori_senza_device(
                percorso.read_text(encoding="utf-8", errors="replace")):
            nudi.append(f"{percorso.name}:{riga} {nome}(...)")
    assert not nudi, (
        "questi modelli scelgono il device da soli, quindi possono prendere la "
        f"scheda anche quando {ENV_DEVICE}=cpu:\n  " + "\n  ".join(nudi))
