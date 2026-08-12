"""`_senza_diacritici("베로나")` restituiva una parola che non esisteva più.

⚠️ È LA TRAPPOLA PERFETTA, e va detto prima di tutto il resto: **le due
stringhe si stampano identiche.** Nessuna rilettura del codice, nessuna
ispezione a occhio dell'output, nessun `print` può trovarla. Servono `len()` o
i codepoint::

    _senza_diacritici("베로나")  ->  "베로나"        a vedersi, identica
    len(originale) = 3             len(risultato) = 6
    0xbca0 0xb85c 0xb098     ->    0x1107 0x1166 0x1105 0x1169 0x1102 0x1161
    "베로나" in testo_originale  ->  False

La funzione decomponeva in NFKD e filtrava i **combining marks**, senza mai
ricomporre. Per l'italiano e il tedesco funziona — il segno viene TOLTO, e
«città» → «citta» è una stringa piena e legittima. Ma l'hangul si decompone in
**jamo**, che combining marks non sono: sopravvivevano al filtro e restavano
separati per sempre.

⇒ Ogni token coreano prodotto da `content_tokens` era una stringa che **non si
trova nel testo da cui è stata estratta**.

═══ IL DANNO, misurato ALLA PORTA ═══

`_content_overlap` di una frase coreana confrontata con **se stessa** — il
massimo che quel criterio possa dare — valeva **0.00**. Quindi in coreano ogni
guardia di stesso-soggetto era cieca e `validate_claim` non poteva confermare
nulla: `unknown` su un claim identico al fatto in memoria.

🔑 STESSA CLASSE DEI DUE DIFETTI CURATI POCO PRIMA, ed è la terza volta oggi:
**due lati dello stesso confronto normalizzano in modo diverso.** Prima era la
dieresi tedesca (`content_tokens` toglieva i diacritici, lo scope della
negazione no); qui è la forma Unicode. La differenza è che questa non si vede
nemmeno guardando.

═══ ⚠️ IL LIMITE CHE RESTA, misurato e NON curato ═══

Curata la normalizzazione, il coreano conferma ma **produce ancora un falso
conflitto** fra due frasi che non c'entrano nulla::

    «베로나 창고에는 480개의 팔레트가 있습니다»   (480 pallet nel magazzino)
    «서버에 320개의 연결이 있습니다»             (320 connessioni sul server)
    numeric_conflict -> ('개의', 480.0, 320.0)      ⇐ falso positivo

A/B nella stessa esecuzione: **è pre-esistente**, con e senza la ricomposizione
NFC il risultato è identico. La causa è doppia e nessuna delle due è Unicode:

· `개의` è il **contatore generico** coreano («pezzi di»), non la grandezza. Il
  sostantivo vero sta DOPO — `480개의 팔레트가` è «480 [contatore] pallet» — e
  il parser prende la parola subito dopo il numero.
· l'unica parola condivisa dalle due frasi è `있습니다`, cioè **il verbo**, che
  fa da falso soggetto condiviso alla guardia.

📌 È lo stesso difetto del giapponese curato in `66583acc` (l'unità che si
porta dentro il verbo), con i ruoli invertiti: là il verbo entrava nell'unità,
qui il verbo è l'unica cosa condivisa e l'unità è un contatore vuoto. Dichiarato
qui invece che taciuto — la cura richiede di sapere dove sta il sostantivo, che
non è una normalizzazione.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

import pytest

from verimem.quantity_match import _senza_diacritici, content_tokens
from verimem.validate_claim import validate_claim


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = "t"
    confidence: float = 0.9
    source_episodes: list = field(default_factory=list)


class _Agent:
    def __init__(self, facts: list[_Fact]) -> None:
        self.semantic = type(
            "_S", (), {"search_facts": lambda _s, _q, **_k: facts})()


FRASE_KO = "베로나 창고에는 480개의 팔레트가 있습니다."


@pytest.mark.parametrize("parola", ["베로나", "창고에는", "팔레트가", "있습니다"])
def test_una_parola_coreana_resta_LA_STESSA_STRINGA(parola):
    """Il cuore, e l'asserzione è su `len` **apposta**: confrontare le due
    stringhe a occhio non distingue nulla, ed è per questo che il difetto è
    sopravvissuto. Il test misura ciò che l'occhio non vede."""
    fuori = _senza_diacritici(parola.lower())
    assert fuori == parola.lower(), "la parola è cambiata"
    assert len(fuori) == len(parola), (
        f"«{parola}» esce decomposta: {len(parola)} caratteri diventano "
        f"{len(fuori)} — {[hex(ord(c)) for c in fuori]}")
    assert unicodedata.is_normalized("NFC", fuori), "il risultato non è in NFC"


def test_i_token_si_trovano_nel_testo_da_cui_vengono():
    """L'invariante che il difetto rompeva, ed è quello che conta davvero: un
    token estratto da una frase deve poter essere ritrovato in quella frase.
    Senza, ogni confronto costruito sui token è cieco senza dare errore."""
    for t in content_tokens(FRASE_KO):
        assert t in FRASE_KO.lower(), (
            f"il token «{t}» non esiste nella frase da cui è stato estratto")


@pytest.mark.parametrize("lingua,frase", [
    ("KO", FRASE_KO),
    ("EN", "The Verona warehouse contains 480 pallets."),
    ("DE", "Das Lager in Verona enthält 480 Paletten."),
    ("RU", "Склад в Вероне содержит 480 паллет."),
    ("JA", "ヴェローナの倉庫には480パレットあります。"),
])
def test_ALLA_PORTA_il_claim_identico_e_supportato(lingua, frase):
    """Il coreano è quello nuovo; gli altri quattro sono il presidio, perché
    una cura sulla normalizzazione tocca OGNI lingua che passa di lì."""
    verdetto = validate_claim(_Agent([_Fact("f1", frase)]), frase)["verdict"]
    assert verdetto == "supported", f"[{lingua}] non confermato: {verdetto}"


@pytest.mark.parametrize("originale,atteso", [
    ("città", "citta"),
    ("Stück", "stuck"),
    ("verfügbar", "verfugbar"),
])
def test_i_DIACRITICI_veri_continuano_a_cadere(originale, atteso):
    """⚠️ IL VERSO OPPOSTO. La ricomposizione NFC non deve rimettere gli accenti
    che la funzione esiste per togliere: «città» e «citta» devono restare la
    stessa parola, altrimenti la cura spegne il motivo per cui la funzione c'è."""
    assert _senza_diacritici(originale.lower()) == atteso
