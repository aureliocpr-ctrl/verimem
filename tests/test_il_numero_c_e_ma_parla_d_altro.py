"""«14 valvole» entra a 100.0 perché la fonte dice «14 operai».

IL BUCO DI L4.1, trovato da ws5 verificando la cura in indipendenza — cioè da
chi non aveva scritto il criterio::

    cifra RIUSATA dalla fonte: fermati 0/3
    cifra NUOVA:               fermati 3/3

    «L'accordo con Marelli dura 3 anni.»      la fonte ha «3 per cento»  ->  98.6
    «Il fornitore Gatti ha consegnato 14 valvole.»  ha «14 operai»       -> 100.0
    «Il magazzino di Chieti contiene 2 corsie.»     ha «linea 2»         -> 100.0

``valori_non_nella_fonte`` confronta i VALORI e non le coppie (unità, valore), e
il suo docstring lo DICHIARAVA. La giustificazione regge ancora — l'unità in un
testo libero è fragile — ma la stima del costo era sbagliata: in un documento
aziendale le cifre da 1 a 20 sono ovunque, quindi un'allucinazione con un numero
piccolo trova quasi sempre una cifra gemella. **Un limite dichiarato ma
sottostimato resta un difetto, non una scelta.**

LA MISURA CHE HA DECISO LA CURA, fatta PRIMA di scrivere il criterio::

                                    vicinato UGUALE   DIVERSO
    inventati con cifra riusata            0             7
    veri riformulati                      10             1

Riformulare cambia il VERBO, non l'UNITÀ: «prodotti 850 telai» → «realizzato 850
telai». È questo che rende il vicinato più stretto della copertura lessicale di
ws4, caduta con 6 falsi positivi su 8 perché guardava TUTTE le parole.

🔑 E IL CRITERIO SI È RIVELATO PIÙ PROFONDO DI COME ERA STATO PROGETTATO. Il
lato *precedente* era stato aggiunto per un caso solo — «linea 3 **è rimasta**»
contro «linea 3 **ha lavorato**», dove il numero è un identificativo e ciò che
segue è un verbo. Misurando i SINONIMI si è visto che cattura anche quelli:
«300 **pallet**» contro «300 **bancali**» ha il seguente diverso e il precedente
uguale (``ospita``). La regola vera non è «stessa unità», è **«almeno un lato
dell'intorno coincide ⇒ è la stessa grandezza»**.

⚠️ IL LIMITE, MISURATO E NON NASCOSTO — è il prezzo esatto di quel lato::

    inventati che copiano il contesto e cambiano SOLO l'unità   persi 4/4
        «In reparto sono presenti 14 valvole.»  (fonte: 14 operai)  -> 99.961
        «Il deposito ospita 300 scaffali.»      (fonte: 300 bancali)-> 99.152
        «Sono state spedite 60 pedane.»         (fonte: 60 casse)   -> 99.973
    e il moat ne ferma **1 su 4** — solo «4500 dollari» contro «4500 euro», che
    legge come incompatibile (6.6).

Il verso opposto era peggio: senza il lato precedente il criterio colpirebbe
ogni sinonimo, e il riformulato È il caso normale. Si sceglie di coprire meno e
non sbagliare sul caso normale — la stessa scelta, e per la stessa ragione, di
L4.1 rispetto alla copertura lessicale.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto

FONTE = ("Relazione trimestrale dello stabilimento di Pordenone. Sono stati "
         "prodotti 850 telai. La linea 3 ha lavorato per 22 giorni. Il "
         "contratto con Ferrero vale 4500 euro. Sono stati assunti 7 tecnici. "
         "La spedizione comprendeva 60 casse.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


# ⚠️ Ogni claim in un TOPIC DIVERSO — protocollo di ws5: varianti dello stesso
# claim nello stesso topic vengono lette come supersessioni l'una dell'altra, e
# si finisce per misurare la supersessione credendo di misurare il giudizio.

@pytest.mark.parametrize("i,claim", list(enumerate([
    "La garanzia dura 3 anni.",          # 3  <- «linea 3»
    "Il magazzino ha 7 corsie.",         # 7  <- «7 tecnici»
    "Il collaudo e' durato 22 minuti.",  # 22 <- «22 giorni»
])))
def test_un_numero_preso_da_UN_ALTRO_contesto_viene_DICHIARATO(mem, i, claim):
    """IL CUORE. Il valore è nella fonte ma riferito a un'altra grandezza, e il
    moat lo approvava fino a 100.0 perché la cifra c'è davvero.

    ⚠️ **DICHIARA, non quarantina**, e la differenza è misurata: come veto
    costerebbe il 20% di falsi positivi sui riformulati veri (banco di ws4,
    1/5 — «300 pallet» contro «300 bancali»). Il riformulato è il caso
    normale; si consegna l'avviso e si lascia decidere.
    """
    r = mem.add(claim, topic=f"az/riuso{i}", source=FONTE)
    layers = [w.get("layer") for w in (r.get("warnings") or [])]
    assert "L4.2" in layers, (
        f"nessun avviso sul numero riusato (g={r.get('grounding_score')}, "
        f"layers={layers}): {claim}")


def test_l_avviso_dice_QUALE_grandezza_non_torna(mem):
    """Chi riceve l'avviso deve poter decidere in un colpo d'occhio: senza i
    due sostantivi affiancati, «un numero non torna» costringe a rileggere la
    fonte a mano — ed è esattamente il lavoro che il gate esiste per togliere.
    """
    r = mem.add("Il magazzino ha 7 corsie.", topic="az/dett", source=FONTE)
    testo = " ".join(str(w) for w in (r.get("warnings") or []))
    assert "corsie" in testo and "tecnici" in testo, r.get("warnings")


@pytest.mark.parametrize("i,claim", list(enumerate([
    "Lo stabilimento ha realizzato 850 telai.",
    "L'accordo con Ferrero ammonta a 4500 euro.",
    "Sono state spedite 60 casse.",
    "L'azienda ha assunto 7 tecnici.",
    "La linea 3 e' rimasta operativa per 22 giorni.",
])))
def test_CONTROLLO_POSITIVO_i_riformulati_VERI_passano(mem, i, claim):
    """⚠️ IL PRESIDIO CHE VALE PIÙ DELLA CURA, ed è il caso NORMALE: nessuno
    ricopia la fonte, la riscrive con parole sue. L'ultimo è quello che ha
    imposto il lato precedente del criterio — «linea 3» è un identificativo."""
    r = mem.add(claim, topic=f"az/vero{i}", source=FONTE)
    assert r.get("status") != "quarantined", (
        f"riformulato VERO trattenuto: {claim} (g={r.get('grounding_score')}, "
        f"warnings={r.get('warnings')})")


def test_i_SINONIMI_dell_unita_non_fanno_scattare_il_criterio():
    """La popolazione costruita CONTRO il criterio: veri che cambiano proprio il
    sostantivo su cui il criterio si regge. Passano perché il lato precedente
    coincide — ed è il motivo per cui questa cura non ripete la caduta della
    copertura lessicale (6 falsi positivi su 8)."""
    fonte = ("Verbale: il deposito ospita 300 bancali. Sono state spedite 60 "
             "casse. In reparto sono presenti 14 operai.")
    for claim in ("Il deposito ospita 300 pallet.",
                  "Sono state spedite 60 scatole.",
                  "In reparto sono presenti 14 dipendenti."):
        assert not valori_riusati_da_altro_contesto(claim, fonte), claim


@pytest.mark.parametrize("lingua,fonte,claim,deve_scattare", [
    ("EN", "Report: the plant produced 850 frames. Line 3 ran for 22 days. "
           "7 technicians were hired.",
     "The warehouse has 7 aisles.", True),
    ("EN", "Report: the plant produced 850 frames. Line 3 ran for 22 days. "
           "7 technicians were hired.",
     "The plant manufactured 850 frames.", False),
    ("DE", "Bericht: das Werk produzierte 850 Rahmen. Es wurden 7 Techniker "
           "eingestellt.",
     "Das Lager hat 7 Gaenge.", True),
    ("DE", "Bericht: das Werk produzierte 850 Rahmen. Es wurden 7 Techniker "
           "eingestellt.",
     "Das Werk fertigte 850 Rahmen.", False),
    ("FR", "Rapport: l'usine a produit 850 chassis. On a recrute 7 techniciens.",
     "L'entrepot compte 7 allees.", True),
    ("FR", "Rapport: l'usine a produit 850 chassis. On a recrute 7 techniciens.",
     "L'usine a fabrique 850 chassis.", False),
    ("ES", "Informe: la planta produjo 850 bastidores. Se contrataron 7 tecnicos.",
     "El almacen tiene 7 pasillos.", True),
    ("ES", "Informe: la planta produjo 850 bastidores. Se contrataron 7 tecnicos.",
     "La planta fabrico 850 bastidores.", False),
])
def test_il_criterio_e_POSIZIONALE_quindi_regge_in_altre_lingue(
        lingua, fonte, claim, deve_scattare):
    """Non c'è nessuna lista di parole qui dentro: il criterio guarda DOVE stanno
    i token rispetto al numero. Il presidio serve perché la classe «lista
    monolingue in un prodotto mondiale» è la ③ di questa casa."""
    scatta = bool(valori_riusati_da_altro_contesto(claim, fonte))
    assert scatta is deve_scattare, f"{lingua}: {claim}"


def test_IL_LIMITE_e_dichiarato_e_questo_test_lo_fotografa():
    """⚠️ NON è una cura: è il limite MISURATO, tenuto sotto test perché non si
    perda. Un inventato che copia il contesto e cambia solo l'unità passa —
    ``presenti 14 valvole`` contro ``presenti 14 operai`` — e il moat ne prende
    1 su 4. Se un giorno il criterio li prendesse, questo test cade e va
    riscritto: sarebbe un miglioramento, non una regressione."""
    fonte = ("Verbale: il deposito ospita 300 bancali. In reparto sono "
             "presenti 14 operai.")
    mimetici = ["In reparto sono presenti 14 valvole.",
                "Il deposito ospita 300 scaffali."]
    persi = [c for c in mimetici if not valori_riusati_da_altro_contesto(c, fonte)]
    assert len(persi) == len(mimetici), (
        "il criterio ora prende i mimetici: aggiorna il limite dichiarato nel "
        f"docstring di vicinato_del_valore.py (presi: {set(mimetici)-set(persi)})")


def test_senza_fonte_il_criterio_TACE():
    """Senza fonte non c'è nulla con cui confrontare, e inventarsi un verdetto è
    ciò che tutto questo modulo esiste per impedire."""
    assert not valori_riusati_da_altro_contesto("Ci sono 14 valvole.", "")
    assert not valori_riusati_da_altro_contesto("", "14 operai")
