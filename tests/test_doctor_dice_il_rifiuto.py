"""Il referto di doctor deve NOMINARE il rifiuto, anche quando vale zero.

⚠️ PERCHE' QUESTO FILE ESISTE, misurato il 18/09::

    verimem doctor | grep -ic "reject"   ->  0

Il referto parla di `quarantined` e non nomina mai il rifiuto. E i due esiti
non sono la stessa cosa: un fatto quarantinato ESISTE nello store e si conta;
un fatto rifiutato NON ENTRA (client.py: `stored: False, status: "rejected"`).
Del rifiuto non resta niente da contare nello store — e' la classe
«l'assenza non ha un canale».

🔑 E LA FRASE DEVE DIRE DUE COSE, non una. Misurato lo stesso giorno sul
registro vero: admitted 10449, quarantined 1303, abstained 32, e `rejected`
non compare affatto. Ma lo zero non vuol dire «non e' mai successo»: vuol dire
«non e' mai stato CHIESTO», perche' il rifiuto scatta solo con
``gate_mode="reject"`` e il preset di partenza (`balanced`) lo lascia a None.

⚠️ E IL REFERTO DEVE DIRE DI CHI PARLA. Misurato (T103b): una scrittura dalla
porta MCP entra nello store e il libro mastro NON si muove — il registro e'
agganciato a `Memory.add()`, e la porta MCP scrive un livello sotto. Una riga
che dicesse «mai richiesto» senza dire su quale popolazione sarebbe VERA su
CLI e libreria e letta come vera su tutto: il modo peggiore di sbagliare.
"""
from __future__ import annotations

import pytest

from verimem.trust_ledger import TrustLedger

#: Il NOME esatto del controllo, non una parola cercata nel testo.
#: ⚠️ Cercare «rifiut» dentro nome+dettaglio sembrava piu' generoso ed era
#: sbagliato: agganciava il controllo `version`, perche' il NOME DEL RAMO su
#: cui lavoro contiene quella parola. Il banco leggeva l'ambiente invece del
#: prodotto, e la cella negativa e' passata nel ROSSO — ed e' cosi' che l'ho
#: visto. Un controllo si cerca per nome.
NOME_DEL_CONTROLLO = "rifiuto"


def _referto_con(righe: dict[str, int], tmp_path, monkeypatch) -> dict:
    """Scrive un libro mastro finto e torna il controllo del rifiuto."""
    dati = tmp_path / "dati"
    (dati / "semantic").mkdir(parents=True)
    libro = TrustLedger(dati / "semantic" / "semantic.db")
    for azione, n in righe.items():
        libro.record_many(azione, n)
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(dati))
    from verimem.doctor import run_doctor
    controlli = run_doctor()
    trovati = [c for c in controlli if c["name"] == NOME_DEL_CONTROLLO]
    assert trovati, (
        f"il referto non ha nessun controllo chiamato {NOME_DEL_CONTROLLO!r}. "
        f"Un esito che non ha un canale non si legge come «zero»: si legge "
        f"come «tutto a posto». Controlli visti: {[c['name'] for c in controlli]}")
    return trovati[0]

def test_il_referto_nomina_il_rifiuto_e_dice_PERCHE_e_zero(tmp_path, monkeypatch):
    """IL CUORE: non basta un numero, deve dire che non e' mai stato CHIESTO."""
    c = _referto_con({"admitted": 40, "quarantined": 5}, tmp_path, monkeypatch)
    testo = c["detail"].lower()
    assert "mai richiesto" in testo, (
        f"il referto non dice PERCHE' e' zero. «0 rifiuti» si legge come «il "
        f"cancello non rifiuta mai», che e' falso: non gli e' mai stato "
        f"chiesto. Letto: {c['detail']!r}")
    assert "balanced" in testo and "gate_mode" in testo, (
        f"il referto non dice COME si chiede: senza il preset e la manopola, "
        f"chi legge non sa cosa cambiare. Letto: {c['detail']!r}")


def test_il_referto_dice_DI_QUALE_PORTA_parla(tmp_path, monkeypatch):
    """La riga vale su CLI e libreria, NON sulla porta MCP: deve dirlo."""
    c = _referto_con({"admitted": 40, "quarantined": 5}, tmp_path, monkeypatch)
    testo = c["detail"].lower()
    assert "mcp" in testo, (
        f"il referto non dichiara la popolazione. Il libro mastro non conta "
        f"le scritture della porta MCP (misurato): una frase vera su CLI e "
        f"libreria verrebbe letta come vera su tutto. Letto: {c['detail']!r}")


def test_con_un_rifiuto_registrato_la_frase_CAMBIA(tmp_path, monkeypatch):
    """IL NEGATIVO OBBLIGATORIO, e senza questa cella le altre due non
    provano niente: una riga che stampasse «mai richiesto» SEMPRE — anche
    leggendo la tabella sbagliata — le farebbe passare uguale."""
    c = _referto_con({"admitted": 40, "quarantined": 5, "rejected": 3},
                     tmp_path, monkeypatch)
    testo = c["detail"].lower()
    assert "mai richiesto" not in testo, (
        f"c'e' un rifiuto nel registro e il referto dice ancora «mai "
        f"richiesto»: sta leggendo qualcos'altro. Letto: {c['detail']!r}")
    assert "3" in c["detail"], (
        f"il referto non porta il numero dei rifiuti. Letto: {c['detail']!r}")
