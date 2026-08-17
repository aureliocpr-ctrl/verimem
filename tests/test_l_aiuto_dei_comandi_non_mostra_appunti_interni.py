"""L'aiuto che `--help` stampa non contiene la storia interna del comando.

Typer usa `help=` del decoratore quando c'è e il docstring quando manca. I
docstring di `cli.py` portano — legittimamente — la storia del comando: la data
in cui un difetto fu misurato, i numeri, il modulo che lo conteneva. Serve a chi
mantiene il comando; non a chi lo esegue. Senza `help=` esplicito finisce sotto
gli occhi di chi ha appena installato il pacchetto.

    verimem tiers --help  ->  "Il 2026-08-05 le cinque tabelle delle entità
                               dentro semantic.db ... sono state scambiate
                               per il tier"

Questo collaudo **replica la regola di Typer** invece di leggere i docstring: il
primo misuratore guardava il sorgente e dava lo stesso numero prima e dopo la
cura, perché la cura lascia i docstring dove sono. Il livello a cui si misura
decide il verdetto, e il livello giusto qui è ciò che viene stampato.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
CLI = RADICE / "verimem" / "cli.py"

#: Marcatori di materiale interno. Ognuno è una cosa che un utente non ha modo
#: di usare: quando è stato misurato un difetto, dove sta la riga che lo
#: conteneva, quale commit lo curò, quale ciclo di lavoro lo scoprì.
_INTERNI = {
    "data": re.compile(r"\b20\d\d-\d\d-\d\d\b"),
    "file:riga": re.compile(r"\b\w+\.py:\d+"),
    "commit": re.compile(r"\b[0-9a-f]{7,12}\b"),
    # `#?` non è un dettaglio: senza, «Cycle #145» passa e «cycle 145» no. Il buco
    # l'ha trovato il controllo positivo qui sotto, prima che il file fosse committato.
    "ciclo/misura": re.compile(r"\b(?:Cycle\s*#?\d|misurat|scoperto|si vedeva)", re.IGNORECASE),
}

#: Parole funzione italiane che l'inglese non ha. Il prodotto è pubblicato in
#: inglese: un aiuto in italiano non è un errore di battitura, è una superficie
#: che parla una lingua che chi installa non ha scelto.
_ITALIANO = re.compile(
    r"\b(?:il|lo|la|del|della|che|non|per|con|come|quante|piu|più|gia|già|"
    r"solo|ogni|dove|sono|viene|senza|una|un)\b", re.IGNORECASE)


def _aiuti_stampati() -> dict[str, str]:
    """Per ogni comando, il testo che Typer mostra: `help=` se c'è, altrimenti il docstring."""
    albero = ast.parse(CLI.read_text(encoding="utf-8", errors="replace"))
    aiuti: dict[str, str] = {}
    for nodo in ast.walk(albero):
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in nodo.decorator_list:
            testo = ast.unparse(dec)
            if ".command(" not in testo and ".callback(" not in testo:
                continue
            esplicito = None
            if isinstance(dec, ast.Call):
                esplicito = next(
                    (kw.value.value for kw in dec.keywords
                     if kw.arg == "help" and isinstance(kw.value, ast.Constant)), None)
            aiuti[nodo.name] = esplicito if esplicito is not None else (
                ast.get_docstring(nodo) or "")
            break
    return aiuti


def test_nessun_aiuto_stampa_materiale_interno():
    """Date, righe di file, commit e cicli di lavoro non arrivano a chi digita --help."""
    colpiti = {}
    for nome, aiuto in _aiuti_stampati().items():
        trovati = {k: rx.findall(aiuto)[:3] for k, rx in _INTERNI.items() if rx.search(aiuto)}
        if trovati:
            colpiti[nome] = trovati
    assert not colpiti, (
        f"questi comandi stampano materiale di sviluppo a chi li esegue: {colpiti}. "
        f"La cura NON è accorciare il docstring — quella storia serve a chi mantiene il "
        f"comando — ma dichiarare `help=\"...\"` sul decoratore, che Typer usa al suo posto.")


def test_nessun_aiuto_e_in_italiano():
    """Il pacchetto è pubblicato in inglese: l'interfaccia parla una lingua sola."""
    italiani = {}
    for nome, aiuto in _aiuti_stampati().items():
        prima = aiuto.strip().splitlines()[0] if aiuto.strip() else ""
        parole = set(w.lower() for w in _ITALIANO.findall(prima))
        if len(parole) >= 2:
            italiani[nome] = sorted(parole)[:4]
    assert not italiani, (
        f"l'aiuto di questi comandi è in italiano: {italiani}. Il resto della CLI è in "
        f"inglese, e chi installa dal registro pubblico non ha scelto l'italiano.")


def test_ogni_comando_ha_un_aiuto():
    """Un comando senza aiuto è invisibile a chi non ne conosce già il nome."""
    muti = [n for n, a in _aiuti_stampati().items() if not a.strip()]
    assert not muti, (
        f"questi comandi non dicono cosa fanno: {muti}. Compaiono nel listato senza "
        f"descrizione, quindi li usa solo chi sa già che esistono.")


def test_il_criterio_riconosce_un_aiuto_sporco():
    """Il controllo positivo: senza, «nessun comando colpito» sarebbe vero e vuoto."""
    finto = ("Force a sleep cycle now.\n\n"
             "Cycle #145 rename: moved here on 2026-08-05, see semantic.py:5212.")
    trovati = {k for k, rx in _INTERNI.items() if rx.search(finto)}
    assert {"data", "file:riga", "ciclo/misura"} <= trovati, (
        f"il criterio non riconosce più il materiale interno: su un aiuto che contiene "
        f"data, riferimento a riga e ciclo ha trovato solo {trovati}")
