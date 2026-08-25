"""«The Rovigo warehouse» non produceva NESSUNA entita', e il fatto spariva.

Misurato il 2026-08-25 da @ws6 (8 casi su 8) e riprodotto qui prima della cura:
un nome proprio in posizione ATTRIBUTIVA — la forma prenominale normale
dell'inglese, «The <Nome> <sostantivo>» — viene perso per intero.

    The Rovigo warehouse was audited in May.   ->  ['May']      <- e May e' una DATA
    The Frankfurt office moved ...             ->  []
    ... 8 casi su 8 persi

La causa NON e' la regola sentence-initial (`_SENTENCE_START` non riconosce
`'The '`: l'avevo scritto e l'ho ritirato). E' il filtro qui sotto::

    first_word = name.split()[0].lower()
    if first_word in _STOPWORDS:
        continue                      # <- scarta l'INTERO match, nome compreso

Il match e' «The Rovigo»: la prima parola e' un determinante, e con essa se ne
va il nome proprio. Il danno non e' cosmetico — un fatto senza entita' non ha
niente con cui essere distinto da un altro, e in verimem due fatti EN che
parlano di magazzini DIVERSI si supersedono a vicenda (uno dei due sparisce).

⚖️ LE DUE POPOLAZIONI, misurate ENTRAMBE prima di consegnare, perche' su una
sola ogni criterio sembra ottimo (regola di casa) — e perche' e' cio' che
l'ordine di lavoro chiede esplicitamente: «con la misura dei falsi positivi
PRIMA di consegnare (`The Monday meeting` non deve diventare un'entita')».

    PRIMA della cura:   A 0/8 estratti      ·   B 1/8 falsi positivi
    DOPO la cura:       A 8/8               ·   B 0/8

📌 Il falso positivo di B esisteva GIA' prima di questa cura e non e' stato
introdotto da lei: «A Tuesday standup» -> ['Tuesday'], mentre «The Monday
meeting» -> []. La differenza e' che `the` sta in `_STOPWORDS` e `a` no —
la stessa classe di difetto (una lista incompleta), nello stesso punto di
codice. Lo strip del determinante lo chiude di conseguenza: il resto passa
di nuovo dal controllo delle date, che prima veniva saltato.

⚠️ IL PREZZO DI QUESTA CURA, misurato e scritto qui perche' non lo scopra
qualcun altro fra un mese. Tolto il determinante, «The <Maiuscola>» a inizio
frase e' AMBIGUA e la struttura non la disambigua::

    The Rovigo warehouse ...   -> Rovigo    <- voluto
    The Board approved it.     -> Board     <- NON voluto, e introdotto da me
    The Report is ready.       -> Report    <- idem

Prima della cura questi due davano `[]`, perche' lo scarto del determinante
si portava via tutto — cioe' erano «giusti per la ragione sbagliata».
Separarli richiede di sapere che «Rovigo» e' un nome proprio e «Board» no:
un DIZIONARIO della lingua, che in questa casa e' gia' una strada falsificata
(vedi il commento su `acronym` in `entity_extract_lite.py`, stessa questione
per le parole urlate). Ho provato il criterio strutturale «dopo il nome deve
esserci un sostantivo, non un verbo»: separa Board/Report da Rovigo, ma la
lista dei verbi lessicali e' aperta e la lista chiusa (ausiliari) non prende
«approved». Non consegno un criterio che non regge.

TAGLIA MISURATA, e la popolazione e' dichiarata perche' e' piccola: sui **38
fatti inglesi** del set reale `~/.engram/local_gate/corpus_labels_v2.jsonl`
il confronto fra la versione di HEAD e questa da' **0 entita' nuove e 0
perse** — la forma «The <Maiuscola>» non compare li'. E' un dato onesto e
POCO informativo: dice che la cura e' neutra su quel corpus, non che sia
sicura in generale.

⚖️ CONSEGNATA COMUNQUE, e il motivo e' l'asimmetria del danno: il difetto
curato CANCELLA un fatto vero in silenzio (due magazzini EN diversi si
supersedono), l'effetto collaterale AGGIUNGE un nodo spurio al grafo. Il
primo perde informazione, il secondo la sporca. Se chi ha il fronte del
grafo misura che il rumore costa piu' della perdita, questa cura va rivista:
il numero da guardare e' l'impatto sul PPR, e non l'ho misurato.

🔬 LIVELLO DELLA MISURA, dichiarato: `extract_entities_lite` e' la funzione
pubblica del modulo (`__all__`), ed e' regex pura — nessun embedder, nessun
coseno. Questo file puo' quindi girare SOTTO pytest senza il problema dello
stub SHA-256 di `conftest`, ed e' il motivo per cui non e' un banco esterno.
"""
from __future__ import annotations

import pytest

from verimem.entity_extract_lite import extract_entities_lite

# I casi di @ws6, ripresi TESTUALMENTE dal suo referto delle 21:58 e non
# reinventati da me: chi scrive la cura non e' un buon autore dei propri casi.
ATTRIBUTIVI = [
    ("The Rovigo warehouse was audited in May.", "Rovigo"),
    ("The Frankfurt office moved to a new building.", "Frankfurt"),
    ("The Stripe integration failed twice.", "Stripe"),
    ("The Ancona depot reported a shortage.", "Ancona"),
    ("The Boeing contract was renewed.", "Boeing"),
    ("The Dublin team shipped on time.", "Dublin"),
    ("The Rossi report was filed late.", "Rossi"),
    ("The Milan branch closed early.", "Milan"),
]

# La popolazione OPPOSTA: un determinante seguito da una parola che NON e' un
# nome proprio. Se la cura si limitasse a togliere il determinante, questi
# diventerebbero entita' — ed e' esattamente il modo in cui una cura giusta
# sulla popolazione A rompe il prodotto sulla B.
NON_ENTITA = [
    "The Monday meeting was postponed.",
    "The Friday deploy went fine.",
    "The March review is done.",
    "The Sunday brunch was cancelled.",
    "The quarterly report is ready.",
    "The next release is blocked.",
    "A Tuesday standup was added.",
    "The December audit closed.",
]


def _nomi(testo: str) -> list[str]:
    return [e["name"] for e in extract_entities_lite(testo)]


@pytest.mark.parametrize("testo,atteso", ATTRIBUTIVI)
def test_il_nome_proprio_attributivo_sopravvive(testo: str, atteso: str):
    nomi = _nomi(testo)
    assert any(atteso == n or atteso in n.split() for n in nomi), (
        f"«{atteso}» perso: il determinante iniziale ha portato via il nome "
        f"proprio con se'.\n  testo: {testo}\n  estratte: {nomi}")


@pytest.mark.parametrize("testo", NON_ENTITA)
def test_CONTROLLO_un_determinante_non_promuove_una_parola_comune(testo: str):
    """La difesa. Senza questi, la cura di sopra si misura su meta' del
    problema e sembra perfetta."""
    nomi = _nomi(testo)
    assert nomi == [], (
        f"falso positivo: «{testo}» non contiene un nome proprio, ma "
        f"l'estrattore ha prodotto {nomi}")
