"""Un chunk che comincia a metà sezione cita il dato del vicino.

IL DIFETTO, portato da ws5 il 2026-08-04 da utente esterno: un ricercatore
indicizza il proprio paper e chiede «qual è la conducibilità idraulica del
sottobacino 27?». Il prodotto risponde con **score 0.889** — alto, credibile —
e una citazione a offset esatti… che contiene il valore del **sottobacino 26**.

    chunk totali = 30 · che iniziano all'inizio di una SEZIONE = 0 · sfasati = 30

Non è «non trovato», che si vede. È «trovato il vicino», che non si vede. Su un
documento a struttura ripetitiva — paper con tabelle, pazienti, campioni, siti,
lotti, articoli di legge — l'errore è **silenzioso e di una unità**, ed è il
peggiore possibile per un prodotto che vende citazioni verificabili.

LA CAUSA, letta nel codice e non ipotizzata. `chunking._find_boundary` conosce
GIÀ una gerarchia di confini: paragrafo, poi fine frase, poi parola. Mancava il
livello più alto — l'INTESTAZIONE — ed è la stessa classe pagata tre volte
questa settimana: la causa non è mai «manca X», è che X c'era incompleto.

E c'è un secondo pezzo, che spiega perché il difetto è sistematico invece che
occasionale: la funzione cerca l'ULTIMO confine della finestra (``para[-1]``),
cioè taglia il più tardi possibile per riempire il chunk. Quindi
un'intestazione che cade a metà finestra non viene mai presa come taglio: viene
INGLOBATA, e il chunk risultante è «coda della sezione N + testa della N+1».
Con sezioni più corte di ``chunk_size`` questo succede a ogni singolo chunk —
i 30 su 30 di ws5.

⚠️ IL NUMERO CHE INGANNA, e va detto perché è istruttivo: ws5 ha misurato 30
chunk per 30 sezioni. Sembra allineato ed è una coincidenza aritmetica
(17348 byte / ~578 di media). Il conteggio giusto non è quanti chunk ci sono,
ma **quanti cominciano dove comincia una sezione** — di nuovo contare contro
identificare, come i thread di rerank stanotte.
"""
from __future__ import annotations

import pytest

from verimem.chunking import chunk_text

#: Un documento a struttura ripetitiva: la forma di quasi tutti i paper veri.
#: Il sottobacino i ha coefficiente 0,{30+i} — così ogni sezione è distinguibile
#: e si può verificare RIGA PER RIGA quale valore risponde a quale domanda.
SEZIONI = 12
DOC = "\n\n".join(
    f"## Sottobacino {i}\n\n"
    f"Il coefficiente di deflusso del sottobacino {i} vale 0,{30 + i}. "
    f"La conducibilita' idraulica del substrato del sottobacino {i} e' pari a "
    f"{i} per dieci alla meno cinque metri al secondo. "
    f"L'area drenata dal sottobacino {i} misura {100 + i} ettari."
    for i in range(1, SEZIONI + 1)
)


def _intestazioni_in(pezzo: str) -> list[str]:
    return [r for r in pezzo.splitlines() if r.startswith("## ")]


def test_ogni_chunk_comincia_dove_comincia_una_sezione():
    """La misura di ws5, girata al contrario. Il conto che conta non è quanti
    chunk ci sono, ma quanti sono allineati: erano 0 su 30."""
    chunks = chunk_text(DOC, chunk_size=400, overlap=60)
    disallineati = [c for c in chunks if not c.text.lstrip().startswith("## ")]
    assert not disallineati, (
        f"{len(disallineati)} chunk su {len(chunks)} cominciano a meta' "
        f"sezione; il primo comincia con: "
        f"«{disallineati[0].text.lstrip()[:60]}…»")


def test_nessun_chunk_mescola_DUE_sottobacini():
    """Il danno vero: finche' un chunk contiene la coda del 26 e la testa del
    27, una query sul 27 puo' pescarlo e ricevere il valore del 26 — con un
    punteggio alto, perche' il numero 27 nel chunk c'e' davvero."""
    for c in chunk_text(DOC, chunk_size=400, overlap=60):
        titoli = _intestazioni_in(c.text)
        assert len(titoli) <= 1, (
            f"un chunk contiene {len(titoli)} sezioni: {titoli}. "
            f"Una domanda sulla seconda ricevera' i dati della prima")


@pytest.mark.parametrize("n", [3, 7, 11])
def test_il_valore_giusto_sta_nel_chunk_giusto(n):
    """La verifica end-to-end del reclamo: cercando il sottobacino n, il chunk
    che lo contiene deve portare IL SUO coefficiente, non quello del vicino."""
    chunks = chunk_text(DOC, chunk_size=400, overlap=60)
    suoi = [c for c in chunks if f"## Sottobacino {n}\n" in c.text]
    assert suoi, f"nessun chunk contiene la sezione {n}"
    assert f"0,{30 + n}" in suoi[0].text, (
        f"il chunk della sezione {n} non contiene il suo coefficiente "
        f"0,{30 + n}")


def test_l_invariante_di_provenienza_resta_esatta():
    """Il cuore del tier documenti: text[start:end] == chunk.text, altrimenti
    la citazione a offset e' una bugia. Nessuna cura sui confini puo'
    permettersi di romperla."""
    for c in chunk_text(DOC, chunk_size=400, overlap=60):
        assert DOC[c.start:c.end] == c.text


def test_un_testo_SENZA_intestazioni_si_comporta_come_prima():
    """Il verso opposto: la prosa continua — un contratto, un romanzo, una
    trascrizione — non ha intestazioni, e li' il comportamento a paragrafi non
    deve cambiare. Senza questo, la cura sarebbe una regressione travestita."""
    prosa = ("Questa e' una frase di prova. " * 40).strip()
    chunks = chunk_text(prosa, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    for c in chunks:
        assert prosa[c.start:c.end] == c.text


def test_una_sezione_piu_lunga_del_chunk_si_spezza_lo_stesso():
    """Il caso degenere che non deve bloccare il loop: se una sezione da sola
    supera chunk_size, va spezzata ai confini interni — l'allineamento e' una
    preferenza, non una gabbia."""
    lunga = "## Unica\n\n" + ("Frase lunga di riempimento. " * 60)
    chunks = chunk_text(lunga, chunk_size=300, overlap=50)
    assert len(chunks) > 1, "una sezione lunga non e' stata spezzata"
    for c in chunks:
        assert lunga[c.start:c.end] == c.text
