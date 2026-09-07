"""Un verbo che la lista di atomic_claims non ha si riconosce dalla desinenza,
con due guardie (blocco «VERBO PER MORFOLOGIA» del modulo).

Cella scritta PRIMA del banco cieco di Marie (30 composte + 10 controlli su
testo nuovo, chiesto il 06/09 alle 13:47 con le predizioni depositate: >= 80%
delle code con verbo fuori lista spezzate, <= 1 controllo su 10 spezzato per
errore). Qui ci sono solo i casi GIA' NOTI, quelli su cui la regola e' stata
disegnata: le 30 composte della parte B del banco dei claim corti (con la sola
lista, anche allargata dei nove verbi, ne restavano fuse 16 per tredici verbi
fuori lista: lascia, sposta, blocca, cancella, rinvia, raddoppia, dimezza,
libera, allunga, riduce, riapre, conoscono, cambia) e i due errori della regola
LARGA sulle desinenze («visibile in skills list», «multilingue in 10 lingue»).
Un 30/30 qui NON e' la misura — e' il controllo che la regola fa cio' per cui e'
scritta e non rompe i casi che la forma larga rompeva. La misura e' il banco
cieco, su frasi che chi ha scritto la regola non ha visto.
"""
from __future__ import annotations

import pytest

from verimem.atomic_claims import _verbo_morfologico, decomponi, ha_verbo_finito

# le 10 teste vere del P3 (tre code ciascuna) e le 30 code false corte, nello
# stesso ordine del banco «la regola dei claim corti misurata prima di scriverla»
# (docs/stato-reale/banchi, parte B)
TESTE = [
    "Al collaudo sono emersi dei rilievi.",
    "Il fornitore e' ancora in attesa dell'importo.",
    "Nessuna decisione e' stata assunta in quella data.",
    "La consegna e' arrivata dopo la data prevista.",
    "L'impianto lascia inutilizzata piu' di meta' della capacita'.",
    "Alla pratica mancano ancora dei gradi.",
    "Alcuni partecipanti non sono arrivati.",
    "Sul tetto serve ancora un intervento.",
    "Nel 2025 la licenza risulta scaduta.",
    "Del campione non si conoscono ancora i valori.",
]
CODE = [
    " e resta aperto.", " e vale per Prato.", " e riguarda il magazzino.",
    " e costa poco.", " e dura un mese.", " e scade domani.", " e parte lunedi'.",
    " e tocca la mensa.", " e chiude il reparto.", " e vale anche a Pordenone.",
    " e interessa la direzione.", " e riguarda i fornitori.", " e copre il trimestre.",
    " e serve al collaudo.", " e cambia il turno.", " e ferma la linea.",
    " e apre il deposito.", " e sposta la consegna.", " e blocca il pagamento.",
    " e cancella la riunione.", " e rinvia la firma.", " e raddoppia il canone.",
    " e dimezza le scorte.", " e libera il piazzale.", " e allunga la garanzia.",
    " e riduce i rilievi.", " e sposta la sede.", " e chiude il cantiere.",
    " e ferma le spedizioni.", " e riapre il bando.",
]
COMPOSTE = [TESTE[i // 3].rstrip(".") + CODE[i] for i in range(30)]

# coordinazioni di nomi e aggettivi: UN claim, non due. I primi due sono gli
# errori della regola larga; «piano» e «mano» sono i due casi che il modulo
# citava contro ogni regola sulle desinenze.
CONTROLLI = [
    "Skill registrata e visibile in skills list.",
    "Il modello e' semantico e multilingue in 10 lingue.",
    "La risposta e' robusta e veloce.",
    "Una scelta e una rinuncia.",
    "Tre file e due cartelle restano in memoria e su disco.",
    "Il piano e la mano.",
    "Il servizio e' lento ma stabile e pronto al rilascio.",
    "La memoria e il consumo restano bassi.",
    "In memoria e su disco il file e' identico.",
    "Il test e' verde e stabile da tre giorni.",
]


@pytest.mark.parametrize("composta", COMPOSTE, ids=[c.strip() for c in CODE])
def test_le_30_composte_note_si_spezzano_in_due_claim(composta):
    claims = decomponi(composta)
    assert len(claims) == 2, claims
    coda = composta.rsplit(" e ", 1)[1].rstrip(".")
    assert claims[1].rstrip(".").endswith(coda), claims


@pytest.mark.parametrize("testa", TESTE)
def test_ogni_testa_ha_un_verbo_riconosciuto(testa):
    # «lascia» (seguito da un participio) e «conoscono» (-ono) non sono in lista
    assert ha_verbo_finito(testa), testa


@pytest.mark.parametrize("controllo", CONTROLLI)
def test_una_coordinazione_di_nomi_o_aggettivi_resta_un_claim_solo(controllo):
    claims = decomponi(controllo)
    assert len(claims) == 1, claims


@pytest.mark.parametrize("pezzo, verbo", [
    ("riduce i rilievi", "riduce"),
    ("lascia inutilizzata la meta'", "lascia"),
    ("non si conoscono ancora i valori", "conoscono"),
    ("cambiera' il turno", "cambiera'"),
    ("cambierà il turno", "cambierà"),
    ("i valori finiscono nel registro", "finiscono"),
    ("costa poco", "costa"),
    ("scade domani", "scade"),
])
def test_la_morfologia_trova_il_verbo(pezzo, verbo):
    m = _verbo_morfologico(pezzo)
    assert m is not None and m.group() == verbo, (pezzo, m and m.group())


@pytest.mark.parametrize("pezzo", [
    "visibile in skills list",   # aggettivo + preposizione
    "multilingue in 10 lingue",  # idem
    "veloce",                    # aggettivo in fine pezzo
    "una scelta senza tre",      # determinante, preposizione, numerale
    "il piano e la mano",        # i due «troppo larga»
    "10 lingue",                 # nome dopo un numero
    "l'ultima versione",         # elisione davanti, nome in -ione
    "citta' e paese",            # accento finale scritto con l'apostrofo
    "chiaramente la memoria",    # avverbio in -mente
    "allunga per un mese",       # LIMITE DICHIARATO: verbo in -a seguito da preposizione
    "appare nel registro",       # LIMITE DICHIARATO: verbo in -are (parere/apparire)
])
def test_la_morfologia_tace_su_nomi_aggettivi_e_sui_limiti_dichiarati(pezzo):
    assert _verbo_morfologico(pezzo) is None, pezzo
