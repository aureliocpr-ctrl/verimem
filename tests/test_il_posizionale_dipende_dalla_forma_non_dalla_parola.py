"""Il criterio posizionale copre una FORMA di frase, non un vocabolario di parole.

`_GENERIC_INDEX_RE` è nato con una promessa scritta accanto a sé:

    "sends message 0/1/2", "stores profile 0/1/2", "computes rate 0/1/2" —
    SEVEN were retired, because message/profile/rate were not listed.
    A vocabulary cannot be enumerated; a position can be read.

Questo banco misura quanto di quella promessa regge. Misurato il 2026-08-20 su
worktree fermi (`7d3e97a7`, `8ab59e62`, `d3e6597c`), 8 forme di frase × 6 parole
che non stanno in NESSUNO dei tre elenchi:

    tutte e sei le parole:  SI  no  no  no  SI  SI  no  no     <- identico
    copertura: 3 forme su 8, cioè 18 celle su 48

⇒ La parola non conta: conta se dopo il numero c'è fine-frase o una parola
  funzionale. Appena segue una parola di CONTENUTO (`open`, `yesterday`,
  `failed`, `aperto`, `ieri`) l'estrattore la legge come unità di misura, il
  numero smette di essere «bare» e il ramo posizionale viene scartato.

⚠️ GLI ELENCHI SONO TRE, e questo banco lo presidia perché costa un'ora
scoprirlo — chi ne guarda uno solo conclude «non è il vocabolario» mentre la
causa è un altro elenco:

    _ETICHETTE_RECORD    anti_confab_gate.py   le etichette di record
    _EVENT_INDEX_RE      quantity_match.py     ~55 voci dell'estrattore
    _ATTRIBUTI_NUMERATI  anti_confab_gate.py   la guardia opposta

`sprint` e `lotto` stanno solo nel secondo, `message` solo nel primo, `rate` e
`profile` sono state aggiunte al terzo il 2026-08-20. Misurato lo stesso giorno:
«The tracker shows sprint 0 open.» dà un indice e «... rate 0 open.» no, frase
identica — la differenza era in quale elenco stava la parola, non nel criterio.

📌 LIVELLO DICHIARATO: qui si misura `event_indices`, cioè il criterio. Che il
verdetto regga anche alla porta del prodotto è stato misurato a parte lo stesso
giorno (`Memory.add` + `count` su `8ab59e62`): «The tracker shows rate 0/1/2
open.» dava 1 fatto vivo su 3, «...sprint 0/1/2...» ne dava 3. Non si rifà qui
perché caricherebbe l'embedder in una suite che deve restare veloce.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import _ATTRIBUTI_NUMERATI, _ETICHETTE_RECORD
from verimem.quantity_match import _EVENT_INDEX_RE, event_indices

#: Parole scelte per una ragione sola: non stanno in nessuno dei tre elenchi.
#: Se una ci finisce, il banco smette di misurare il posizionale e misura la
#: lista — per questo il controllo qui sotto è il primo test del file. È già
#: successo: la prima stesura usava `rate` e `profile`, che erano entrate in
#: `_ATTRIBUTI_NUMERATI` dieci minuti prima, e il controllo di allora guardava
#: due elenchi su tre, quindi non le vedeva.
PAROLE = ("widget", "gadget", "bucket", "crate", "tenant", "cluster")

#: Le forme in cui il numero resta «bare»: fine frase, oppure una parola che
#: `_NON_UNIT_WORDS` conosce come funzionale (`for`).
FORME_COPERTE = (
    "The tax module computes {p} {n}.",
    "The plan uses {p} {n} for billing.",
    "Il modulo calcola {p} {n}.",
)

#: Le forme in cui una parola di CONTENUTO segue il numero. Sono frasi normali,
#: non casi limite: è come si scrive un registro in inglese e in italiano.
FORME_SCOPERTE = (
    "The tracker shows {p} {n} open.",
    "We reviewed {p} {n} yesterday.",
    "{p} {n} failed validation.",
    "Il registro mostra {p} {n} aperto.",
    "Abbiamo rivisto {p} {n} ieri.",
)


def _indicizza(forma: str, parola: str, n: int = 0) -> bool:
    """Il criterio riconosce `<parola> <n>` come indice in questa frase?"""
    return (parola, n) in event_indices(forma.format(p=parola, n=n))


def _in_un_elenco(parola: str) -> list[str]:
    """In quali dei tre elenchi sta *parola*. Vuoto = il banco è onesto."""
    dove = []
    if parola in _ETICHETTE_RECORD:
        dove.append("_ETICHETTE_RECORD")
    if _EVENT_INDEX_RE.search(f"{parola} 0"):
        dove.append("_EVENT_INDEX_RE")
    if parola in _ATTRIBUTI_NUMERATI:
        dove.append("_ATTRIBUTI_NUMERATI")
    return dove


def test_CONTROLLO_le_parole_del_banco_non_stanno_in_nessuno_dei_TRE_elenchi():
    """Tiene onesto tutto il resto del file: senza, misurerebbe le liste."""
    sporche = {p: _in_un_elenco(p) for p in PAROLE if _in_un_elenco(p)}
    assert not sporche, (
        f"{sporche} sono finite in un elenco: questo banco non sta più "
        f"misurando il criterio posizionale, e i suoi verdi non significano "
        f"più quello che dicono. Sostituire la parola, non togliere il test")


def test_gli_elenchi_sono_TRE_e_decidono_cose_diverse():
    """La frase è la stessa: cambia la parola, e cambia solo in quale elenco sta."""
    assert _indicizza("The tracker shows {p} {n} open.", "sprint"), (
        "«sprint» ha smesso di essere un indice: se è uscito da _EVENT_INDEX_RE "
        "questo file va riscritto, perché la sua premessa non vale più")
    assert _in_un_elenco("sprint") == ["_EVENT_INDEX_RE"], (
        "«sprint» non sta più nel solo _EVENT_INDEX_RE: non dimostra più che è "
        "l'elenco dell'estrattore a decidere, e non il vocabolario del gate")
    assert _in_un_elenco("message") == ["_ETICHETTE_RECORD"], (
        "«message» non sta più nel solo _ETICHETTE_RECORD: era l'esempio che "
        "i tre elenchi non si contengono a vicenda")


@pytest.mark.parametrize("parola", PAROLE)
@pytest.mark.parametrize("forma", FORME_COPERTE)
def test_una_forma_col_numero_in_fondo_e_coperta(forma: str, parola: str):
    """Ciò che la promessa mantiene, e che una cura non deve far cadere."""
    assert _indicizza(forma, parola), (
        f"«{forma.format(p=parola, n=0)}» non è più un indice: era coperta il "
        f"2026-08-20 ed è una delle 3 forme su 8 che il criterio regge")


@pytest.mark.parametrize("parola", PAROLE)
@pytest.mark.parametrize("forma", FORME_SCOPERTE)
@pytest.mark.xfail(strict=True, reason=(
    "APERTO 2026-08-20, e NON è una regressione: rotto anche su 7d3e97a7, prima "
    "che 41ff5f34 introducesse il criterio nel gate. Quando dopo il numero c'è "
    "una parola di contenuto, `extract_quantities` la legge come unità (`open`→"
    "`ope`, `yesterday`, `failed`), il numero non è più «bare» e il ramo "
    "posizionale viene scartato — quindi la promessa «a position can be read» "
    "vale in 3 forme su 8. strict=True: il giorno che si allarga, questi "
    "diventano XPASS e la suite chiede di togliere il marcatore."))
def test_una_forma_con_una_parola_dopo_il_numero_dovrebbe_essere_coperta(
        forma: str, parola: str):
    assert _indicizza(forma, parola), (
        f"«{forma.format(p=parola, n=0)}»: il numero è preceduto da una parola "
        f"e seguito da un'altra parola, e il criterio posizionale non lo vede")


def test_la_copertura_e_LA_STESSA_per_tutte_le_parole():
    """L'invariante che spiega tutte le celle sopra, e la sola che va difesa.

    Se un giorno una parola avesse una copertura diversa dalle altre, vorrebbe
    dire che è rientrato un criterio LESSICALE dove il file dichiara che ce n'è
    uno posizionale — ed è il difetto che questo banco esiste per vedere.
    """
    tutte = FORME_COPERTE + FORME_SCOPERTE
    coperture = {p: tuple(_indicizza(f, p) for f in tutte) for p in PAROLE}
    distinte = set(coperture.values())
    assert len(distinte) == 1, (
        f"la copertura dipende dalla parola e non solo dalla forma: {coperture}")
    assert sum(next(iter(distinte))) == len(FORME_COPERTE), (
        f"il numero di forme coperte è cambiato: erano {len(FORME_COPERTE)} su "
        f"{len(tutte)} il 2026-08-20, cioè 18 celle su 48 con queste "
        f"{len(PAROLE)} parole")
