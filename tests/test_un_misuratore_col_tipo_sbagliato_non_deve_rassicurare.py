"""`_entita_diverse` col tipo sbagliato rispondeva `False` in silenzio.

    pa = getattr(a, "proposition", "") or ""

Una `str` non ha `.proposition`. Chi chiamava la funzione con due stringhe — il
modo naturale di provarla da fuori — confrontava due testi **vuoti** e riceveva
sempre `False`: la risposta più rassicurante, cioè «non c'è motivo di
fermarsi».

🔑 È COSTATO UNA MISURA VERA. Il 19/08 ws6 ha consegnato a ws8 una tabella di
casi costruita così e l'ha ritirata da sola, scrivendo che i due «controlli
negativi» erano i peggiori: davano `False`, si leggevano come «giusto», ed
erano `False` perché la funzione non vedeva niente. Ha proposto la cura, e per
due giorni è rimasta senza padrone — il gate è il perimetro di ws3.

⚖️ LE STRINGHE SI ACCETTANO, non si vietano: è il modo in cui i banchi la
usano, e vietarlo non renderebbe nessuno più accorto. Un tipo che non è né un
fatto né un testo SOLLEVA — un misuratore che col tipo sbagliato restituisce la
risposta più comoda è peggio di uno che si rompe.
"""
from __future__ import annotations

import types

import pytest

from verimem.anti_confab_gate import _entita_diverse

_A = "Su 42bb3839 la cella ha stampato 1 failed"
_B = "Su b7bc7b77 la cella ha stampato 1 failed"


def _f(p):
    return types.SimpleNamespace(proposition=p)


def test_due_stringhe_danno_la_stessa_risposta_di_due_fatti():
    """IL CUORE: il caso di ws6. Prima le stringhe davano `False` sempre,
    perché la funzione leggeva due proposizioni vuote."""
    assert _entita_diverse(_A, _B) == _entita_diverse(_f(_A), _f(_B))


def test_con_le_stringhe_il_verdetto_non_e_piu_False_per_costruzione():
    """La prova che il difetto c'era: su due record diversi la risposta giusta
    è `True`, e con le stringhe si otteneva `False`."""
    assert _entita_diverse(_A, _B) is True


@pytest.mark.parametrize("valore", [42, None, [1, 2], {"proposition": "x"}])
def test_un_tipo_che_non_e_ne_fatto_ne_testo_SOLLEVA(valore):
    """⚠️ IL PRESIDIO CHE VALE: un `False` silenzioso è indistinguibile da un
    `False` misurato, e chi lo riceve non ha modo di accorgersene.

    Il `dict` è nell'elenco di proposito: ha una chiave `proposition` e NON
    l'attributo — è il travestimento più facile da scambiare per un fatto.
    """
    with pytest.raises(TypeError, match="proposition"):
        _entita_diverse(valore, _f(_B))


def test_un_fatto_con_proposizione_vuota_resta_legittimo():
    """L'altra popolazione: un fatto che ESISTE e ha la proposizione vuota non
    è un errore di tipo e NON deve sollevare.

    ⚠️ Il verdetto è `True`, non `False`, e la prima stesura di questo test si
    aspettava il contrario: `True` qui significa «non ritirare», perché un lato
    che non nomina niente è il caso in cui si sa MENO — è il ramo aggiunto in
    `59fb0862`. Il test si aspettava un valore, non un comportamento, e ha
    sbagliato di conseguenza. Qui si prova ciò che serve: che non sollevi.
    """
    for vuoto in ("", None):
        esito = _entita_diverse(_f(vuoto), _f(_B))
        assert isinstance(esito, bool), (
            f"proposizione {vuoto!r}: la funzione deve rispondere, non "
            f"sollevare né restituire {esito!r}")


def test_i_due_chiamanti_del_prodotto_non_passano_mai_None():
    """⛔ LA CURA PUÒ ROMPERE IL WRITE PATH, e questo test è la ragione per cui
    non lo fa: i due call site costruiscono `SimpleNamespace(...,
    proposition=...)` in loco e proteggono il secondo argomento con
    `is not None`. Se un domani qualcuno chiamasse la funzione senza quella
    guardia, il prodotto solleverebbe invece di ammettere in silenzio — ed è
    la direzione giusta, ma va vista.
    """
    from pathlib import Path
    sorgente = (Path(__file__).resolve().parent.parent / "verimem"
                / "anti_confab_gate.py").read_text(encoding="utf-8",
                                                   errors="replace")
    chiamate = [r for r in sorgente.splitlines()
                if "_entita_diverse(" in r and "def " not in r
                and not r.strip().startswith("#")]
    assert chiamate, "il banco non trova più i call site"
    for r in chiamate:
        assert "is not None" in r, (
            f"un call site non protegge più l'argomento: {r.strip()!r}")
