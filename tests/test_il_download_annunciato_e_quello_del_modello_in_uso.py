"""Il comando annuncia la taglia DEL MODELLO CHE STA PER SCARICARE.

Il difetto curato: `verimem warmup` diceva «first run downloads ~440 MB» per un
modello che, misurato su una cache vuota, ne scarica **1082**. Chi installava
sentiva 440 MB e ne riceveva 1,1 GB — e la stessa cifra sbagliata era ripetuta
in quattro punti fra prodotto, esempi e collaudi.

⚠️ Perché questo collaudo non ripete quello che esiste già.
`test_il_costo_dichiarato_e_lo_stesso_ovunque` presidia la taglia del GIUDICE e
dichiara onestamente il proprio limite: *«la dimensione di un file remoto non è
nel codice, quindi verifica che le copie coincidano fra loro»*. È vero, ed è
esattamente il buco che ha lasciato passare questo difetto: **quattro copie
coerenti fra loro possono essere coerentemente sbagliate**, e restano verdi.

Qui il legame è un altro: la cifra è appesa al **nome del modello**. Cambiare
`_DEFAULT_EMBEDDING_MODEL` senza misurare il nuovo rende questo collaudo ROSSO,
mentre un presidio di sola coerenza resterebbe verde — che è il caso in cui il
prodotto comincia a mentire senza che nessun test se ne accorga.

📌 Ciò che resta fuori, dichiarato: la misura stessa (1082 MB) non è
riproducibile in CI — richiede una cache HF vuota e la rete. È registrata nel
codice con data, piattaforma e metodo. Questo collaudo garantisce che la cifra
ANNUNCIATA sia quella MISURATA per quel modello, non che la misura sia giusta.
"""
from __future__ import annotations

import re
from pathlib import Path

from verimem.cli import _EMBEDDER_DOWNLOAD_MB
from verimem.config import _DEFAULT_EMBEDDING_MODEL, CONFIG

RADICE = Path(__file__).resolve().parent.parent

#: Le superfici che annunciano la taglia dell'embedder a chi legge.
#: I verbali sotto `docs/stato-reale/` sono ESCLUSI di proposito: registrano
#: l'output osservato in un momento preciso, e riscriverli falsificherebbe un
#: registro invece di curare un difetto.
SUPERFICI = (
    "verimem/cli.py",
    "examples/sdk_quickstart.py",
    "tests/test_cli_warmup.py",
    "scripts/bench_e5_dense.py",
)

#: «~1.1 GB», «1.1GB», «~440 MB» — cattura numero e unità, non la formattazione.
_TAGLIA = re.compile(r"~?\s*(?P<n>\d+(?:\.\d+)?)\s*(?P<u>GB|MB)\b", re.IGNORECASE)

#: Solo le righe che parlano DELL'EMBEDDER: le stesse superfici nominano anche
#: il giudice (656 MB), che ha il suo presidio e non va confuso con questo.
_PARLA_DELL_EMBEDDER = re.compile(r"e5-base|embedding model|embedder", re.IGNORECASE)


def _cifre_annunciate(percorso: Path) -> list[float]:
    """Le taglie in MB che quel file annuncia per l'embedder."""
    trovate: list[float] = []
    for riga in percorso.read_text(encoding="utf-8", errors="replace").splitlines():
        if riga.lstrip().startswith("#:"):
            continue          # il commento che documenta la tabella e il difetto
        if not _PARLA_DELL_EMBEDDER.search(riga):
            continue
        for m in _TAGLIA.finditer(riga):
            n = float(m.group("n"))
            trovate.append(n * 1024 if m.group("u").upper() == "GB" else n)
    return trovate


def test_il_modello_in_uso_ha_una_misura():
    """Il legame che il presidio di sola coerenza non ha.

    Se qualcuno cambia il modello e non lo misura, il comando non deve poter
    continuare ad annunciare la cifra del modello precedente.
    """
    assert _DEFAULT_EMBEDDING_MODEL in _EMBEDDER_DOWNLOAD_MB, (
        f"`_DEFAULT_EMBEDDING_MODEL` è {_DEFAULT_EMBEDDING_MODEL!r} ma nessuno ha "
        f"misurato quanto scarica: la tabella conosce {sorted(_EMBEDDER_DOWNLOAD_MB)}. "
        f"Misurare su una cache HF vuota e aggiungere la voce — NON copiare la "
        f"cifra del modello precedente, che è il difetto che questo collaudo esiste "
        f"per impedire.")


def test_le_superfici_annunciano_la_cifra_misurata():
    """Nessuna superficie può annunciare una taglia diversa da quella misurata."""
    atteso = _EMBEDDER_DOWNLOAD_MB[_DEFAULT_EMBEDDING_MODEL]
    divergenti, viste = {}, 0
    for nome in SUPERFICI:
        p = RADICE / nome
        if not p.exists():
            continue
        for mb in _cifre_annunciate(p):
            viste += 1
            # tolleranza: «~1.1 GB» è 1126.4 MB contro 1082 misurati
            if abs(mb - atteso) > atteso * 0.10:
                divergenti.setdefault(nome, []).append(mb)

    assert viste, (
        "nessuna superficie annuncia più la taglia dell'embedder: o è sparita "
        "— e allora chi installa non sa più cosa sta per scaricare — o la forma "
        "è cambiata e questo collaudo va riscritto, non cancellato")
    assert not divergenti, (
        f"queste superfici annunciano una taglia che non è quella misurata "
        f"({atteso} MB per {_DEFAULT_EMBEDDING_MODEL}): {divergenti}")


def test_un_modello_non_misurato_non_eredita_la_cifra_di_un_altro():
    """«Non l'ho misurato» e «pesa N» sono due risposte diverse.

    È la regola che il prodotto già enuncia per gli allarmi in
    `review_queue.threshold`: un valore mancante non deve diventare in silenzio
    il valore di qualcun altro.
    """
    ignoto = "una/rete-mai-misurata"
    assert ignoto not in _EMBEDDER_DOWNLOAD_MB
    assert _EMBEDDER_DOWNLOAD_MB.get(ignoto) is None, (
        "un modello sconosciuto deve dare None — è quel None che fa dire al "
        "comando «size not measured», invece di annunciare la cifra di un altro")


def test_il_criterio_riconoscerebbe_il_difetto(tmp_path):
    """Controllo positivo: col testo di prima, il collaudo deve diventare rosso."""
    finto = tmp_path / "prima.py"
    finto.write_text(
        '    console.print("Warming embedding model — first run downloads ~440 MB")\n',
        encoding="utf-8")
    cifre = _cifre_annunciate(finto)
    assert cifre == [440.0], f"il criterio non legge più la cifra annunciata: {cifre}"
    atteso = _EMBEDDER_DOWNLOAD_MB[_DEFAULT_EMBEDDING_MODEL]
    assert abs(cifre[0] - atteso) > atteso * 0.10, (
        "col vecchio valore il collaudo resterebbe verde: sarebbe un guardiano "
        "che non guarda")


def test_la_tabella_non_e_vuota():
    """Tiene onesti i due sopra: a tabella vuota sarebbero veri e vuoti."""
    assert _EMBEDDER_DOWNLOAD_MB, "la tabella delle misure è vuota"
    for nome, mb in _EMBEDDER_DOWNLOAD_MB.items():
        assert mb > 0, f"{nome} dichiara una taglia di {mb} MB"


def test_il_banco_non_gira_sul_modello_del_prodotto():
    """La trappola che questo collaudo ha scoperto scrivendosi, resa visibile.

    `tests/conftest.py` imposta `HIPPO_EMBEDDING_MODEL` su un MiniLM per non
    scaricare un e5-base a ogni esecuzione. È una scelta giusta e ha un prezzo:
    **sotto pytest `CONFIG.embedding_model` NON è il modello del prodotto.**

    Chi scrive un collaudo leggendo `CONFIG` misura l'ambiente del banco e crede
    di misurare il prodotto — la prima stesura di questo file lo faceva, ed è
    diventata rossa per una ragione ambientale invece che per un difetto.

    Questo test non chiede di cambiare nulla: **fa fallire chi allinea i due
    valori senza accorgersene**, così la differenza resta un fatto dichiarato e
    non una sorpresa.
    """
    assert CONFIG.embedding_model != _DEFAULT_EMBEDDING_MODEL, (
        "sotto pytest il modello coincide con quello del prodotto: se è stato "
        "voluto, questo collaudo va aggiornato; se è successo per caso, ogni "
        "esecuzione della suite ora scarica il modello grande")
