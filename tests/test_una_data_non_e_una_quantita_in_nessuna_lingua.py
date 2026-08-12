"""«10 августа», «8月10日»: la cura delle date valeva solo per cinque lingue.

⚠️ QUESTO FILE NASCE DA UN DIFETTO CONSEGNATO COME CURATO. Il 2026-08-10 le date
sono state escluse dalle quantità (`822aac2a`) e il commit diceva *«i nomi dei
mesi coprono cinque lingue»* — come se fosse una copertura. Il perimetro chiesto
è di sette: inglese, italiano, francese, spagnolo, **russo, cinese, giapponese**.
Misurato il giorno dopo, prima di scrivere questa cura::

    IT  «10 agosto»   -> data riconosciuta, quantità []
    EN  «10 August»   -> data riconosciuta, quantità []
    ISO 2026-08-10    -> data riconosciuta, quantità []
    RU  «10 августа»  -> data NON vista, estrae ('августа', 10.0)
    ZH  «8月10日»      -> data NON vista, estrae ('', 8.0) e ('日运行失败', 10.0)
    JA  «8月10日»      -> data NON vista, estrae ('', 8.0) e ('日に実行が失敗しました', 10.0)

🔑 E nelle due lingue senza spazi il danno era **il doppio**: il secondo numero
si porta dietro il resto della frase come falsa unità, perché non c'è uno spazio
a fermarlo. Il difetto era peggiore proprio dove non era stato guardato.

═══ LE DUE STRADE, e una non ha bisogno di vocabolario ═══

· **Russo**: serve la lista dei mesi, al **genitivo** — nelle date si scrive «10
  августа», cioè «10 di agosto». È una lista, e come tutte le liste invecchia.
· **Cinese e giapponese**: **nessuna lista**. La data si scrive `8月10日` in
  entrambe le lingue, e 月 (mese) e 日 (giorno) sono gli stessi caratteri. Il
  criterio è **posizionale**, copre due lingue con un pattern solo e non dipende
  da un vocabolario.

⚖️ È la differenza che conta per il resto del prodotto: dove esiste un criterio
posizionale, **non si scrive una lista**. Le liste sono la classe di errore più
ricorrente di questa casa — *liste monolingue in un prodotto mondiale* — e il
commit del 10/08 la citava dicendo di averla evitata, mentre la stava facendo.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities

# (etichetta, frase) — la stessa informazione in sette lingue e tre notazioni.
DATE = [
    ("IT",  "Il 10 agosto il run e' fallito."),
    ("EN",  "On 10 August the run failed."),
    ("FR",  "Le 10 aout l'execution a echoue."),
    ("ES",  "El 10 agosto la ejecucion fallo."),
    ("RU",  "10 августа запуск не удался."),
    ("ZH",  "8月10日运行失败。"),
    ("JA",  "8月10日に実行が失敗しました。"),
    ("JA-Y", "2026年8月10日に実行が失敗しました。"),
    ("ISO", "Il 2026-08-10 il run e' fallito."),
]


@pytest.mark.parametrize("lingua,frase", DATE, ids=[d[0] for d in DATE])
def test_una_data_non_produce_quantita_in_nessuna_delle_sette_lingue(lingua, frase):
    """Il cuore: una data non è una misura, in nessuna lingua del perimetro.

    ⚠️ RU, ZH e JA sono i tre casi che il 10/08 erano rimasti fuori. Gli altri
    sei sono qui perché una cura che aggiunge lingue **può romperne una che
    funzionava**, ed è successo abbastanza volte in questa casa da doverlo
    presidiare invece di sperarci.
    """
    assert extract_quantities(frase) == set(), (
        f"[{lingua}] «{frase}» produce {sorted(extract_quantities(frase))}")


@pytest.mark.parametrize("lingua,frase,atteso", [
    ("IT", "Il magazzino contiene 480 pallet.", 480.0),
    ("EN", "The warehouse holds 480 pallets.", 480.0),
    ("RU", "Склад содержит 480 паллет.", 480.0),
    ("ZH", "维罗纳仓库有480个托盘。", 480.0),
    ("JA", "ヴェローナの倉庫には480パレットあります。", 480.0),
    ("dec", "La tolleranza e' 0.125 mm.", 0.125),
])
def test_CONTROLLO_POSITIVO_le_quantita_vere_sopravvivono_in_ogni_lingua(
        lingua, frase, atteso):
    """⚠️ LA POPOLAZIONE OPPOSTA, e qui non è una formalità.

    Un criterio che togliesse le date allargandosi troppo spegnerebbe il
    rilevatore invece di affinarlo — e in cinese e giapponese, dove non c'è uno
    spazio a delimitare, un pattern goloso mangia mezza frase. Se questi cadono,
    la cura sopra è da ritirare.
    """
    valori = {v for _u, v in extract_quantities(frase)}
    assert atteso in valori, f"[{lingua}] «{frase}» ha perso il valore vero"


def test_il_criterio_CJK_e_POSIZIONALE_e_non_una_lista():
    """Perché questa cura non invecchia come le altre, scritto dove si verifica.

    Cinese e giapponese condividono 月 e 日: un pattern solo copre due lingue e
    non dipende da un vocabolario. Se un giorno questa asserzione cadesse
    vorrebbe dire che qualcuno ha sostituito il criterio posizionale con una
    lista di parole — che è il modo in cui questa classe di difetti è tornata
    ogni volta.
    """
    from verimem.quantity_match import _DATA_RE
    assert _DATA_RE.search("8月10日")
    assert _DATA_RE.search("2026年8月10日")
    # e la stessa forma dentro una frase giapponese, non isolata
    assert _DATA_RE.search("8月10日に実行が失敗しました。")
