"""Il pavimento tagliava fatti e lo diceva SOLO quando li aveva tagliati tutti.

DA DOVE VIENE, e conviene dirlo perche' nasce da un mio errore pubblico. Alle
22:03 ho scritto a chi stava misurando «quanto taglia il pavimento» che poteva
rileggere il taglio dal campo `tagliati`, gia' in `main` dal pezzo (i). E' FALSO
nel caso che stava misurando, e la condizione lo dice a chiare lettere::

    if _soglia and _n_prima and _best_prima < _soglia   # client.py

`tagliati` vive DENTRO l'avviso `sotto_il_pavimento`, e quell'avviso esce solo
quando il migliore e' SOTTO la soglia — cioe' quando il pavimento ha portato via
TUTTO. Chi misurava aveva 0 avvisi accesi su 6 domande pertinenti: il migliore
sopravviveva ogni volta, quindi l'avviso era `None`, quindi il campo non esisteva
proprio nel caso in cui serviva.

🔑 IL DIFETTO, che e' piu' grande dell'errore che l'ha scoperto: **una lettura
che perde 4 fatti su 5 e conserva il migliore non dice niente.** Chi legge vede
una risposta buona e non ha modo di sapere che il pavimento ha tolto l'80% del
materiale su cui quella risposta si regge. E' la forma «una misura che non c'e'
si legge come perfetta»: l'assenza del campo viene letta come «non ha tagliato».

⚖️ PERCHE' UN CAMPO NUOVO E NON ALLARGARE L'AVVISO. Sono due significati:
`sotto_il_pavimento` e' un'ASTENSIONE («non mi fido di niente di quello che ho»),
`tagliati_dal_pavimento` e' un DATO («ho tolto N di M»). Farli uscire dallo stesso
campo e' esattamente l'errore che questo modulo passa la notte a curare — un solo
segnale per due significati — e renderebbe l'astensione rumorosa proprio mentre
la sua rarita' e' cio' che la rende leggibile.

⚠️ COME QUESTO BANCO SI DIFENDE DALLO STUB. Sotto pytest l'embedder e' uno stub
SHA-256: gli score sono arbitrari. Quindi non fisso soglie a mano — le LEGGO
nella stessa esecuzione e scelgo un valore che cade **fra il massimo e il
minimo**. Cosi' il caso «taglia, ma il migliore sopravvive» e' costruito per
definizione, qualunque cosa dica l'embedder.

🪞 E LA PRIMA STESURA DI QUESTO BANCO ERA SBAGLIATA, vale la pena lasciarlo
scritto: pretendevo `scala[0] > scala[1]`, cioe' il primo STRETTAMENTE sopra il
secondo, e in questo ambiente i primi due punteggi sono IDENTICI (`0.5477`) —
tre fatti condividono le stesse parole della domanda. La premessa cadeva e il
banco moriva prima di misurare il difetto. Serve molto meno: che esista **un
punteggio sotto il massimo**, e la soglia si mette in mezzo.
"""

from __future__ import annotations

import pytest

from verimem.client import Memory

DOMANDA = "canone del contratto"


@pytest.fixture()
def memoria(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    m = Memory(str(tmp_path / "s.db"))
    for testo, src in [
        ("Il canone del contratto Rossi e' 900 euro al mese.",
         "Contratto Rossi: canone 900 euro al mese."),
        ("Il canone del contratto Bianchi e' 750 euro al mese.",
         "Contratto Bianchi: canone 750 euro al mese."),
        ("Il canone del contratto Verdi e' 1100 euro al mese.",
         "Contratto Verdi: canone 1100 euro al mese."),
        ("Il deposito cauzionale del contratto Neri e' di tre mensilita'.",
         "Contratto Neri: deposito di tre mensilita'."),
    ]:
        m.add(testo, source=src, topic="tmp/contratti")
    return m


def _scala(memoria):
    """I punteggi VERI di questa esecuzione, dal piu' alto al piu' basso.

    ⚠️ Si legge senza pavimento e con `as_of=None`: il routing temporale non
    c'entra con questo banco e una data dedotta svuoterebbe il risultato per
    tutt'altra causa.
    """
    out = memoria.search(DOMANDA, k=10, as_of=None)
    return out, sorted((float(i.get("score") or 0.0) for i in out),
                       reverse=True)


def test_la_premessa_il_banco_puo_costruire_taglio_con_migliore_SALVO(memoria):
    """Senza almeno due punteggi DISTINTI non esiste una soglia che tagli
    lasciando in piedi il migliore, e tutto il resto del file misurerebbe
    un'altra cosa. Questa cella e' il controllo positivo del banco stesso."""
    out, scala = _scala(memoria)
    assert len(out) >= 2, (
        f"servono almeno 2 risultati per costruire il caso, ne ho {len(out)}: "
        "il banco non e' valido in questo ambiente, rimisurare prima di "
        "leggere le altre celle")
    assert scala[0] > scala[-1], (
        f"tutti i punteggi sono identici ({scala[0]}): non esiste una soglia "
        "che tagli qualcuno e salvi il migliore")


def test_il_taglio_e_DICHIARATO_anche_quando_il_migliore_sopravvive(memoria):
    """IL CUORE. Soglia fra il primo e il secondo punteggio: il pavimento
    taglia, il migliore resta, l'astensione NON e' dovuta — e prima di questa
    cura chi legge non aveva alcun modo di sapere che era stato tagliato
    qualcosa."""
    out, scala = _scala(memoria)
    soglia = (scala[0] + scala[-1]) / 2

    ris = memoria.search(DOMANDA, k=10, as_of=None, min_relevance=soglia)

    assert len(ris) >= 1, (
        "la soglia doveva salvare il migliore: la premessa del banco non "
        "regge, rimisurare")
    assert len(ris) < len(out), (
        f"la soglia {soglia} non ha tagliato nulla ({len(ris)} di {len(out)}): "
        "il caso non e' quello che questo file misura")

    dichiarato = getattr(ris, "tagliati_dal_pavimento", None)
    assert dichiarato is not None, (
        "il pavimento ha tolto dei fatti e la porta non lo dice: chi legge "
        "vede una risposta buona e non sa che il materiale sotto e' stato "
        "ridotto. E' il difetto per cui esiste questo file")
    assert dichiarato["tagliati"] == len(out) - len(ris), dichiarato
    assert dichiarato["rimasti"] == len(ris), dichiarato
    assert dichiarato["pavimento"] == round(soglia, 4), dichiarato


def test_CONTROLLO_l_astensione_NON_si_accende_se_il_migliore_e_salvo(memoria):
    """⚖️ I DUE SIGNIFICATI RESTANO SEPARATI. `sotto_il_pavimento` dice «non mi
    fido di NIENTE di quello che ho»: qui il migliore e' sopra la soglia, quindi
    non e' dovuto. Se questa cella diventasse rossa, la cura avrebbe reso
    rumorosa l'astensione — che vale proprio perche' e' rara."""
    out, scala = _scala(memoria)
    soglia = (scala[0] + scala[-1]) / 2
    ris = memoria.search(DOMANDA, k=10, as_of=None, min_relevance=soglia)
    assert getattr(ris, "sotto_il_pavimento", None) is None, (
        "l'avviso di astensione si e' acceso su una lettura in cui il migliore "
        "supera il pavimento: due significati diversi nello stesso segnale")


def test_CONTROLLO_senza_taglio_il_campo_resta_SPENTO(memoria):
    """⚠️ LA POPOLAZIONE OPPOSTA. Un campo sempre acceso non informa: e' rumore
    con l'aria di un dato. Senza pavimento non si taglia nulla, e la porta deve
    tacere."""
    ris = memoria.search(DOMANDA, k=10, as_of=None)
    assert getattr(ris, "tagliati_dal_pavimento", None) is None, (
        "nessun pavimento e' stato chiesto, quindi nessun taglio: il campo "
        "acceso qui direbbe il falso")


def test_CONTROLLO_una_soglia_sotto_a_tutti_non_taglia_e_non_dichiara(memoria):
    """⚠️ IL PAVIMENTO C'E' MA NON MORDE: chiesto, e sotto ogni punteggio. Il
    campo deve restare spento — altrimenti misurerebbe «e' stato chiesto un
    pavimento», non «e' stato tagliato qualcosa»."""
    out, scala = _scala(memoria)
    ris = memoria.search(DOMANDA, k=10, as_of=None,
                         min_relevance=max(0.0, scala[-1] / 2))
    assert len(ris) == len(out), (
        f"una soglia sotto il minimo ha tagliato: {len(ris)} di {len(out)}")
    assert getattr(ris, "tagliati_dal_pavimento", None) is None
