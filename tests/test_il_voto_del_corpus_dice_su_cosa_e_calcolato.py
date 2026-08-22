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


# ──────────────────  il default: il numero vero, non il comodo  ──────────────

def test_il_default_copre_un_corpus_reale_non_solo_un_banco():
    """Il default era 2000 e su un corpus di 11 383 fatti dava un voto sul 18%.

    Misurato prima di cambiarlo, sullo stesso store::

        limit=2000    n=2 000    composite 0.976   provenance 0.995   0.56s
        limit=100000  n=11 383   composite 0.771   provenance 0.578   1.01s

    Il default risparmiava 0,45 secondi e regalava venti punti di voto.

    ⚠️ SI ASSERTA LA COSTANTE, non il conteggio su questo banco. La prima
    stesura chiamava `epistemic_health()` sui due fatti della fixture e
    pretendeva `n_not_examined == 0`: vero anche col default VECCHIO, perché
    due fatti stanno dentro 2000. **Passava senza la cura** — terzo sensore
    debole della giornata.

    ⛔ E dichiaro cosa questo test NON prova: che su uno store con più di
    2000 fatti il default li guardi davvero. Servirebbero 2001 scritture, e il
    costo non vale il grado di certezza in più; il comportamento su un corpus
    vero è la misura qui sopra, presa a mano.
    """
    assert Memory._HEALTH_LIMIT_DEFAULT >= 100_000, (
        f"il default è tornato basso ({Memory._HEALTH_LIMIT_DEFAULT}): su un "
        f"corpus reale il voto tornerebbe a descrivere la fetta più recente")


def test_un_limite_esplicito_resta_possibile_e_si_dichiara(mem_con_due_fatti):
    """⚖️ Alzare il default non deve togliere la leva: chi ha un corpus enorme
    passa un limite, e in quel caso il referto lo DICE. Il comportamento
    degrada dichiarandosi — l'unica cosa che il default vecchio non faceva."""
    h = mem_con_due_fatti.epistemic_health(limit=1)
    assert h.get("n_not_examined") == 1
    assert "not a random sample" in str(h.get("sample") or "").lower()


def test_la_porta_MCP_eredita_il_default_invece_di_cablarne_uno_suo():
    """⚠️ IL CABLAGGIO È COME NASCONO LE DUE SUPERFICI. L'handler MCP aveva
    `arguments.get("limit", 2000)`: un default suo, che restava indietro
    quando l'SDK cambiava il proprio. È la stessa forma dei due pesi del
    modello e delle due finestre di undo, viste oggi.
    """
    import re
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "verimem"
           / "mcp_server.py").read_text(encoding="utf-8", errors="replace")
    i = src.index('if name == "hippo_epistemic_health"')
    blocco = src[i:i + 2000]
    assert not re.search(r'arguments\.get\(\s*"limit"\s*,\s*\d+', blocco), (
        "l'handler MCP cabla di nuovo un default suo per `limit` invece di "
        "ereditarlo dall'SDK")
