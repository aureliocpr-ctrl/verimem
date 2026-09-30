"""Il warm del giudice deve caricare ANCHE le librerie che `scipy.linalg` non
trascina — altrimenti la prima scrittura le importa mentre serve, e non torna.

⚠️ PERCHE' QUESTO FILE ESISTE, ed e' il pezzo che mancava a T1b.

`_scalda_le_librerie_del_giudice` importa `scipy.linalg`, che TRASCINA
`numpy.random` (presidiato da test_il_preload_carica_anche_numpy_random.py). Con
il daemon SPENTO quel warm basta: 3 giri su 3. Con il daemon ACCESO — il caso
dell'applicazione — non basta, misurato alla porta MCP vera il 17/09::

    demone ACCESO, senza questo warm:  chiamata 1  180.35 s  SCADUTO, store 0
    demone ACCESO, con  questo warm:   chiamata 1   33.90 s, chiamata 2 0.41 s
                                       scritture riuscite 2 su 2

La ragione sta nella catena della richiesta: `transformers` -> `sklearn` ->
`scipy`, e `sklearn` non e' fra cio' che `scipy.linalg` tira dentro. Quindi la
richiesta trova ancora qualcosa da importare, e l'import di un'estensione C
mentre una richiesta e' in corso non finisce (ipotesi: loader lock di Windows;
misurato: 0,3% di CPU per tutta l'attesa).

🔑 IL PREZZO E' PARTE DELLA CURA, e la terza cella lo presidia. Misurato::

    transformers.generation.utils DA SOLO:  20.6 -> 769.4 MB   (+748,8)
    i cinque di qui                      :  20.7 -> 141.5 MB   (+120,8)

Curare allargando fino a `transformers` costerebbe 626 MB in piu' per ogni
processo che apre il server, anche a chi legge soltanto. E' stato rifiutato: la
cella 3 fa cadere il banco se qualcuno ce lo rimette per far passare un rosso.

⚠️ OGNI CELLA GIRA IN UN SUBPROCESS PULITO: dentro pytest `sklearn` e `scipy`
sono quasi certamente gia' importati da qualcun altro, e la misura direbbe
sempre True — un verde che non vale niente.
"""
from __future__ import annotations

import json
import subprocess
import sys

#: Quelli che il warm deve garantire. `scipy.linalg` non e' qui: e' gia'
#: presidiato altrove, e ripeterlo direbbe che il banco copre piu' di quanto fa.
ATTESI = (
    "scipy.special",
    "scipy.interpolate",
    "scipy.optimize",
    "scipy.stats",
    "sklearn.utils.validation",
)

#: Quelli che il warm NON deve tirare dentro: sono il 85% del prezzo.
VIETATI = ("torch", "transformers")


def _in_un_processo_pulito(codice: str) -> dict:
    """Esegue `codice` in un interprete nuovo e ne legge il JSON finale."""
    p = subprocess.run([sys.executable, "-c", codice], capture_output=True,
                       text=True, timeout=600)
    assert p.returncode == 0, f"il sottoprocesso e' uscito con {p.returncode}: {p.stderr[-800:]}"
    ultima = [r for r in p.stdout.strip().splitlines() if r.startswith("{")]
    assert ultima, f"nessun JSON nello stdout: {p.stdout[-400:]} / {p.stderr[-400:]}"
    return json.loads(ultima[-1])


def test_controllo_positivo_il_banco_vede_la_differenza():
    """PRIMA del warm nessuno dei cinque c'e'. Senza questa cella, un verde
    della prossima non proverebbe niente: potrebbero esserci gia'."""
    r = _in_un_processo_pulito(
        "import sys, json\n"
        "import verimem.preload  # il modulo, non il warm\n"
        f"print(json.dumps({{m: m in sys.modules for m in {ATTESI!r}}}))\n")
    assert not any(r.values()), (
        f"qualcuno era gia' importato prima del warm: {r}. Il banco non "
        f"distingue piu' il prima dal dopo.")


def test_il_warm_carica_quelli_che_questa_macchina_puo_importare():
    """IL CUORE, e la condizione e' scritta apposta cosi'.

    scikit-learn NON e' una dipendenza dichiarata (pyproject.toml porta scipy,
    non scikit-learn): dove non c'e', il warm lo salta — ed e' giusto, e'
    best-effort — e pretendere che ci sia rende il banco verde da chi sviluppa
    e rosso in CI. Misurato: test (ubuntu-latest / py3.12) rosso al primo giro
    esattamente per questo.

    La pretesa e' quindi: ogni modulo che QUESTA macchina puo' importare
    dev'essere gia' caricato dopo il warm. Dove sklearn manca, manca anche
    dalla catena della richiesta (transformers -> sklearn -> scipy), e non c'e'
    niente da curare.

    E LA CELLA NON PUO' PASSARE A VUOTO: se questa macchina non potesse
    importarne NESSUNO, l'elenco dei mancanti sarebbe vuoto e la cella verde
    senza aver misurato niente. Un banco muto non e' un banco verde: la prima
    pretesa lo fa cadere.
    """
    r = _in_un_processo_pulito(
        "import sys, json, importlib.util\n"
        "from verimem.preload import _scalda_le_librerie_del_giudice as w\n"
        "w()\n"
        f"m5 = {ATTESI!r}\n"
        "print(json.dumps({m: {'caricato': m in sys.modules,\n"
        "                      'installato': importlib.util.find_spec(\n"
        "                          m.split('.')[0]) is not None} for m in m5}))\n")
    installati = [m for m, v in r.items() if v["installato"]]
    mancanti = [m for m in installati if not r[m]["caricato"]]
    assert installati, (
        f"nessuno dei cinque e' installato qui: la cella non ha misurato "
        f"niente e non deve dirsi verde. Letto: {r}")
    assert not mancanti, (
        f"dopo il warm mancano ancora: {mancanti} (installati qui: "
        f"{installati}). La prima scrittura li importera' mentre serve, ed e' "
        f"li' che non torna: 180,35 s, zero fatti.")

def test_il_warm_non_si_porta_dietro_il_modello():
    """IL NEGATIVO CHE PRESIDIA IL PREZZO: +120,8 MB, non +746,9."""
    r = _in_un_processo_pulito(
        "import sys, json\n"
        "from verimem.preload import _scalda_le_librerie_del_giudice as w\n"
        "w()\n"
        f"print(json.dumps({{m: m in sys.modules for m in {VIETATI!r}}}))\n")
    entrati = [m for m, c in r.items() if c]
    assert not entrati, (
        f"il warm si e' portato dietro {entrati}: sono ~748,8 MB per ogni "
        f"processo che apre il server, anche per chi legge soltanto. Se "
        f"servono davvero, si cambia la nota — non il banco.")


def test_il_codice_importa_ESATTAMENTE_la_lista_dichiarata():
    """LA CELLA NEGATIVA, e ora e' strutturale invece che a runtime.

    Prima svuotavo la lista e guardavo che il warm non caricasse piu' niente.
    Non si puo' piu': dentro `lock_import()` ci vanno SOLO nodi Import (lo
    pretende test_ogni_import_pesante_passa_dal_lock) e `__import__` sta nella
    lista dei sink con eval ed exec (test_no_dangerous_sinks). Misurato in CI
    il 18/09, due rossi, e i due presidi avevano ragione.

    Quindi gli import sono scritti a mano, e il rischio diventa un altro: la
    lista dichiarata qui sopra e il codice che importa davvero possono
    DIVERGERE — due copie divergono sempre, e' la prima classe del registro.
    Questa cella legge l'AST della funzione e pretende che i due insiemi siano
    UGUALI: chi toglie un import fa cadere il banco, e chi ne aggiunge uno non
    dichiarato pure.

    NESSUN IMPORT VERO QUI: si legge il sorgente, non si esegue.
    """
    import ast
    import inspect
    import textwrap

    from verimem import preload

    albero = ast.parse(textwrap.dedent(
        inspect.getsource(preload._scalda_le_librerie_del_giudice)))
    importati = {
        alias.name
        for nodo in ast.walk(albero) if isinstance(nodo, ast.Import)
        for alias in nodo.names
    }
    atteso = {"scipy.linalg"} | set(ATTESI)
    assert importati == atteso, (
        f"il codice e la lista dichiarata non dicono la stessa cosa.\n"
        f"  importa ma non e' dichiarato: {sorted(importati - atteso)}\n"
        f"  dichiarato ma non importato : {sorted(atteso - importati)}")
