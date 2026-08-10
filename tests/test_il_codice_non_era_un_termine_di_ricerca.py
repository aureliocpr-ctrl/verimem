"""`S-007` non era fra i token con cui il write path cerca i fatti da confrontare.

TROVATO cercando perché la RIMISURA di una scheda smette di ritirare la vecchia
sopra una certa scala. La curva, su un registro di laboratorio:

     5 schede + rimisura  ->  la vecchia S-007 viene ritirata   ✅
    10 schede + rimisura  ->  restano DUE S-007 vive            ❌
    15 · 20 · 25          ->  restano DUE S-007 vive            ❌

La soglia sta fra 5 e 10, e il numero non è un caso:

    validate_claim.py   agent.semantic.search_facts(token, limit=10, topic=...)

Il write path sceglie i candidati del confronto cercando per TOKEN, **dieci per
token**. E i token sono i nomi propri secondo `_CAPS_RE`:

    _CAPS_RE = re.compile(r"\\b([A-Z][a-zA-Z]{2,})\\b")

una maiuscola seguita da **almeno due lettere**. Quindi `GPT` entra e `S-007`
no. In un registro dove ogni riga si chiama S-001…S-200 il write path non aveva
**un solo token** capace di ritrovare la riga giusta: cercava «campione» e
«milligrammi», e su un corpus omogeneo quei token riportano dieci righe
qualsiasi.

È la stessa famiglia dell'«omogeneità del corpus è il nemico comune», ma sul
percorso di SCRITTURA e con un numero preciso: dieci.

⚠️ NON SI ALZA `limit`. Alzarlo costa su ogni scrittura e non risolve: a 200
righe servirebbe 200. Cercare il codice è O(1) e riporta esattamente le righe
dello stesso record — il termine di ricerca più selettivo che un registro possa
avere, e l'unico che nessuno cercava.

⚠️ IL PRESIDIO: i token non devono esplodere. Su prosa senza codici il risultato
è invariato, e una frase con un codice ne guadagna uno — non dieci.
"""
from __future__ import annotations

import pytest

from verimem.validate_claim import _extract_salients

#: ⚠️ IL MARCATORE STAVA SUL MODULO E TENEVA DENTRO ANCHE CHI NON C'ENTRAVA.
#: Era un `pytestmark` con `strict=False`, quindi valeva per tutti e quattro i
#: test — e TRE su quattro se lo meritano davvero: chiedono al codice proprio
#: cio' che il difetto impedisce (`S-007` fra i token, `GPT-5` intero invece che
#: troncato a `GPT`, un token in piu' da una frase con un codice).
#: Il quarto no: `test_una_frase_senza_codici_non_cambia` guarda la PROSA, che
#: il difetto non tocca. Passava, e passando in silenzio non diceva a nessuno di
#: essere l'unico ancora acceso.
#:
#: 🔑 IL COSTO DI `strict=False` NON E' CHE NASCONDE UN ROSSO — qui i rossi sono
#: veri e attesi. E' che **non distingue**: sotto quel marcatore un test che
#: descrive il difetto e uno che non c'entra hanno lo stesso aspetto, e il
#: giorno in cui la cura arriva nessuno dei tre lo dira'.
#: 📌 Il segnale che l'ha rivelato non era nel file ma nel referto della CI: due
#: `xpassed` in un run da 10.208 test — questo e' uno dei due. Un `xpassed` e'
#: l'unico modo in cui un marcatore troppo largo si lamenta.
#:
#: Ora il marcatore sta sui TRE test del difetto ed e' `strict`: il giorno in cui
#: `_CAPS_RE` verra' curata diventano ROSSI e chiedono di essere liberati,
#: invece di restare verdi in silenzio.
_DIFETTO_VIVO = pytest.mark.xfail(
    strict=True,
    reason="IL DIFETTO E' VIVO e la cura e' RITIRATA (2026-08-04). "
           "`_CAPS_RE` esige una maiuscola seguita da due lettere, quindi "
           "`S-007` non e' mai un termine di ricerca e in un registro il write "
           "path non ritrova la riga giusta. Aggiungere i codici ai token NON "
           "basta: misurato, la curva 5->OK / 10+->NO non cambia, perche' "
           "`search_facts` di default esclude i quarantinati e il corpus si e' "
           "gia' mangiato i candidati.")


def _token(testo: str) -> set[str]:
    caps, _anni = _extract_salients(testo)
    return caps


@_DIFETTO_VIVO
@pytest.mark.parametrize("testo,atteso", [
    ("Il campione S-007 contiene zinco a 99 milligrammi per litro.", "S-007"),
    ("Il magazzino K-77 ha 4200 metri quadri.", "K-77"),
    ("La scheda REF-42 riporta una resa dell'80 per cento.", "REF-42"),
])
def test_il_codice_del_record_e_un_termine_di_ricerca(testo, atteso):
    """Il cuore: senza questo token, in un registro omogeneo la riga giusta non
    si trova più fra i dieci candidati che il write path esamina."""
    assert atteso in _token(testo), (
        f"«{testo}» non produce il token «{atteso}»: {sorted(_token(testo))}")


def test_una_frase_senza_codici_non_cambia():
    """IL PRESIDIO. Quasi tutto il corpus è prosa: lì il comportamento deve
    restare quello di prima, token per token."""
    assert _token("Il server di produzione ha 64 GB di RAM.") == {"RAM"}
    assert _token("La riunione settimanale e' il martedi' alle 10.") == set()


@_DIFETTO_VIVO
def test_i_token_non_esplodono():
    """L'altro presidio: ogni token in più è una query in più sul percorso di
    scrittura. Una frase con un codice ne guadagna UNO."""
    assert len(_token("Il campione S-007 contiene zinco a 99 milligrammi.")) == 1
    # tre lotti nominati -> tre token, non trenta
    assert _token("I lotti A-1, B-2 e C-3 arrivano lunedi'.") == {"A-1", "B-2", "C-3"}


@_DIFETTO_VIVO
def test_i_nomi_propri_continuano_a_essere_cercati():
    """La funzione esisteva per trovare i nomi propri, e continua a farlo: il
    codice si AGGIUNGE, non sostituisce."""
    assert "GPT" in _token("Il modello GPT-5 costa 3 dollari.")
    assert "GPT-5" in _token("Il modello GPT-5 costa 3 dollari.")
