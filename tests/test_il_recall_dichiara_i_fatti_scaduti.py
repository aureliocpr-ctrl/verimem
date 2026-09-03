"""Quando la scadenza toglie dei fatti, il recall deve dirlo.

`valid_until` **morde**: un fatto scaduto sparisce dal top-k, e non per un
degrado di punteggio — lo toglie la maschera vettoriale (`semantic.py:4249` e
`:4252`, `fresh_mask = (view_lv <= now) & (view_vu > now)`), misurato in
`tests/test_un_fatto_scaduto_non_viene_servito.py`.

⚠️ MA L'ESCLUSIONE NON HA UN CANALE. Chi legge riceve una risposta più corta e
non ha modo di sapere che il materiale sotto è stato ridotto: **l'assenza del
campo si legge come «non ha tolto nulla»**.

Non è una forma nuova: è la stessa che `Risultati.tagliati_dal_pavimento` cura
per il pavimento, e il suo commento la descrive parola per parola — *«una lettura
che perde quattro fatti su cinque e conserva il migliore non diceva niente…
l'assenza del campo si legge come "non ha tagliato"»*. Questo test chiede lo
stesso trattamento per la scadenza.

⚠️ NON È `letto_al_passato`, e i due non vanno confusi: quello dichiara che **la
domanda** è stata interpretata come una domanda sul passato (`recall_as_of`);
qui è **il fatto** ad avere una scadenza propria. Due cause diverse dello stesso
vuoto — e il modulo dichiara già, in un commento, che tenerle su un solo segnale
è il difetto che passa il tempo a curare.

⚠️ PERCHÉ ORA, e con quale limite: il campo è popolato su **0 fatti su 17098**,
quindi oggi questo avviso non scatterebbe mai in produzione. È voluto: la riga
che dichiara deve esistere **prima** che la capacità venga esposta su più porte,
altrimenti si dà un modo di far sparire fatti senza un modo di accorgersene.
"""
import tempfile
import time

import pytest

# I due fatti parlano della STESSA cosa cosi' che una sola query li peschi
# entrambi: e' l'unico modo perche' l'assenza dello scaduto sia attribuibile alla
# scadenza e non alla domanda.
FRASE = "Il deposito di Verona ospita quattromilaseicento pallet di ricambi."
FONTE = "Inventario: il deposito di Verona ospita 4600 pallet di ricambi."
#: ⚠️ IL FATTO VIVO NON HA NUMERI, ed e' una correzione pagata: la prima
#: versione diceva «duemila pallet» con fonte «2000 pallet» — stessa identica
#: forma dello scaduto qui sopra — e il gate la QUARANTINAVA (grounding 15,66,
#: `L4-grounding`) mentre ammetteva l'altra a 99,95. Il recall tornava vuoto e
#: il test sembrava misurare la scadenza: misurava il gate.
ALTRO = "Il deposito di Verona custodisce pallet di imballaggi in un'area coperta."
FONTE_ALTRO = "Inventario: il deposito di Verona custodisce pallet di imballaggi in un'area coperta."
#: ⚠️ SETTE PAROLE, non quattro. La prima versione chiedeva «il deposito di
#: Verona» e il recall tornava VUOTO anche per il fatto vivo — la guardia sotto
#: l'ha preso. In casa la curva e' misurata: 3 parole ritrovano il 27%, 5 il 95%,
#: 7 il 100%. Una query corta non misura la scadenza, misura il pavimento.
QUERY = "quanti pallet ospita il deposito di Verona"


@pytest.fixture()
def store_isolato(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="test_dichiara_scaduti_")
    monkeypatch.setenv("HIPPO_DATA_DIR", tmp)
    monkeypatch.setenv("ENGRAM_DATA_DIR", tmp)
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
    return tmp


def test_senza_scadenze_non_dichiara_nulla(store_isolato):
    """CONTROLLO POSITIVO al rovescio: l'avviso non deve esserci quando non
    serve. Senza questo, un campo valorizzato sempre passerebbe il test sotto
    senza distinguere niente."""
    from verimem import Memory

    m = Memory()
    m.add(FRASE, topic="test/dich-a", source=FONTE)
    m.add(ALTRO, topic="test/dich-b", source=FONTE_ALTRO)
    r = m.recall(QUERY, k=10)
    testi = [x.get("text", "") if isinstance(x, dict) else str(x) for x in r]
    #: ⚠️ QUESTA RIGA MANCAVA e senza di essa il controllo non controllava: un
    #: recall VUOTO passava, perche' l'assenza dell'avviso e' compatibile con
    #: l'assenza di tutto. E' cosi' che il gate ha potuto quarantinare il fatto
    #: vivo per due giri senza che il file se ne accorgesse.
    assert testi, "il recall non serve NULLA: il file non sta misurando la scadenza"
    assert getattr(r, "esclusi_perche_scaduti", None) is None, (
        "nessun fatto e' scaduto: l'avviso non deve comparire, altrimenti "
        "comparirebbe sempre e non direbbe nulla"
    )


def test_il_conteggio_non_sopravvive_alla_lettura_successiva(store_isolato):
    """FALSIFICAZIONE DI QUESTA STESSA CURA, portata da un pari (ws1).

    `_recall_scaduti` era un attributo di CLASSE — un valore iniziale, non un
    reset per chiamata — e `SemanticMemory.recall` ha quattro uscite anticipate
    PRIMA della riga che lo assegna. Peggio: l'azzeramento che avevo messo in
    `Memory.search` stava dentro il ramo `else`, quindi una lettura con `as_of`
    non lo toccava affatto.

    ⇒ Due letture di fila sulla STESSA memoria: la prima trova uno scaduto e lo
    dichiara giustamente; la seconda — che con la scadenza non c'entra nulla —
    puo' riportare il numero della prima. Un avviso che compare quando non
    serve non e' un avviso mancato: e' una bugia, ed e' l'esatto contrario di
    cio' per cui il campo esiste.
    """
    from verimem import Memory

    m = Memory()
    ieri = time.time() - 86_400
    m.add(FRASE, topic="test/eco-scaduto", source=FONTE, valid_until=ieri)
    m.add(ALTRO, topic="test/eco-vivo", source=FONTE_ALTRO)

    primo = m.recall(QUERY, k=10)
    #: CONTROLLO POSITIVO: se la prima lettura non dichiarasse nulla, la seconda
    #: non potrebbe ereditare niente e il test passerebbe senza misurare.
    assert getattr(primo, "esclusi_perche_scaduti", None) is not None, (
        "la prima lettura non dichiara: non c'e' nulla da ereditare e questo "
        "test non sta misurando l'eco"
    )

    #: ⚠️ LA SECONDA DOMANDA E' FUORI TEMA, e la scelta e' quella che rende il
    #: test capace di distinguere: se chiedessi la STESSA cosa, dopo la cura il
    #: conteggio sarebbe fresco ma di nuovo 1, e un test che pretende `None`
    #: fallirebbe su un comportamento GIUSTO. Su una domanda che non pesca
    #: nulla di scaduto, invece, il valore fresco e' 0 e un 1 puo' venire solo
    #: dalla chiamata precedente — cioe' esattamente l'eco che si misura.
    secondo = m.recall("come si regola il termostato della sala macchine", k=10)
    assert getattr(secondo, "esclusi_perche_scaduti", None) is None, (
        f"la seconda lettura riporta il conteggio della PRIMA: "
        f"{getattr(secondo, 'esclusi_perche_scaduti', None)!r}. Il contatore "
        f"non viene azzerato all'ingresso e sopravvive alla chiamata"
    )


def test_quando_la_scadenza_toglie_un_fatto_il_recall_lo_dichiara(store_isolato):
    """Il caso: due fatti sulla stessa cosa, uno scaduto. La risposta arriva
    (l'altro c'è), ma chi legge deve sapere che sotto ne è stato tolto uno."""
    from verimem import Memory

    m = Memory()
    ieri = time.time() - 86_400
    m.add(FRASE, topic="test/dich-scaduto", source=FONTE, valid_until=ieri)
    m.add(ALTRO, topic="test/dich-vivo", source=FONTE_ALTRO)

    r = m.recall(QUERY, k=10)
    testi = [x.get("text", "") if isinstance(x, dict) else str(x) for x in r]
    assert any("coperta" in t for t in testi), (
        f"il fatto VIVO deve essere servito, altrimenti il vuoto ha un'altra "
        f"causa e il test non misura la scadenza: {testi!r}"
    )
    assert not any("ricambi" in t for t in testi), (
        f"il fatto SCADUTO non dev'essere servito: {testi!r}"
    )

    avviso = getattr(r, "esclusi_perche_scaduti", None)
    assert avviso is not None, (
        "la scadenza ha tolto un fatto e il recall NON LO DICE: chi legge vede "
        "una risposta piu' corta e non ha modo di sapere che sotto c'era altro. "
        "E' la stessa forma che `tagliati_dal_pavimento` cura per il pavimento"
    )
    assert avviso.get("esclusi") == 1, (
        f"l'avviso deve dire QUANTI ne ha tolti, non solo che ne ha tolti: {avviso!r}"
    )


# ⚠️ QUI C'ERA UNO `xfail(strict=True)` PER IL CASO CHE NON FUNZIONA, ed e'
# stato tolto dopo averlo eseguito: risultava XPASS. Committarlo avrebbe rotto
# la CI — che e' ESATTAMENTE il difetto diagnosticato stamattina in un altro
# file, arrivato fin qui per la stessa strada.
#
# La ragione dello XPASS e' il reperto, ed e' piu' grande di questo file:
# SOTTO PYTEST L'EMBEDDER E' UNO STUB (`encoder: _StubModel`, verificato), e le
# similarita' non somigliano a quelle del prodotto:
#
#     sotto pytest (stub)       servito 0,7144   scaduto 0,3536
#     CLI vera (modello vero)   servito 0,8969   scaduto 0,8159
#
# ⇒ Ogni test che dipende da un confronto fra similarita' — questo compreso —
# misura lo stub. I test di questo file restano validi perche' verificano che
# l'avviso ESISTA e sia legato alla domanda, non la taratura di una soglia; ma
# nessuno di loro puo' dire se il criterio funziona sul prodotto. Quello si
# vede solo dalla porta vera, e da li' oggi NON funziona (numeri nel commit
# 28d53170 e in `client.py`).
