"""L'ESTRATTO che finisce in un evento e in una etichetta non deve mutilare.

Terza parte del mandato lingue (Aurelio, 2026-08-07) per il perimetro ws7 —
le superfici di governo. I primi due pezzi hanno curato il taglio della CLI
(`d07f5ca0`) e quello della sala motore (`ed3838bc`). Restavano i punti che
avevo DICHIARATO aperti sul canale: gli estratti negli eventi `flow.*` e le
etichette del grafo di discendenza.

⚠️ QUI IL DIFETTO E' PEGGIO CHE IN UNA UI. In una interfaccia un accento
perso e' un carattere brutto; in un evento e' un DATO archiviato: la riga
finisce in `events.jsonl`, viene riletta mesi dopo, e chi cerca la
proposizione con la stringa che ha in mano non la trova piu'.

=== IL PUNTO DI PROGETTO, ed e' la ragione per cui il banco sta su `emit` ===
La lunghezza dell'estratto la decideva OGNI CHIAMANTE (`[:140]` in due
posti, `[:80]` in altri due, `[:800]` per il transcript). Quattro copie
della stessa politica: e' la classe ① di questo prodotto — *una copia invece
della superficie unica*. La cura sposta la politica DENTRO l'emettitore: il
chiamante dice quale campo e', l'emettitore decide quanto e come tagliare.

🔑 E ho verificato che l'ordine conta e non e' invertibile: **riparare a
valle non si puo'.** Dei quattro modi di rompere un grafema, due lasciano
una traccia (uno ZWJ penzolante, mezza bandiera) e due NON ne lasciano
nessuna — l'accento composto e il virama SPARISCONO, e `caffe` e `नमस` sono
stringhe legittime che nessun controllo a valle puo' riconoscere come
mutilate. Quindi l'emettitore deve ricevere il testo INTERO: se riceve gia'
il taglio, il dato e' gia' perso.
"""
from __future__ import annotations

import unicodedata as _ud
from types import SimpleNamespace

from verimem import lineage_trace, observability


def _non_spezza(intero: str, estratto: str) -> bool:
    """L'invariante: il carattere SUBITO DOPO il taglio non si compone con
    l'ultimo tenuto. Se si compone, quello che ho tenuto e' uscito senza il
    suo segno — che e' esattamente il difetto."""
    if not intero.startswith(estratto):
        return False
    if len(estratto) >= len(intero):
        return True
    return _ud.combining(intero[len(estratto)]) == 0


def _proposizione_che_si_spezza(taglio: int) -> str:
    """Una proposizione in cui il carattere in posizione ``taglio`` e' il
    segno combinante di quello prima.

    ⚠️ Costruita a RUNTIME con `normalize("NFD")` e non scritta come
    letterale: una `é` battuta nel sorgente viene salvata PRECOMPOSTA (un
    solo code point), il taglio non spezzerebbe niente e **il banco passerebbe
    senza misurare nulla**. E' l'errore che ho gia' pagato una volta oggi.
    """
    accento = _ud.normalize("NFD", "é")  # 'e' + U+0301, DUE code point
    assert len(accento) == 2, "l'ambiente ha ricomposto: il banco non misura"
    # la 'e' finisce in `taglio - 1`, il suo segno esattamente in `taglio`.
    # ⚠️ La prima stesura IGNORAVA `taglio` e metteva l'accento a indice 128:
    # a 140 c'era uno spazio, due prove passavano senza misurare niente. E'
    # la stessa trappola di stamattina, con un'altra faccia — un banco che
    # non guarda dove taglia il prodotto misura se stesso.
    riempimento = ("deposito " * 60)[:taglio - 1]
    assert len(riempimento) == taglio - 1
    return riempimento + accento + " macchiato, e altro testo dopo il taglio"


class TestEstrattoNegliEventi:
    """Il campo `*_excerpt` di un evento: tagliato dall'emettitore, pulito."""

    def _cattura(self, **payload):
        visti: list = []

        def orecchio(evt):
            visti.append(evt)

        # una funzione con NOME, non `visti.append`: il bound method e' un
        # oggetto nuovo a ogni accesso e la unsubscribe non lo ritroverebbe
        # (il bus perderebbe un ascoltatore a ogni test — la perdita che
        # `test_eventbus_unsubscribe_leak.py` gia' presidia).
        observability.BUS.subscribe("*", orecchio)
        try:
            observability.emit("fact_stored", **payload)
        finally:
            observability.BUS.unsubscribe("*", orecchio)
        assert visti, "l'evento non e' arrivato sul bus"
        return visti[-1].payload

    def test_il_taglio_dell_estratto_non_spezza_il_grafema(self):
        intero = _proposizione_che_si_spezza(observability.MAX_ESTRATTO)
        # posizione del taglio dentro un grappolo: e' la premessa del banco
        assert _ud.combining(intero[observability.MAX_ESTRATTO]) != 0

        p = self._cattura(fact_id="f1", topic="t",
                          proposition_excerpt=intero)
        estratto = p["proposition_excerpt"]
        assert _non_spezza(intero, estratto), repr(estratto[-6:])

    def test_l_estratto_e_limitato_dall_emettitore(self):
        """Il chiamante passa il testo INTERO: se l'emettitore non tagliasse,
        una proposizione lunga finirebbe per intero in ogni riga del log."""
        intero = "x" * 5000
        p = self._cattura(fact_id="f1", topic="t",
                          proposition_excerpt=intero)
        assert len(p["proposition_excerpt"]) <= observability.MAX_ESTRATTO

    def test_presidio_italiano_invariato(self):
        """IL PRESIDIO di ws3, e senza questo confronto non si saprebbe se il
        difetto e' della lingua o della funzione. Su testo italiano gia'
        composto l'estratto e' ESATTAMENTE il taglio semplice."""
        intero = ("Il magazzino di Citta' Sant'Angelo ospita 300 pallet "
                  "di merce varia. " * 8)
        p = self._cattura(fact_id="f1", topic="t",
                          proposition_excerpt=intero)
        assert p["proposition_excerpt"] == intero[:observability.MAX_ESTRATTO]

    def test_gli_altri_campi_non_vengono_toccati(self):
        """FALSIFICAZIONE: una cura che tronca TUTTO passerebbe i tre test
        sopra ed e' sbagliata. Solo i campi che si dichiarano estratti."""
        lungo = "y" * 5000
        p = self._cattura(fact_id="f1", topic=lungo, reason=lungo)
        assert p["topic"] == lungo
        assert p["reason"] == lungo

    def test_un_estratto_non_stringa_non_rompe_l_emissione(self):
        """`emit` non deve MAI sollevare nel percorso di scrittura."""
        p = self._cattura(fact_id="f1", proposition_excerpt=None)
        assert p["proposition_excerpt"] is None


class TestEtichettaDelGrafo:
    """`lineage_trace._label_for` e' l'etichetta che si LEGGE nel grafo di
    discendenza: stesso taglio, stessa cura."""

    def _agente(self, testo: str):
        return SimpleNamespace(
            semantic=SimpleNamespace(
                get=lambda _i: SimpleNamespace(proposition=testo)),
            memory=SimpleNamespace(
                get=lambda _i: SimpleNamespace(task_text=testo)),
            skills=SimpleNamespace(get=lambda _i: None),
        )

    def test_etichetta_di_un_fatto_non_spezza(self):
        intero = _proposizione_che_si_spezza(140)
        assert _ud.combining(intero[140]) != 0
        etichetta = lineage_trace._label_for("f1", "fact", self._agente(intero))
        assert _non_spezza(intero, etichetta), repr(etichetta[-6:])

    def test_etichetta_di_un_episodio_non_spezza(self):
        intero = _proposizione_che_si_spezza(140)
        etichetta = lineage_trace._label_for("e1", "episode",
                                             self._agente(intero))
        assert _non_spezza(intero, etichetta), repr(etichetta[-6:])

    def test_presidio_italiano_etichetta_invariata(self):
        intero = ("Il deposito di Citta' Sant'Angelo e' pieno. " * 10)
        etichetta = lineage_trace._label_for("f1", "fact", self._agente(intero))
        assert etichetta == intero[:140]
