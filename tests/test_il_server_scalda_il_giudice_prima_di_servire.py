"""Il server deve caricare la catena del giudice ALL'AVVIO, prima di servire.

MISURATO il 06/09 sul server MCP, e questo test esiste per quello:

  · durante una richiesta in corso NESSUNA estensione C si carica nel processo —
    bloccata anche una senza alcun legame con scipy — mentre il GIL resta libero
    (una sonda continua a stampare ogni 5 s per tutti i 121 s del blocco);
  · PRIMA che la richiesta arrivi, lo stesso import passa in 0,5 s;
  · caricando la catena prima, la scrittura con fonte torna in 17,3 s di mediana
    (16,9 · 17,7 · 16,9 su tre giri, stack dell'utente) invece di non tornare in
    1800 s.

L'ipotesi sul PERCHÉ — il loader lock di Windows tenuto dal thread dentro il
caricamento di `_fblas` — resta un'ipotesi: non è osservabile da Python. Ma la
cura non ne dipende: **il caricamento va fatto dove il caricamento si può fare**,
cioè prima di servire.

⚠️ SUBPROCESS, e non è un vezzo: dentro pytest `scipy.linalg` è già importato da
altri test, quindi un assert in-process direbbe sempre «verde» e non misurerebbe
niente. Il controllo positivo del banco è che il subprocess parta pulito.

È la stessa famiglia di difetto che `preload.py` documenta da mesi per
l'embedder — «NEVER cold-load in-process» — e che per il giudice non vale, perché
il suo warm è condizionato a `ENGRAM_GROUNDING_WRITE`, «assente = NO».
"""
import subprocess
import sys
import textwrap

_PROVA = textwrap.dedent(
    """
    import os, sys
    os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
    os.environ.pop("ENGRAM_GROUNDING_WRITE", None)

    # controllo positivo: il processo deve partire SENZA la catena caricata,
    # altrimenti il banco direbbe verde senza aver misurato niente
    assert "scipy.linalg" not in sys.modules, "PARTENZA-SPORCA"
    print("PARTENZA-PULITA", flush=True)

    from verimem.preload import preload_embedding
    th = preload_embedding(log=None)
    if th is not None:
        th.join(180)

    print("SCIPY-CARICATO=%s" % ("scipy.linalg" in sys.modules), flush=True)
    """
)


def test_il_preload_del_server_carica_la_catena_del_giudice():
    """Dopo il preload d'avvio, la catena che serve al giudice deve esserci."""
    esito = subprocess.run(
        [sys.executable, "-c", _PROVA],
        capture_output=True, text=True, timeout=600,
    )
    fuori = (esito.stdout or "") + (esito.stderr or "")

    assert "PARTENZA-PULITA" in fuori, (
        "il sottoprocesso è partito con scipy.linalg già caricato: questo banco "
        f"non può dire niente. Output: {fuori[-400:]}")

    assert "SCIPY-CARICATO=True" in fuori, (
        "dopo il preload d'avvio la catena del giudice NON è caricata: la prima "
        "scrittura con fonte se la caricherà addosso, e a quel punto nel processo "
        "non si carica più nessuna estensione C finché la richiesta non finisce "
        "(misurato: non torna in 1800 s). Il preload deve scaldare anche il "
        f"giudice, non solo l'embedder. Output: {fuori[-400:]}")
