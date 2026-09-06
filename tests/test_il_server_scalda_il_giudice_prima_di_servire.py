"""Il server deve caricare la catena del giudice ALL'AVVIO, prima di servire.

MISURATO il 06/09 sul server MCP, e questo test esiste per quello:

  · durante una richiesta in corso NESSUNA estensione C si carica nel processo —
    bloccata anche una senza alcun legame con scipy — mentre il GIL resta libero
    (una sonda continua a stampare ogni 5 s per tutti i 121 s del blocco);
  · PRIMA che la richiesta arrivi, lo stesso import passa in 0,5 s;
  · caricando la catena prima, la scrittura con fonte torna in 17,3 s di mediana
    (16,9 · 17,7 · 16,9 su tre giri, stack dell'utente) invece di non tornare in
    1800 s, e la seconda scrittura costa 0,1 s.

L'ipotesi sul PERCHÉ — il loader lock di Windows tenuto dal thread dentro il
caricamento di `_fblas` — resta un'ipotesi: non è osservabile da Python. Ma la
cura non ne dipende: **il caricamento va fatto dove il caricamento si può fare**.

⚠️ DUE TEST, E IL SECONDO ESISTE PER UN DIFETTO DEL PRIMO che ho trovato
rileggendolo: «scipy è in sys.modules dopo il preload» **passerebbe anche senza
la cura**, perché `preload_embedding` in certi ambienti chiama `_warm()`, che
importa `sentence_transformers`, che importa scipy per conto suo (preload.py:220
→ embedding.py:51). Un test verde per un effetto collaterale è peggio di nessun
test. Quindi:

  · il primo presidia la FUNZIONE, che deve esistere e caricare da sola;
  · il secondo presidia il COLLEGAMENTO, in delegate-only — dove l'embedder NON
    viene caricato e quindi l'effetto collaterale non può salvare il test.

⚠️ SUBPROCESS in entrambi: dentro pytest `scipy.linalg` è già importato da altri
test, quindi un assert in-process direbbe sempre «verde». `PARTENZA-PULITA` è il
controllo che il subprocess sia davvero partito senza la catena.
"""
import subprocess
import sys
import textwrap

_PREAMBOLO = """
    import os, sys
    os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
    os.environ.pop("ENGRAM_GROUNDING_WRITE", None)
    assert "scipy.linalg" not in sys.modules, "PARTENZA-SPORCA"
    print("PARTENZA-PULITA", flush=True)
"""

_LA_FUNZIONE = textwrap.dedent(_PREAMBOLO + """
    from verimem.preload import _scalda_le_librerie_del_giudice
    _scalda_le_librerie_del_giudice(log=None)
    print("SCIPY-CARICATO=%s" % ("scipy.linalg" in sys.modules), flush=True)
""")

_IL_COLLEGAMENTO = textwrap.dedent("""
    import os, sys
    os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
    # delegate-only: l'embedder NON viene caricato, quindi se scipy compare è
    # perché il preload lo carica di proposito e non per effetto collaterale.
    os.environ["HIPPO_ENCODE_DELEGATE_ONLY"] = "1"
    os.environ.pop("ENGRAM_GROUNDING_WRITE", None)
    assert "scipy.linalg" not in sys.modules, "PARTENZA-SPORCA"
    print("PARTENZA-PULITA", flush=True)

    from verimem.preload import preload_embedding
    th = preload_embedding(log=None)
    if th is not None:
        th.join(180)
    # ⚠️ QUI C'ERA UN `import sentence_transformers` per una diagnostica, e
    # RENDEVA IL TEST CIECO: quell'import tira dentro scipy da solo, quindi il
    # test passava anche senza la cura (misurato: 1 failed 1 passed sul prodotto
    # pre-cura, quando avrebbe dovuto essere 2 failed). Un banco non deve mai
    # caricare cio' che sta misurando. Si guarda e basta.
    print("EMBEDDER-VISTO=%s"
          % any(m.startswith("sentence_transformers") for m in sys.modules),
          flush=True)
    print("SCIPY-CARICATO=%s" % ("scipy.linalg" in sys.modules), flush=True)
""")


def _esegui(codice: str) -> tuple[int, str]:
    """Esegue e restituisce (returncode, output).

    ⚠️ IL `returncode` NON E' UN DETTAGLIO, ed e' il difetto che questo file
    aveva quando e' entrato in main il 06/09: leggevo solo stdout+stderr, quindi
    un processo MORTO lasciava l'output tronco e ogni assert riferiva «manca la
    stringa X» invece di «il processo e' morto» — in CI il messaggio viene pure
    troncato e la causa sparisce. Il banco di guardia
    ``test_nessun_banco_nuovo_ignora_l_esito_del_subprocess`` l'ha visto e ha
    fatto rosso su tre job: aveva ragione. Il codice d'uscita va LETTO e va
    finire nel messaggio, altrimenti si diagnostica il soggetto per una colpa
    dello strumento.
    """
    esito = subprocess.run([sys.executable, "-c", codice],
                           capture_output=True, text=True, timeout=600)
    return esito.returncode, (esito.stdout or "") + (esito.stderr or "")


def test_la_funzione_di_preload_carica_la_catena_del_giudice():
    """Il pezzo: esiste una funzione che carica la catena, e la carica."""
    rc, fuori = _esegui(_LA_FUNZIONE)
    assert "PARTENZA-PULITA" in fuori, (
        f"subprocess partito sporco: il banco non dice niente. rc={rc} coda={fuori[-300:]}")
    assert "SCIPY-CARICATO=True" in fuori, (
        "la funzione di preload del giudice non carica la catena (o non esiste): "
        "la prima scrittura con fonte se la caricherà addosso, e a quel punto nel "
        "processo non si carica più nessuna estensione C finché la richiesta non "
        f"finisce — misurato: non torna in 1800 s. rc={rc} coda={fuori[-300:]}")


def test_il_preload_del_server_la_chiama_anche_in_delegate_only():
    """Il collegamento, nell'unico ambiente dove l'effetto collaterale non salva.

    In delegate-only il preload NON carica l'embedder, quindi `scipy` non può
    entrare in `sys.modules` per la via di `sentence_transformers`: se c'è, c'è
    perché il preload lo ha voluto.
    """
    rc, fuori = _esegui(_IL_COLLEGAMENTO)
    assert "PARTENZA-PULITA" in fuori, (
        f"subprocess partito sporco: il banco non dice niente. rc={rc} coda={fuori[-300:]}")
    assert "SCIPY-CARICATO=True" in fuori, (
        "in delegate-only il preload del server NON carica la catena del giudice. "
        "È l'ambiente del server MCP (HIPPO_ENCODE_DELEGATE_ONLY=1 lo imposta "
        f"`main()` stesso), cioè proprio quello dove il difetto morde. rc={rc} coda={fuori[-300:]}")
