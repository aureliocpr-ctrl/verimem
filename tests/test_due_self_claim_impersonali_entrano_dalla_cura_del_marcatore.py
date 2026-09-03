"""🔴 ROSSO VOLUTO: due self-claim impersonali entrano, e devono essere fermate.

Questo file e' ROSSO su `main` di proposito, per decisione presa il 2026-09-03
alle 19:45 dopo uno spot-check indipendente. Non e' un `xfail`: un `xfail` qui
dichiarerebbe ACCETTABILE che «La funzionalita' funziona ed e' verificata»
entri servibile in memoria, che e' la cosa che questo prodotto esiste per
impedire.

━━ COME CI SIAMO ARRIVATI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
La cura `c857752e` (30/08, `subject_extract.py`) allarga il marcatore di verbo,
cosi' piu' soggetti leggono come third-party e L1 escala di meno. La cura
DICHIARO' questo rischio prima di misurarlo e lo misuro' su 13.662 fatti vivi:
132 diventano DOMAIN, 0 lo perdono, e dei 132 **nessuno e' in prima persona**.

Il controllo guardava la popolazione che la cura CAMBIA. Misurata quella che la
garanzia PROTEGGEVA (A/B fra padre e figlio sulle stesse 17.428 proposizioni
del corpus vivo): dei 4.649 trattenuti dal padre, il figlio ne libera **15**.
Lo 0,32% sembra innocuo; l'elenco no.

🔑 PERCHE' IL CONTROLLO NON POTEVA VEDERLE: chiedeva «sono in PRIMA PERSONA?».
Nessuna delle due lo e'. «La funzionalita' funziona», «l'implementazione e'
finita» sono IMPERSONALI — ed e' la forma normale della self-claim in italiano.
Il proxy («prima persona») non era la grandezza («self-claim»).

━━ E IL FILE FISSA ENTRAMBI I LATI, DI PROPOSITO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Una cura che rimettesse tutto come prima riporterebbe il difetto che `c857752e`
era nata per curare — e che il 28/08 costava 6 fatti veri su 7 fermati su un
verbale d'ufficio. Percio' qui stanno anche due fatti di TERZI VERI che oggi
sono ammessi e che devono RESTARE ammessi: se la riparazione li rifa' cadere,
queste due celle diventano rosse e lo dicono subito.

    da FERMARE (rosse oggi)   «La funzionalita' funziona ed e' verificata.»
                              «L'implementazione e' finita e collaudata.»
    da NON fermare (verdi)    una misura con gli orari, una descrizione di layer
    controllo (verde)         «La migrazione e' completata e tutti i test passano.»

⚡ Nessun modello: `ground_write=False`, la famiglia L1 e' lessicale. Il difetto
non dipende dal giudice — misurato: con e senza giudice il fatto entra uguale.

Vicini: `docs/stato-reale/banchi/ws3-la-popolazione-che-la-garanzia-proteggeva.py`
(l'A/B completo, con i comandi per rifarlo).
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate

#: le due liberate che sono self-claim: nessun soggetto terzo, nessuna
#: evidenza, e il claim parla dello stato del lavoro di chi scrive
SELF_CLAIM_IMPERSONALI = [
    "La funzionalita' funziona ed e' verificata.",
    "L'implementazione e' finita e collaudata.",
]

#: due fatti di TERZI veri, presi dallo stesso insieme di 15: descrivono cio'
#: che e' stato osservato, con i dati per controllarlo. Sono il GUADAGNO della
#: cura e non devono tornare a cadere.
TERZI_VERI = [
    "Il comando warmup e' iniziato alle 14:50:24 ed e' finito alle 14:53:19.",
    "Il layer che quarantina la frase e' L1.18 con reason "
    "Automation claim schedulato lacks scheduler evidence.",
]

#: resta fermato sia prima sia dopo la cura: senza, non si distingue questo
#: difetto da un guasto generale del gate
CONTROLLO = "La migrazione e' completata e tutti i test passano."


def _esito(frase: str) -> tuple[bool, list[str]]:
    """(e' fermata?, quali layer si sono accesi) — dalla PORTA del prodotto."""
    g = run_validation_gate(proposition=frase, verified_by=[], topic=None,
                            agent=None, source=None, ground_write=False)
    layer = [str((w or {}).get("layer") or "")
             for w in (getattr(g, "warnings", None) or [])]
    return getattr(g, "action", None) in ("downgrade", "reject"), layer


@pytest.mark.parametrize("frase", SELF_CLAIM_IMPERSONALI)
def test_una_self_claim_impersonale_deve_essere_fermata(frase):
    """🔴 ROSSA OGGI. Verde quando la cura del marcatore sara' ripensata."""
    fermata, layer = _esito(frase)
    assert fermata, (
        f"{frase!r} entra servibile. I layer si accendono comunque ({layer}) e "
        "l'azione e' `persist`: il gate nomina cio' che ha visto e lascia "
        "passare. Al commit padre `ccab08b4` questa frase era fermata."
    )


def test_CONTROLLO_una_self_claim_esplicita_e_ancora_fermata():
    """Il righello: senza, le due celle sopra misurerebbero un gate rotto."""
    fermata, layer = _esito(CONTROLLO)
    assert fermata, (
        f"anche {CONTROLLO!r} entra ({layer}): non e' la cura del marcatore, "
        "e' il gate che non trattiene piu' nulla — allargare la misura"
    )


@pytest.mark.parametrize("frase", TERZI_VERI)
def test_un_fatto_di_terzi_vero_resta_ammesso(frase):
    """L'altro lato: la riparazione non deve ricomprare il difetto del 28/08.

    Se questa cella diventa rossa, chi ha riparato ha ristretto troppo e i
    fatti veri di terzi ricominciano a cadere — che e' il difetto misurato il
    28/08 (6 fatti veri su 7 fermati su un verbale d'ufficio).
    """
    fermata, layer = _esito(frase)
    assert not fermata, (
        f"{frase!r} ora e' fermata ({layer}): la riparazione ha ristretto "
        "troppo e riporta il difetto che `c857752e` curava"
    )
