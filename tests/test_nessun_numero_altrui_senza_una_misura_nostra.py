"""Il prodotto anti-confabulazione pubblicava giudizi sui concorrenti senza fonte.

⚠️ È IL PARADOSSO CHE IL MANDATO DEL 2026-08-12 CHIEDE DI CHIUDERE PER PRIMO:
*«se affermiamo di essere meglio di qualcuno senza un banco che lo provi, stiamo
facendo esattamente ciò che il nostro prodotto vieta»*. Un'affermazione su un
prodotto terzo, senza misura, dentro il sistema che quarantina i fatti senza
fonte, **entrerebbe quarantinata dal nostro stesso gate**.

Trovato in tre superfici, e le prime due dicevano la stessa cosa in due posti —
la classe più ricorrente di questa casa::

    mcp_server.py:4885   description MCP, LETTA DALL'AGENTE A RUNTIME
        «mem0/Zep have no status/supersession/contradiction so every hit is
         unverified by construction (~1.0)»
    hallucination_rate.py:3   docstring del modulo, stessa affermazione
    conversation_ingest.py:161
        «MemOS extraction is 79.7 and consolidation trades ~2pp recall»

🔑 IL DIFETTO NON È IL CONFRONTO, È IL SUO STATUTO. «by construction» non è una
misura: è una deduzione da una premessa («non espongono il campo»), scritta dove
un lettore la prende per un dato. E la deduzione è pure sbagliata nel verso che
ci conviene — se un sistema non espone un verdetto di affidabilità, quella
metrica su di lui è **indefinita**, non alta.

📌 `79.7` è il caso più netto: un numero a tre cifre significative attribuito a
un prodotto che non abbiamo mai misurato noi.

═══ PERCHÉ IL CRITERIO GUARDA I NUMERI E NON I NOMI ═══

Nominare un concorrente è legittimo e spesso necessario: `client.py` dice
«mem0/Zep ergonomics» per spiegare perché un alias esiste, e
`entity_extract_lite.py` usa «mem0» come **esempio di token** con le cifre
dentro. Vietare il nome sarebbe un divieto di parola — aggirabile, e per giunta
dannoso.

⇒ La regola è più stretta e verificabile: **nessun numero attribuito a un
prodotto terzo** in una superficie di codice, finché non esiste un banco nostro
che lo produca. Un giudizio si può discutere; un numero senza misura è una
citazione senza fonte, che è esattamente la cosa che questo prodotto esiste per
fermare.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]

#: I prodotti nominati nel repo. È una lista di NOMI PROPRI — non c'è criterio
#: strutturale per un nome proprio, e va aggiornata quando se ne cita un altro.
CONCORRENTI = ("mem0", "zep", "memos", "supermemory", "letta", "memgpt")

#: ⚠️ LA FORMA DEL NUMERO CONTA, e questa riga è la seconda versione: la prima
#: cercava QUALUNQUE cifra entro 70 caratteri dal nome e produceva **17 rossi,
#: tutti falsi** — versioni (`0.7.5`), indici di roadmap (`#10`), le cifre
#: dentro i nomi stessi (`mem0`, `gpt4o`, `qwen3`). Il banco qui sotto l'ha
#: fermata prima che la consegnassi: è il motivo per cui esiste.
#:
#: 🔑 Un'attribuzione ha una FORMA riconoscibile — un valore **misurato**:
#: decimale (`79.7`), approssimato (`~1.0`), percentuale (`12%`), punti
#: (`2pp`). Un intero nudo accanto a un nome non è una misura: è quasi sempre
#: una versione o un riferimento.
_NUMERO = r"(?:~\s*\d+(?:[.,]\d+)?|\d+[.,]\d+|\d+\s*(?:%|pp\b|punti\b|points\b))"

#: ⚠️ E LA FINESTRA È TARATA SUL CASO CHE HA ORIGINATO IL PRESIDIO, non a
#: occhio. A 45 caratteri il banco restava rosso su una riga sola — proprio la
#: description MCP da cui è nato tutto, dove fra il nome e il numero ci sono
#: sette parole («…every hit is unverified by construction (~1.0)»). Un
#: guardiano che non prende il caso che lo ha fatto nascere non serve a niente.
#:
#: 🔑 Allargare è sicuro perché il filtro che elimina i falsi non è la distanza,
#: è la FORMA del numero.
#:
#: ⚠️⚠️ E IL VALORE È MISURATO, NON STIMATO — ci ho provato due volte a occhio,
#: 45 e poi 65, e il banco è rimasto rosso entrambe le volte. Misurando la
#: distanza vera fra il nome e il numero nei tre casi reali::
#:
#:     «mem0/Zep … by construction (~1.0)»        distanza = 91
#:     «MemOS extraction is 79.7 …»               distanza = 15
#:     «beats mem0 by 12 points on recall»        distanza =  4
#:
#: La mia stima migliore era sotto di un terzo. Un numero che si può misurare
#: non si indovina — vale per le soglie quanto per i fatti.
_FINESTRA = 100


def _accuse_numeriche(testo: str) -> list[str]:
    trovate = []
    for nome in CONCORRENTI:
        for verso in (
            rf"{nome}[^.\n]{{0,{_FINESTRA}}}?{_NUMERO}",
            rf"{_NUMERO}[^.\n]{{0,{_FINESTRA}}}?{nome}",
        ):
            for m in re.finditer(verso, testo, re.IGNORECASE):
                frammento = m.group(0)
                # un numero DENTRO il nome non è un'attribuzione: «mem0» ha uno
                # zero, «gpt4o» un quattro. Serve un numero SEPARATO dal nome.
                senza_nome = re.sub(nome, " ", frammento, flags=re.IGNORECASE)
                if re.search(r"\d", senza_nome):
                    trovate.append(frammento.strip())
    return trovate


#: Le superfici di codice che un lettore — umano o agente — incontra.
SORGENTI = sorted(
    p for p in (_RADICE / "verimem").glob("*.py")
    if p.name != "__init__.py"
)


@pytest.mark.parametrize("percorso", SORGENTI, ids=lambda p: p.name)
def test_nessun_numero_e_attribuito_a_un_prodotto_terzo(percorso):
    """Il cuore. Non vieta di nominare un concorrente: vieta di appiccicargli
    una cifra che non abbiamo misurato noi.

    Se un giorno il banco comparativo esiste ed è stato eseguito, questo test va
    aggiornato indicando DOVE sta la misura — non tolto.
    """
    accuse = _accuse_numeriche(percorso.read_text(encoding="utf-8", errors="ignore"))
    assert not accuse, (
        f"{percorso.name} attribuisce un numero a un prodotto terzo senza una "
        f"misura nostra: {accuse[:3]}"
    )


@pytest.mark.parametrize("frammento,e_accusa", [
    # ⚠️ I DUE CASI VERI, COPIATI DAL REPO E NON PARAFRASATI. La prima stesura
    # di questa riga era abbreviata da me con dei puntini di sospensione — e il
    # banco restava rosso non perché il criterio fosse debole, ma perché la mia
    # abbreviazione conteneva un punto e il criterio non attraversa le frasi.
    # 🔑 Un caso di banco riscritto a memoria misura la memoria di chi lo
    # scrive, non il codice: si copia dalla fonte, sempre.
    ("MemOS extraction is 79.7 and consolidation trades ~2pp recall", True),
    ("mem0/Zep have no status/supersession/contradiction so every hit is "
     "unverified by construction (~1.0)", True),
    ("beats mem0 by 12 points on recall", True),
    # ⚠️ la popolazione opposta: nomi legittimi, senza cifre attribuite
    ("Alias for users who expect a Client name (mem0/Zep ergonomics).", False),
    ("tech token with digits: mem0, gpt4o, qwen3", False),
    ("mem0/Zep expose add(messages) / search(query)", False),
])
def test_IL_RICONOSCITORE_separa_l_accusa_dalla_menzione(frammento, e_accusa):
    """⚠️ IL BANCO DEL MISURATORE, e serve perché «mem0» contiene una cifra: un
    riconoscitore ingenuo segnalerebbe ogni menzione del nome.

    Le ultime tre righe sono i casi veri del repo che DEVONO restare: spiegano
    un'ergonomia, un esempio di tokenizzazione e una firma di API — nessuna
    attribuisce niente a nessuno."""
    assert bool(_accuse_numeriche(frammento)) is e_accusa, frammento
