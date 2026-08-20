"""`trust` non nominava il valore mancante, e `save` sì.

`verimem trust` esiste per sapere PRIMA di scrivere se un fatto passerà. Ma
sullo stesso claim, con la stessa fonte e sullo stesso commit, le due superfici
dicevano cose diverse::

    trust  • [L4.1] un numero che la fonte non dice non e' un numero
             verificato: correggi il valore, oppure passa la fonte che lo contiene

    save     L4.1 — il claim afferma un valore che la fonte non contiene:
             32361578981
             L4.2 — il claim riusa un numero della fonte riferendolo a un'altra
             grandezza: 1 qui e' «per», nella fonte «ubuntu»

⇒ **Lo strumento fatto per controllare PRIMA diceva strettamente MENO di quello
che ti boccia DOPO** — e il valore mancante era `32361578981`, il numero del
run: chi scriveva quel fatto non poteva sapere QUALE numero correggere.

LA CAUSA È UN ORDINE, in `cli.py`::

    msg = w.get("advice") or w.get("reason") or w.get("matched_text") or ""

`advice` è il consiglio GENERICO e viene per primo, quindi vince sempre;
`reason` — quello che porta il valore — non si vede mai.

⚠️ PERCHÉ NON È COSMETICO. Misurato il 20/08: su 144 fatti quarantinati col
giudice sopra 99, **133 hanno un valore che l'evidenza non contiene** —
conteggi e identificatori che l'autore ha calcolato invece di leggerli. È il
fronte aperto più grande, e la sua cura non è «più disciplina»: è che il
pre-controllo dica QUALE valore togliere. L'adozione misura l'attrito.
"""
from __future__ import annotations

from typer.testing import CliRunner

from verimem.cli import app

CLAIM = "Nel run ci 32361578981 i test unici falliti sono 1 per ciascuna cella."
FONTE = "ubuntu-latest / py3.10  1\nubuntu-latest / py3.11  1"


def _sezione_flag() -> str:
    """SOLO la sezione dei flag della card.

    ⚠️ Non si guarda l'output intero: la card RISTAMPA il claim, quindi cercare
    il valore ovunque rende il test verde per il motivo sbagliato. È successo
    alla prima stesura di questo file — un sensore scollegato che passava
    perché leggeva l'eco del claim invece del verdetto.
    """
    res = CliRunner().invoke(app, ["trust", CLAIM, "--source", FONTE])
    piatto = " ".join((res.output or "").replace("|", " ").split())
    i = piatto.find("flags (why")
    assert i != -1, f"la sezione dei flag non c'e': {piatto[:300]}"
    j = piatto.find("checked:", i)
    return piatto[i:j if j > i else len(piatto)]


def test_il_precontrollo_NOMINA_il_valore_che_manca():
    """IL CUORE: chi legge deve sapere QUALE numero correggere."""
    flag = _sezione_flag()
    assert "L4.1" in flag, f"il flag L4.1 non compare: {flag[:300]}"
    assert "32361578981" in flag, (
        "trust segnala L4.1 ma nella sezione dei flag non dice QUALE valore "
        f"manca: chi scrive il fatto non sa cosa correggere.\n{flag[:400]}")


def test_il_precontrollo_TIENE_anche_il_consiglio():
    """Il valore non deve scacciare il consiglio: servono tutti e due — il
    numero dice COSA, il consiglio dice COME."""
    flag = _sezione_flag()
    assert "passa la fonte" in flag or "correggi il valore" in flag, (
        f"il consiglio e' sparito col cambio di priorita':\n{flag[:400]}")


def test_CONTROLLO_un_claim_sostenuto_resta_senza_flag():
    """⚠️ Il controllo opposto: se il claim è sostenuto la card non deve
    inventarsi flag. Senza questo, «stampa sempre tutto» passerebbe i due test
    qui sopra."""
    res = CliRunner().invoke(
        app, ["trust", "Il job ubuntu-latest / py3.10 riporta 1 test fallito.",
              "--source", "ubuntu-latest / py3.10  1"])
    assert res.exit_code == 0, f"un claim sostenuto e' stato FLAGGED: {res.output[:300]}"
