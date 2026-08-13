"""Un numero su un prodotto altrui deve dire CHI l'ha misurato — e qui si prova.

PERCHE' QUESTO FILE ESISTE. Il 2026-08-12 il mandato e' stato: *«finche' il banco
non esiste, nessuno scrive da nessuna parte che siamo migliori di qualcuno»*.
Il giorno dopo il collaudo del wheel 0.7.5 segnava FALSA una sola voce — «il
pacchetto non attribuisce numeri ad altri prodotti» — e la discussione si e'
concentrata su **una** tabella del README. Un `grep` su TUTTO il file dice che le
menzioni sono **7 su TRE superfici**: la tabella «Capability» (righe ~480-489),
la tabella «Metric» (~445-451) e **un numero sciolto nel testo** (~91,
``vs mem0's 10/10``) che il taglio di una colonna non avrebbe toccato.

IL CRITERIO NON E' «e' un numero?», E' **CHI L'HA MISURATO**:

    numero LORO, citato come loro ....... e' una CITAZIONE ............ AMMESSO
    numero NOSTRO sul LORO prodotto ..... e' una RIVENDICAZIONE ....... VIETATO
                                          (senza un banco pubblicato)

La differenza non e' formale. La tabella «Metric» porta in intestazione
``MemOS (self-reported)`` e nel testo sotto dichiara *«parity, not a win»*: due
dei nostri numeri sono **sotto** i loro. E' l'unico posto del README in cui
diciamo di NON essere migliori — cioe' esattamente cio' che il mandato chiede.
Una pulizia cieca «via tutto cio' che nomina un concorrente» la cancellerebbe,
applicando la regola per ottenerne l'opposto.

DA QUI I DUE TEST, e sono due apposta — le due popolazioni, non una:

  1. ``...senza_la_sua_fonte``   il sensore ACCESO: oggi le violazioni ci sono,
     quindi il test e' ``xfail(strict=True)``. Non e' un sensore scollegato:
     strict fa diventare **ROSSO** il giorno in cui le righe spariscono, cosi'
     chi le toglie e' costretto a togliere anche il marcatore — il guardiano si
     arma da solo, senza che nessuno debba ricordarsene.
  2. ``...i_numeri_che_la_fonte_dichiara``   il sensore che deve TACERE: verde
     oggi e verde domani. Diventa rosso se qualcuno «pulisce» il README a
     tappeto. Misurato solo sulla popolazione dei positivi, il rilevatore del
     test 1 sembrerebbe ottimo anche se segnalasse tutto.

L'etichetta della fonte sta nell'INTESTAZIONE della tabella, non nella riga dei
numeri: ``| ... | 0.672 |`` non contiene la parola «MemOS». Percio' il criterio
si applica alla riga PIU' la sua intestazione — il livello a cui si misura
decide il verdetto, e la riga da sola darebbe la risposta sbagliata.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

README = Path(__file__).resolve().parents[1] / "README.md"

#: I prodotti di terzi nominati nel README. Non e' un elenco del mercato: e'
#: l'elenco di chi compare QUI, che e' l'unica cosa che questo test governa.
CONCORRENTI = ("mem0", "zep", "memos", "langmem", "letta", "memgpt")

#: Marcatori che dichiarano che il numero e' della FONTE, non nostro.
MARCATORI_DI_FONTE = ("self-reported", "self reported", "reported by", "their own",
                      "as published", "per their")

_CIFRA = re.compile(r"\d")
#: Codice, link e path NON sono affermazioni: `evolution_moat_vs_mem0.py` nomina
#: mem0 e contiene uno zero, e non attribuisce niente a nessuno.
_CODICE = re.compile(r"`[^`]*`")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _prosa(riga: str) -> str:
    """La riga senza codice e senza URL: cio' che un lettore legge come claim."""
    return _CODICE.sub(" ", _LINK.sub(r"\1", riga))


def _righe_con_intestazione() -> list[tuple[int, str, str]]:
    """``(numero, riga, intestazione della tabella a cui appartiene)``.

    Fuori da una tabella l'intestazione e' la stringa vuota. Una tabella
    markdown e' riconosciuta dalla riga di separazione ``|---|---|``: quella
    PRIMA e' l'intestazione, e vale fino alla prima riga che non inizia con '|'.
    """
    testo = README.read_text(encoding="utf-8").splitlines()
    fuori = ""
    intestazione = fuori
    out: list[tuple[int, str, str]] = []
    for i, riga in enumerate(testo, start=1):
        spoglia = riga.strip()
        if not spoglia.startswith("|"):
            intestazione = fuori
            out.append((i, riga, fuori))
            continue
        if set(spoglia) <= set("|-: "):  # la riga di separazione
            intestazione = testo[i - 2] if i >= 2 else fuori
            out.append((i, riga, intestazione))
            continue
        out.append((i, riga, intestazione))
    return out


def _senza_i_nomi(testo: str) -> str:
    """Il testo con i nomi dei prodotti rimossi.

    ⚠️ Serve, e la prima versione di questo file non lo faceva: **«mem0»
    contiene la cifra 0**. Cercando la cifra nella riga intera, l'intestazione
    ``| Capability | Verimem (measured) | mem0 / Zep / MemOS |`` risultava
    «un numero attribuito a mem0», e con lei tre righe i cui unici numeri sono
    NOSTRI (1.000, 0.96–0.97, 0.17→0.92). Sette righe segnalate invece di due:
    il verdetto sembrava giusto, la ragione era sbagliata. Se il prodotto si
    fosse chiamato «memzero» il difetto sarebbe rimasto invisibile.
    """
    for c in CONCORRENTI:
        testo = re.sub(re.escape(c), " ", testo, flags=re.IGNORECASE)
    return testo


def _violazioni() -> list[tuple[int, str]]:
    """Celle che attribuiscono una cifra a un prodotto altrui senza dire di chi e'.

    ⚠️ La granularita' e' la **cella**, non la riga: in una tabella a tre colonne
    la riga tiene insieme i NOSTRI numeri e il giudizio sul loro prodotto, e
    chiedere «questa riga ha una cifra?» risponde di si' per la colonna
    sbagliata. Il livello a cui si misura decide il verdetto.

    📌 Governa i NUMERI, ed e' cio' che la voce di collaudo enuncia
    (*«non attribuisce numeri ad altri prodotti»*). Le celle qualitative senza
    cifra — «no write gate», «served as-is», «absent or partial» — sono
    affermazioni comparative pure: un tema adiacente, che questo file **non**
    copre e non pretende di coprire.
    """
    fuori = []
    for numero, riga, intestazione in _righe_con_intestazione():
        prosa = _prosa(riga)
        in_tabella = prosa.strip().startswith("|")
        if in_tabella and prosa.strip() == _prosa(intestazione).strip():
            continue  # l'intestazione non attribuisce: nomina le colonne
        celle = prosa.split("|") if in_tabella else [prosa]
        titoli = _prosa(intestazione).split("|") if in_tabella else [""]
        for i, cella in enumerate(celle):
            # ⚠️ una cella EREDITA il nome della sua colonna: «| ... | 0.672 |»
            # non contiene la parola «MemOS», che sta nell'intestazione. Senza
            # questa eredita' il rilevatore saltava quelle righe PRIMA di
            # guardare il marcatore — e il marcatore, misurato, non faceva
            # alcun lavoro: toglierlo non cambiava di una riga il risultato.
            colonna = titoli[i] if i < len(titoli) else ""
            contesto = f"{cella} {colonna}".lower()
            if not any(c in contesto for c in CONCORRENTI):
                continue
            if any(m in contesto for m in MARCATORI_DI_FONTE):
                continue  # e' una citazione: il numero e' dichiarato loro
            if not _CIFRA.search(_senza_i_nomi(cella)):
                continue
            fuori.append((numero, cella.strip()[:110]))
            break
    return fuori


@pytest.mark.xfail(
    strict=True,
    reason=(
        "debito noto al 2026-08-13: il README attribuisce cifre a mem0 senza "
        "dichiararne la fonte (~riga 91 «vs mem0's 10/10», ~riga 485 «mem0: "
        "40/60»). strict=True: quando quelle righe spariscono questo test "
        "diventa ROSSO, e chi le toglie deve togliere anche questo marcatore — "
        "e' cosi' che il guardiano si arma da solo."
    ),
)
def test_nessun_numero_e_attribuito_a_un_prodotto_altrui_senza_la_sua_fonte() -> None:
    fuori = _violazioni()
    assert not fuori, (
        "numeri attribuiti a un prodotto altrui senza dichiarare CHI li ha "
        "misurati:\n" + "\n".join(f"  README.md:{n}  {t}" for n, t in fuori)
    )


def test_il_rilevatore_non_segnala_i_numeri_che_la_fonte_dichiara() -> None:
    """La popolazione opposta: cio' che deve restare.

    La tabella «Metric» cita ``MemOS (self-reported)`` e sotto dichiara *«parity,
    not a win»* — due nostri numeri sono INFERIORI ai loro. E' l'unico punto del
    README dove diciamo di non essere migliori. Se un domani qualcuno togliesse
    a tappeto ogni riga che nomina un concorrente, applicherebbe il mandato del
    12/08 ottenendo l'opposto di cio' che chiede: questo test glielo impedisce.
    """
    testo = README.read_text(encoding="utf-8")
    assert "self-reported" in testo, (
        "sparita l'unica tabella comparativa che cita la fonte altrui e ci mette "
        "SOTTO («parity, not a win»): non e' cio' che il mandato chiede di togliere"
    )

    segnalate = {n for n, _ in _violazioni()}
    righe = testo.splitlines()
    numeri_dichiarati = [
        i for i, r in enumerate(righe, start=1)
        if r.strip().startswith("|") and re.search(r"0\.(672|797)", r)
    ]
    assert numeri_dichiarati, (
        "precondizione: la tabella deve ancora riportare i numeri di MemOS "
        "(0.672 end-to-end, 0.797 extraction). Se cambiano, aggiorna QUESTO test"
    )
    for n in numeri_dichiarati:
        assert n not in segnalate, (
            f"README.md:{n} — il rilevatore segnala un numero che la sua fonte "
            f"DICHIARA («self-reported» in intestazione). Un criterio che non "
            f"distingue la citazione dalla rivendicazione cancella la pagina "
            f"piu' onesta che abbiamo"
        )
