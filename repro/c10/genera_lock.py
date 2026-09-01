"""Il lock minimo del repro-pack C10 — e la riga che conta NON viene dai metadati.

⚠️ REPERTO 02/09 00:20, che questo script esiste per non ripetere:
`importlib.metadata.version("verimem")` dice **0.7.0** su questa macchina,
mentre il codice che il processo ESEGUE e' **0.7.6**, importato dal working
tree. I metadati descrivono cio' che e' stato INSTALLATO, non cio' che verra'
importato — e con un checkout attivo sul path le due cose divergono.

⇒ Un lock e' precisamente cio' su cui si fa affidamento per riprodurre: uno che
sbaglia la versione del pacchetto principale e' PEGGIO di nessun lock. Per
verimem si legge `__version__` e si stampa anche il PATH, cosi' chi legge vede
da dove arriva. Per le altre dipendenze i metadati vanno bene: non sono su un
checkout.

`importlib.metadata.version` non importa il modulo, quindi torch e transformers
non vengono caricati: costa millisecondi e non contende i 758 MB del giudice.
"""
import platform
import sys
from importlib.metadata import PackageNotFoundError, version

ALTRE = [
    "torch",            # caricato da make_finetuned_scorer
    "transformers",     # AutoModelForSequenceClassification, AutoTokenizer
    "tokenizers",
    "safetensors",      # i pesi del giudice sono model.safetensors
    "numpy",
    "sentence-transformers",
    "huggingface-hub",
]

print("# repro-pack C10 — lock minimo")
print("# generato leggendo i metadati installati, SENZA importare i moduli")
print(f"python=={platform.python_version()}   # {sys.platform}")

#: --- verimem: dal codice, non dai metadati (vedi il docstring) ---
try:
    import verimem
    eseguita = getattr(verimem, "__version__", "(nessun __version__)")
    dove = getattr(verimem, "__file__", "(ignoto)")
except Exception as e:                       # noqa: BLE001
    eseguita, dove = f"(import fallito: {e})", "(ignoto)"
try:
    installata = version("verimem")
except PackageNotFoundError:
    installata = "(non installato)"
print(f"verimem=={eseguita}   # ESEGUITA, da {dove}")
if str(installata) != str(eseguita):
    print(f"# ⚠️  i METADATI installati dicono {installata}: diverso da cio' che gira.")
    print("#    Chi riproduce deve installare la versione ESEGUITA, non quella dei")
    print("#    metadati — e se non e' su PyPI, dal sorgente al commit dichiarato.")

for p in ALTRE:
    try:
        print(f"{p}=={version(p)}")
    except PackageNotFoundError:
        print(f"# {p}: NON INSTALLATO in questo ambiente")
