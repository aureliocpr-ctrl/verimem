"""`epistemic_health()` dava un voto alto su un campione non casuale.

Il difetto **era già noto**: un commento del 16/08 in `client.py` lo descrive —
*«un voto alto su un ottavo del corpus si legge identico a un voto alto sul
corpus»* — e la cura fu aggiungere `n_not_examined`. Questo file aggiunge le
due cose che lì mancavano.

**QUANTO pesa**, misurato sul corpus di casa nella stessa esecuzione::

                             default (2000)      tutto (11379)
        provenance_coverage       0.995              0.578
        composite                 0.976              0.771

**PERCHÉ pesa**: il campione non è casuale. `list_facts` ordina
`created_at DESC`, quindi i 2000 esaminati sono i **più recenti** — e i fatti
recenti portano una source molto più spesso dei vecchi, perché è cambiato il
modo in cui li scriviamo, non il corpus. La distorsione ha una direzione
**prevedibile**: ogni frazione legge ALTA.

⇒ `n_not_examined` dice QUANTI restano fuori; non diceva **quali**. Un voto di
0,98 e uno di 0,77 mandano a fare cose diverse, e col default si legge il primo.

📌 E il `57.8%` che `verimem doctor` stampa è il numero sul corpus INTERO —
cioè le due superfici davano 99,5% e 57,8% per la stessa proprietà.

⚠️ IL CAMPIONE QUI È COSTRUITO CON `limit=1` SU UNO STORE DI DUE FATTI, non
ereditato dallo store di casa. La prima stesura usava `Memory()` e il default
2000: sotto pytest lo store è isolato e vuoto, `n_not_examined` era 0 e i due
test che contano SALTAVANO — passavano solo i presidi, sul caso banale. È il
secondo sensore scollegato della giornata, e la regola è la stessa: **la
condizione di un test non può dipendere da uno stato che il banco non
costruisce.**
"""
from __future__ import annotations

import pytest

from verimem import Memory

FONTE = "Planimetria: magazzino centrale, 4200 metri quadrati."


@pytest.fixture()
def mem_con_due_fatti(tmp_path):
    m = Memory(str(tmp_path / "s.db"))
    m.add("Il magazzino centrale ha 4200 metri quadrati.", topic="az/m",
          source=FONTE)
    m.add("Il magazzino nord ha 1800 metri quadrati.", topic="az/n",
          source="Planimetria: magazzino nord, 1800 metri quadrati.")
    return m


def test_col_campione_il_report_dichiara_che_e_ORDINATO(mem_con_due_fatti):
    """IL CUORE: il lettore non può dedurre dai numeri COME sono stati scelti
    i fatti guardati."""
    h = mem_con_due_fatti.epistemic_health(limit=1)
    assert h.get("n_not_examined"), (
        f"il banco non produce un campione: n_not_examined="
        f"{h.get('n_not_examined')!r}")
    campione = str(h.get("sample") or "")
    assert campione, "il report non dice su cosa è calcolato"
    assert "recent" in campione.lower(), (
        f"il report non dice che il campione è ordinato per data: {campione!r}")
    assert "not a random sample" in campione.lower(), (
        f"il report non avverte che il campione NON è casuale: {campione!r}")


def test_dice_anche_in_quale_DIREZIONE_e_distorto(mem_con_due_fatti):
    """Non basta «non è casuale»: una distorsione senza verso non si sa come
    correggere. Qui il verso si conosce — i recenti hanno la source più
    spesso — e va detto."""
    h = mem_con_due_fatti.epistemic_health(limit=1)
    assert "high" in str(h.get("sample") or "").lower(), (
        f"il report non dice in che direzione legge il campione: "
        f"{h.get('sample')!r}")


def test_presidio_sul_corpus_INTERO_non_avverte_di_niente(mem_con_due_fatti):
    """⚖️ L'ALTRA POPOLAZIONE, e senza di essa la cura sarebbe un allarme
    perpetuo: quando non resta fuori nulla, l'avviso sarebbe falso. Un report
    che avverte SEMPRE non informa più di uno che tace sempre."""
    h = mem_con_due_fatti.epistemic_health(limit=1000)
    assert not h.get("n_not_examined"), (
        f"il banco non copre tutto lo store: {h.get('n_not_examined')!r}")
    campione = str(h.get("sample") or "").lower()
    assert "whole corpus" in campione, (
        f"esaminato tutto, ma il report non lo dice: {campione!r}")
    assert "not a random sample" not in campione, (
        f"esaminato tutto e avverte lo stesso di un campione: {campione!r}")


def test_n_not_examined_resta_dichiarato(mem_con_due_fatti):
    """Il presidio più banale: aggiungere il COME non deve far sparire il
    QUANTO, che è la cura del 16/08."""
    h = mem_con_due_fatti.epistemic_health(limit=1)
    assert "n_not_examined" in h, (
        "il conteggio dei non esaminati è sparito dal referto")
    assert h["n_not_examined"] == 1, (
        f"su due fatti con limit=1 ne resta fuori uno, non "
        f"{h['n_not_examined']!r}")
