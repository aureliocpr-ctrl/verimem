"""Su una prosa lunga, UN token condiviso bastava a dichiarare un conflitto.

`conflict_from_parts` è il punto condiviso — il suo docstring lo dice: «Single
source of truth used by BOTH the write-time gate and the batch corpus
scanner». La guardia di precisione è «due frasi devono condividere una parola
di contenuto distintiva prima che valori diversi per la stessa unità contino
come contraddizione». Su frasi corte funziona. Su prosa lunga no.

MISURATO SUL CORPUS VERO (campione 220 fatti con quantità, 24090 coppie)::

    conflitti numerici trovati:                     321
    di cui tenuti in piedi da UN SOLO token:         84   (26%)

e quelli sono fatti che non parlano della stessa cosa::

    token «json»   unità tool    5.0 vs 4.0
    token «chain»  unità loc  1700.0 vs 1414.0
    token «loop»   unità skill   8.0 vs 324.0

Un handoff da 800 caratteri e un altro handoff da 800 caratteri condividono la
parola «loop» e hanno entrambi un numero seguito da «skill»: il gate li
dichiara in contraddizione. E `anti_confab_gate.py:1240` legge quel verdetto e
manda il fatto vecchio a `_route_evolutions`, cioè lo RITIRA — che è il
meccanismo già quantificato il 01/08 come «la supersessione mangia i fatti
veri», 1781 fatti su 6686.

LA CURA NON È UN CONTEGGIO, ed è importante perché il conteggio è già stato
falsificato. Il 25/07 fu provato un criterio strutturale — «ciascun lato ha una
parola distintiva che l'altro non ha, quindi sono soggetti diversi» — e cadde
su due test che esistevano già (`test_exclusive_words_mean_other_subject.py`:
«un attributo opposto, un sinonimo e un valore cambiato hanno la stessa forma
lessicale»). Qui il criterio è un RAPPORTO: quanta parte della frase più povera
è condivisa. Due frasi corte che condividono la metà dei loro termini sono
dello stesso soggetto; due prose che ne condividono un ventottesimo no.

LE DUE POPOLAZIONI SONO SEPARATE, misurate prima di scrivere la cura:

    conflitti che il codice dichiara sulle frasi dei TEST (118 coppie)
        quota minima   0.3333
    falsi dal corpus tenuti da un token (84 coppie)
        quota massima  0.0714

Un fattore 4.7 fra le due. La soglia sta in mezzo e non tocca nessuno dei casi
presidiati — verificato prima di toccare il codice, non dopo.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import numeric_conflict

#: Due prose lunghe che condividono UNA parola e un'unità. Sono la forma
#: esatta trovata sul corpus, accorciate quel tanto che basta a leggerle.
LUNGA_A = (
    "MEGA HANDOFF cycle 313: chiuso il giro sul recall, cablato il probe, "
    "riscritto il composer, misurata la banda del cross encoder, allineati "
    "i tre lettori del soggetto, e il pacchetto conta 1700 loc toccate "
    "nella chain dei moduli di lettura."
)
LUNGA_B = (
    "OMNEX ha una architettura chain con escalation intra scan completa, "
    "BaseFinding e ChainComposer, il registro dei plugin, la coda dei "
    "risultati e il report finale, per un totale di 1414 loc distribuite "
    "fra i sei moduli del motore."
)


def test_una_parola_su_una_prosa_lunga_non_e_lo_stesso_soggetto():
    got = numeric_conflict(LUNGA_A, LUNGA_B)
    assert got is None, (
        f"dichiarato conflitto {got} fra due prose che condividono una parola "
        f"su decine: il gate manda il fatto vecchio a _route_evolutions, cioè "
        f"lo ritira")


#: I casi che il prodotto DEVE continuare a prendere. Presi dai test che
#: esistono già, non inventati: la quota minima misurata su 118 coppie dei
#: test è 0.3333, ben sopra la soglia.
VERI = [
    ("Sessions are stored with a TTL of 30 minutes.",
     "Sessions expire after 45 minutes of inactivity."),
    ("Cache is bounded at 1024 entries.", "Cache holds 4096 entries."),
    ("Il piano annuale costa 100 euro.", "Il piano annuale costa 200 euro."),
    ("Marco ha 30 anni.", "Marco ha 40 anni."),
]


@pytest.mark.parametrize("a,b", VERI)
def test_i_conflitti_veri_restano(a, b):
    assert numeric_conflict(a, b) is not None, (
        "la guardia ha mangiato un conflitto vero: la soglia è troppo alta")


def test_la_soglia_si_puo_spegnere(monkeypatch):
    """Come ogni altra guardia del prodotto: chi dipende dal comportamento
    di prima ha una via per riaverlo."""
    monkeypatch.setenv("ENGRAM_CONFLICT_MIN_SHARED_RATIO", "0")
    assert numeric_conflict(LUNGA_A, LUNGA_B) is not None


def test_una_soglia_illeggibile_non_rompe_il_gate(monkeypatch):
    monkeypatch.setenv("ENGRAM_CONFLICT_MIN_SHARED_RATIO", "molto")
    numeric_conflict(LUNGA_A, LUNGA_B)  # non deve sollevare


def test_lo_scanner_batch_vede_la_stessa_cosa():
    """Il docstring promette che gate e scanner restino identici: la cura sta
    nel punto condiviso, quindi la promessa regge da sé."""
    from verimem.quantity_match import conflict_from_parts, distinctive_tokens
    from verimem.quantity_match import extract_quantities as q
    got = conflict_from_parts(q(LUNGA_A), distinctive_tokens(LUNGA_A),
                              q(LUNGA_B), distinctive_tokens(LUNGA_B))
    assert got is None
