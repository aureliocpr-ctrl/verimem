"""In hindi il gate non estraeva NESSUNA parola. Le vocali non sono lettere.

⚠️ Riguarda oltre un miliardo di parlanti, e il sintomo era il più muto
possibile: `content_tokens` restituiva **l'insieme vuoto** su qualunque frase
hindi, bengali o tamil. Con zero token ogni guardia di stesso-soggetto è cieca,
`_content_overlap` di una frase con SE STESSA vale 0.00, e `validate_claim`
rispondeva `unknown` a un claim identico al fatto in memoria.

═══ LA CAUSA, e sta in una proprietà di Unicode ═══

`\\w` — quindi `[^\\W\\d_]` — comprende lettere e cifre ma **non i combining
mark**. Nelle scritture **abugida** i mark non sono decorazioni: sono le vocali.
Misurato carattere per carattere su «वेरोना» (Verona)::

    व  U+0935  Lo  \\w=True     DEVANAGARI LETTER VA
    े  U+0947  Mn  \\w=False    DEVANAGARI VOWEL SIGN E
    र  U+0930  Lo  \\w=True     DEVANAGARI LETTER RA
    ो  U+094B  Mc  \\w=False    DEVANAGARI VOWEL SIGN O
    न  U+0928  Lo  \\w=True     DEVANAGARI LETTER NA
    ा  U+093E  Mc  \\w=False    DEVANAGARI VOWEL SIGN AA

    [^\\W\\d_]{4,} vede  ['व', 'र', 'न']  →  lunghezze [1, 1, 1]  →  nessuna parola

⇒ Non un difetto di soglia: la regex si **spezzava su ogni vocale**, e nessun
frammento poteva mai arrivare a quattro.

═══ ⚖️ PERCHÉ IL PRIMO TENTATIVO DI CURA NON BASTAVA — la soglia non è neutra ═══

Raggruppando `(?:lettera segni*){4,}` il tamil passava e l'hindi no, e la
ragione è che quel pattern conta le **sillabe**::

    वेरोना  →  3 sillabe (व-र-न)     ma 6 caratteri
    गोदाम   →  3 sillabe             ma 5 caratteri

Quattro sillabe in devanagari sono una parola lunghissima. **«Quattro» significa
cose diverse a seconda della scrittura**, ed è lo stesso inganno del livello di
misura: la soglia sembrava una costante e invece era una unità di misura.
Contando i CARATTERI — il primo obbligatoriamente una lettera — torna a
significare la stessa cosa ovunque.

📌 E la soglia dei 4 **non è stata toccata**: il commento accanto a `_PAROLA_RE`
lo vieta, con un fatto a supporto (`7aa678f57c73`, strada già falsificata sul
corpus). Cambia solo che cosa conta come carattere di una parola.

═══ I MARK SI CHIEDONO A UNICODE, NON SI ELENCANO ═══

`_classe_dei_segni()` li deriva da `unicodedata` all'import: **30 ms una volta
sola**, 2210 mark compattati in 309 intervalli. Elencarli a mano sarebbe la
classe di errore più ricorrente di questa casa — liste monolingue in un prodotto
mondiale — e invecchierebbe a ogni versione di Unicode.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from verimem.quantity_match import content_tokens
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


ABUGIDA = [
    ("HI", "वेरोना गोदाम में 480 पैलेट हैं।"),
    ("BN", "ভেরোনা গুদামে ৪৮০ প্যালেট আছে।"),
]


@pytest.mark.parametrize("lingua,frase", ABUGIDA, ids=[c[0] for c in ABUGIDA])
def test_una_frase_indiana_produce_dei_token(lingua, frase):
    """Il cuore: senza token non esiste nessun confronto, e il difetto non dà
    errore — restituisce un insieme vuoto e ogni guardia costruita sopra tace."""
    assert content_tokens(frase), f"[{lingua}] nessun token estratto"


@pytest.mark.parametrize("lingua,frase", ABUGIDA, ids=[c[0] for c in ABUGIDA])
def test_ALLA_PORTA_il_claim_identico_e_supportato(lingua, frase):
    """La misura che conta, sulla porta che il prodotto usa."""
    verdetto = validate_claim(_Agent([_Fact("f1", frase)]), frase)["verdict"]
    assert verdetto == "supported", f"[{lingua}] non confermato: {verdetto}"


@pytest.mark.parametrize("lingua,frase,attese", [
    ("EN", "The Verona warehouse contains 480 pallets.", 4),
    ("IT", "Il magazzino di Verona contiene 480 pallet.", 4),
    ("RU", "Склад в Вероне содержит 480 паллет.", 4),
])
def test_LE_LINGUE_ALFABETICHE_non_cambiano(lingua, frase, attese):
    """⚠️ IL PRESIDIO. Allargare la classe dei caratteri di una parola tocca
    OGNI lingua che passa di qui: se il conteggio cambiasse dove oggi è giusto,
    la cura avrebbe spostato il problema invece di risolverlo."""
    assert len(content_tokens(frase)) == attese, (
        f"[{lingua}] {sorted(content_tokens(frase))}")


@pytest.mark.parametrize("caso,testo", [
    ("tre lettere", "cat"),
    ("cifre", "4096"),
    ("misto con cifre", "ab12cd"),
    ("segni isolati", "ेोाे"),
    ("punteggiatura", "...!?"),
])
def test_LA_POPOLAZIONE_OPPOSTA_non_diventa_una_parola(caso, testo):
    """⚠️ Il rischio speculare: una classe più larga può promuovere a «parola»
    ciò che non lo è. I segni isolati sono il caso stretto — ora fanno parte
    della classe, ma una parola non può COMINCIARE con una vocale sospesa."""
    assert not content_tokens(testo), f"[{caso}] «{testo}» è diventato un token"
