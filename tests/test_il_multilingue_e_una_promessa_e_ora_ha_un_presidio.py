"""La memoria multilingue è una promessa del prodotto, e nessuno la presidiava.

MISURATO DA UTENTE, con i fatti scritti TUTTI IN ITALIANO e le domande in otto
lingue, sul modello che il prodotto usa davvero (``intfloat/multilingual-e5-base``,
768 dim)::

    [it] 0.889   [en] 0.8641  [de] 0.8403  [fr] 0.8804
    [es] 0.8705  [pt] 0.8795  [nl] 0.8509  [pl] 0.8223
    risposte giuste: 8/8

Otto lingue, otto risposte corrette, tutte sopra 0.82. Il retrieval funziona
davvero cross-lingua — e questa è una **cosa che il prodotto fa bene** e che
non aveva un solo test.

⚠️ PERCHÉ SERVE UN PRESIDIO E NON BASTA LA MISURA: il giorno in cui qualcuno
cambia embedder, aggiunge una normalizzazione monolingue (una stoplist, uno
stemmer italiano, un lowercase ASCII) o tocca il ranking, questa garanzia si
rompe **in silenzio** — non c'è nessuna riga che la difenda. È già successo in
casa: `content_tokens` leggeva ASCII e dava zero token sul cirillico.

⚠️ E L'ASIMMETRIA CHE NE ESCE, da mettere accanto:
    TROVARE (recall)     8 lingue su 8    <- questo file
    CONTARE (ask/count)  2 lingue su 8    <- misurato, `_COUNT` è IT/EN
Il prodotto capisce le domande in otto lingue quando deve trovare, e in due
quando deve contare.

═══════════════════════════════════════════════════════════════════════════
⚠️⚠️ PERCHÉ QUESTO FILE LANCIA UN SUBPROCESS INVECE DI CHIAMARE ``Memory()``
═══════════════════════════════════════════════════════════════════════════
Perché dentro pytest **il modello NON è quello del prodotto**, e la prima
stesura di questo file misurava un encoder che nessun utente riceve::

    tests/conftest.py:11-12   paraphrase-multilingual-MiniLM-L12-v2, dim 384
    prodotto (CONFIG default) intfloat/multilingual-e5-base,        dim 768

Il conftest lo dichiara apertamente («server=e5/768 via config-default,
test=L12/384»): è una separazione voluta, non un bug. Ma per un presidio di
PROMESSE cambia tutto — i punteggi qui sopra li ho misurati da utente, con e5,
e il test li verificava su L12. **Due modelli sotto la stessa frase.**

E non è solo un'inesattezza sulla carta: il 2026-08-21 il primo run del workflow
``presidi-lenti`` (32475919020 su ``93d5e379``) è morto con **16 ERROR in
setup**, tutti::

    huggingface_hub.errors.LocalEntryNotFoundError: Cannot find the requested
    files in the disk cache and outgoing traffic has been disabled.

``verimem warmup`` aveva funzionato — nel log «✓ model ready in 16.6s (vector
dim 768)» — ma scalda ``CONFIG.embedding_model``, cioè il modello del PRODOTTO.
Il conftest ne chiedeva un altro, che nessuno aveva scaricato, e impone
``HF_HUB_OFFLINE=1``. Da me era verde perché la mia macchina ha entrambi i
modelli in cache: la classe «un rosso che non si riproduce dipende da ciò che
la TUA macchina ha e la loro no», al contrario.

Il subprocess risolve le tre cose in una:

* misura **l'ambiente che l'utente installa**, senza conftest di mezzo — e un
  presidio di promesse deve misurare la configurazione consegnata;
* non lascia e5 (1.1 GB) caricato nel processo pytest per i test successivi,
  che è quello che farebbe un monkeypatch di ``embedding._MODEL``;
* carica il modello **una volta sola** per tutti e 17 i test, perché la fixture
  è ``scope="session"``.

Marcato ``slow``: carica sentence-transformers davvero, e il modello è quello
grande.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.slow

#: Il marcatore che separa il risultato dal rumore: il subprocess è un processo
#: verimem vero e scrive log strutturati su stdout, quindi il JSON non può
#: essere «tutto l'output» — va pescato per riga.
_MARCATORE = "@@GIRO-MULTILINGUE@@"

FATTI_IT = [
    "Il magazzino centrale di Rovigo ha 4200 metri quadrati.",
    "La prova gratuita dura quattordici giorni.",
    "L'assistenza risponde entro due giorni lavorativi.",
    "Il piano annuale costa 1200 euro all'anno.",
]

DOMANDE = [
    ("it", "Quanto dura la prova gratuita?"),
    ("en", "How long is the free trial?"),
    ("de", "Wie lange dauert die kostenlose Testphase?"),
    ("fr", "Combien de temps dure l'essai gratuit?"),
    ("es", "Cuanto dura la prueba gratuita?"),
    ("pt", "Quanto tempo dura o teste gratuito?"),
    ("nl", "Hoe lang duurt de gratis proefperiode?"),
    ("pl", "Jak dlugo trwa bezplatny okres probny?"),
]

#: una domanda fuori tema PER OGNI lingua, con la stessa forma della sua
#: gemella in tema: è il termine di paragone che rende leggibile lo score.
FUORI_TEMA = {
    "it": "Quale database usa il cluster di produzione?",
    "en": "Which database does the production cluster use?",
    "de": "Welche Datenbank nutzt der Produktions-Cluster?",
    "fr": "Quelle base de donnees utilise le cluster de production?",
    "es": "Que base de datos usa el cluster de produccion?",
    "pt": "Qual base de dados usa o cluster de producao?",
    "nl": "Welke database gebruikt het productiecluster?",
    "pl": "Ktorej bazy danych uzywa klaster produkcyjny?",
}

#: Lo script del giro: gira in un processo NUOVO, quindi importa la config del
#: prodotto senza nessuna fixture di mezzo. Riceve i dati come argomenti JSON
#: per non duplicare le liste qui sopra — due copie divergono.
_SCRIPT = '''
import json, os, sys

from verimem.config import CONFIG
from verimem.client import Memory

cartella, fatti, domande, fuori = (
    sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3]),
    json.loads(sys.argv[4]))

m = Memory(os.path.join(cartella, "memoria", "s.db"))
for f in fatti:
    m.add(f, topic="az/faq")

esiti = {}
for lingua, domanda in domande:
    in_tema = m.recall(domanda, k=1)
    fuori_tema = m.recall(fuori[lingua], k=1)
    esiti[lingua] = {
        "domanda": domanda,
        "testo": str(in_tema[0].get("text") or "") if in_tema else "",
        "score": float(in_tema[0].get("score") or 0.0) if in_tema else 0.0,
        "score_fuori_tema": (
            float(fuori_tema[0].get("score") or 0.0) if fuori_tema else 0.0),
    }

print(MARCATORE + " " + json.dumps(
    {"modello": CONFIG.embedding_model, "dim": CONFIG.embedding_dim,
     # Il pin COME IL FIGLIO LO VEDE: se il controllo fallisce, questo campo
     # dice se l'ha ereditato dall'ambiente o se e' il default ad essere
     # cambiato — due diagnosi opposte sotto lo stesso rosso.
     "pin_ereditato": os.environ.get("HIPPO_EMBEDDING_MODEL"),
     "esiti": esiti}))
'''


@pytest.fixture(scope="session")
def giro_multilingue(tmp_path_factory):
    """Esegue il giro in un processo NUOVO, con l'ambiente del prodotto.

    ⚠️ Le variabili tolte qui sotto sono la ragione d'essere della fixture, e
    ognuna ha una storia:

    * ``HIPPO_EMBEDDING_MODEL`` / ``_DIM`` — i pin della suite (conftest.py:11).
      Restando, questo file misurerebbe L12/384 invece di e5/768.
    * ``HIPPO_ENCODE_DELEGATE_ONLY`` — se ereditato, i fatti entrano **senza
      vettore** e il recall cade su keyword: il 2026-08-21 dava «13 failed, 3
      passed», e passavano le sole lingue lessicalmente vicine all'italiano. Un
      test cross-lingua che misura la coincidenza delle parole è precisamente
      ciò che questo file esiste per impedire. (conftest.py:137 documenta dal
      2026-06-06 che un ``mcp_server.main()`` in-process lo fa leakare
      permanentemente nell'ambiente.)

    ``HF_HUB_OFFLINE=1`` invece resta ACCESO di proposito: il presidio non deve
    scaricare 1.1 GB di nascosto durante una suite. Se il modello non c'è il
    test deve FALLIRE dicendo di eseguire ``verimem warmup`` — non skippare: uno
    skip verrebbe contato fra i verdi e nasconderebbe un warmup che non ha
    funzionato, che è esattamente il difetto scoperto il 2026-08-21.
    """
    cartella = tmp_path_factory.mktemp("multilingue")
    script = cartella / "giro.py"
    script.write_text(
        "MARCATORE = " + repr(_MARCATORE) + "\n" + _SCRIPT, encoding="utf-8")

    env = dict(os.environ)
    # ⚠️ PER SUFFISSO, NON PER NOME INTERO — e non è pedanteria, è il difetto
    # che questo file ha avuto per venti minuti il 2026-08-21. `_compat.py:136`
    # PROPAGA ogni `HIPPO_*` sui gemelli `ENGRAM_*` e `VERIMEM_*` all'import di
    # `verimem.config`, dentro il processo pytest. Misurato::
    #
    #     PRIMA import: {'HIPPO_EMBEDDING_MODEL': 'PIN-DI-PROVA'}
    #     DOPO  import: {'HIPPO_...', 'ENGRAM_...', 'VERIMEM_...'}
    #
    # Togliendo il solo `HIPPO_`, il figlio RICOSTRUIVA il pin dagli alias
    # superstiti e misurava di nuovo L12. Un elenco di nomi interi va aggiornato
    # ogni volta che nasce un prefisso; il suffisso li prende tutti e tre, e
    # anche il quarto.
    for chiave in [k for k in env
                   if k.endswith(("EMBEDDING_MODEL", "EMBEDDING_DIM",
                                  "ENCODE_DELEGATE_ONLY"))]:
        env.pop(chiave, None)
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR",
                  "ENGRAM_DIR"):
        env[alias] = str(cartella)
    env["ENGRAM_ENCODE_SERVICE"] = "0"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"

    esito = subprocess.run(
        [sys.executable, str(script), str(cartella),
         json.dumps(FATTI_IT), json.dumps(DOMANDE), json.dumps(FUORI_TEMA)],
        capture_output=True, text=True, timeout=900, env=env)

    riga = next((r for r in esito.stdout.splitlines()
                 if r.startswith(_MARCATORE)), None)
    if riga is None:
        manca = "LocalEntryNotFoundError" in esito.stderr
        pytest.fail(
            "il giro multilingue non ha prodotto un risultato"
            + (" — IL MODELLO DEL PRODOTTO NON È IN CACHE: esegui "
               "`verimem warmup --no-daemon` (in CI è il passo «Warm embedding "
               "model»). Questo test non scarica da solo, di proposito."
               if manca else "")
            + f"\nrc={esito.returncode}"
            f"\nstdout:\n{esito.stdout[-2000:]}"
            f"\nstderr:\n{esito.stderr[-3000:]}")
    return json.loads(riga[len(_MARCATORE):])


def test_CONTROLLO_il_giro_e_sul_modello_DEL_PRODOTTO(giro_multilingue):
    """Il controllo che rende non-vuoti i sedici test qui sotto.

    Senza di lui, il giorno in cui il subprocess tornasse a ereditare il pin
    della suite (una riga in più nel conftest, un ``env`` copiato male) tutti
    gli altri resterebbero verdi — misurando l'encoder sbagliato in silenzio.
    Che è esattamente quello che è successo fino al 2026-08-21.
    """
    from verimem.config import CONFIG as CONFIG_SOTTO_PYTEST

    modello = giro_multilingue["modello"]
    assert modello != CONFIG_SOTTO_PYTEST.embedding_model, (
        f"il giro ha usato {modello}, cioe' lo stesso modello che la SUITE "
        "pinna: questo file sta misurando un encoder che il prodotto non "
        "consegna.\nHIPPO_EMBEDDING_MODEL come il FIGLIO l'ha visto: "
        f"{giro_multilingue.get('pin_ereditato')!r} — se non e' None, il pin e' "
        "stato ereditato nonostante l'env.pop della fixture; se e' None, e' il "
        "DEFAULT del prodotto ad essere tornato uguale a quello della suite")
    assert giro_multilingue["dim"] == 768, (
        f"dim {giro_multilingue['dim']}: il prodotto usa 768 (e5-base). Se il "
        "default e' cambiato davvero, aggiorna i punteggi del docstring "
        "RIMISURANDO, non questo numero")


@pytest.mark.parametrize("lingua,domanda", DOMANDE)
def test_una_domanda_in_qualunque_lingua_trova_il_fatto_italiano(
        giro_multilingue, lingua, domanda):
    """IL CUORE: i fatti sono in italiano, la domanda no, la risposta è giusta."""
    esito = giro_multilingue["esiti"][lingua]
    assert esito["testo"], f"[{lingua}] nessun risultato per «{domanda}»"
    assert "quattordici" in esito["testo"], (
        f"[{lingua}] risposta sbagliata: {esito['testo'][:60]}")


@pytest.mark.parametrize("lingua,domanda", DOMANDE)
def test_e_la_SEPARA_da_una_domanda_fuori_tema(giro_multilingue, lingua, domanda):
    """IL PRESIDIO CHE SERVE DAVVERO — ed è la SEPARAZIONE, non il punteggio.

    Il test sopra passerebbe anche con un ranking casuale: con k=1 su quattro
    fatti, azzeccarla è un colpo su quattro. Serve sapere che il modello ha
    CAPITO la domanda invece di indovinarla.

    ⚠️ E NON CON UNA SOGLIA ASSOLUTA, che è la prima stesura di questo test ed
    era sbagliata: chiedeva ``score >= 0.75`` sulla scorta dei valori misurati
    a mano (0.82-0.89), e sotto pytest usciva 0.7006. Non era il modello — era
    che **fuori da pytest gira il rerank** (``{"rerank": "applied"}``) e dentro
    no, quindi la soglia misurava quali STADI del ranking sono attivi, non se
    il retrieval è multilingue. Due misure della stessa cosa divergevano, e la
    costruita male era la mia.

    La separazione invece non dipende dagli stadi: qualunque configurazione dia
    i punteggi, la domanda in tema deve stare SOPRA quella fuori tema nella
    stessa lingua. Se un giorno una lingua smette di separare, lì il
    multilingue si è rotto davvero.
    """
    esito = giro_multilingue["esiti"][lingua]
    assert esito["score"] > esito["score_fuori_tema"], (
        f"[{lingua}] in tema {esito['score']} NON supera fuori tema "
        f"{esito['score_fuori_tema']}: in questa lingua il modello non sta "
        "capendo la domanda")
