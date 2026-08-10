"""Il riesame della quarantena riammette fatti in blocco e non lascia traccia.

IL DIFETTO, misurato sul corpus di casa il 09/08 (9168 fatti, git e15f6ea3)::

    dry-run di `verimem facts requalify-quarantined`
        764 quarantinati  ->  265 dichiarati recuperabili
    audit_mutations                443 righe
        delete 239 · supersede 201 · forget 3 · restore 0

Duecentosessantacinque fatti possono tornare nella vista viva, e dopo non esiste
riga che dica CHI l'ha deciso, QUANDO e con quale versione del criterio.

🔑 E LA CURA C'ERA GIÀ, INCOMPLETA — è l'asimmetria dentro lo stesso file:
``cleanup_episode_telemetry`` (admission_cleanup.py, ~riga 220) chiama
``record_mutation`` per ogni cancellazione; ``requalify_quarantined`` (~riga 302)
fa una ``UPDATE`` nuda. **Chi cancella lascia traccia, chi riammette no** — e
``restore`` è già fra le ``MUTATION_ACTIONS``: non c'era da inventare, c'era da
collegare.

📌 PERCHÉ QUI SÌ, mentre `test_chi_ha_quarantinato_si_sa_anche_domani` argomenta
che la quarantena al *write* NON va in ``audit_mutations``: quella è una
decisione di ammissione su un fatto in arrivo, e la sua sede è la colonna
``quarantined_by``. Questa è un'operazione **amministrativa deliberata su fatti
già nello store**, che cambia cosa il prodotto serve — la stessa famiglia di
``forget`` e ``supersede``, che in quella tabella ci sono già. La distinzione non
è «scrive o non scrive»: è *decisione di ammissione* contro *mutazione di ciò che
è già ammesso*.

⚠️ NON copre (e va detto, perché resta aperto):
- il riesame non passa da ``SemanticMemory.restore_fact`` — quindi non invalida
  la cache di recall come fa il ripristino singolo;
- il criterio di riesame non guarda il verdetto del moat: dei 265 recuperabili,
  165 portano ``grounding_score < 40``, cioè una fonte è stata controllata contro
  di loro e li ha respinti.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.admission_cleanup import requalify_quarantined
from verimem.client import Memory

#: L1 ferma questi per quello che sono: auto-attestazioni senza prova. Sono la
#: materia prima della quarantena, e quella che il riesame va a rivedere.
VANTI = [
    "Ho verificato che la funzione ora funziona correttamente.",
    "Il modulo e' stato testato ed e' pronto per la produzione.",
]


def _quarantinati(mem) -> list[str]:
    c = sqlite3.connect(str(mem.semantic.db_path))
    try:
        return [r[0] for r in c.execute(
            "SELECT id FROM facts WHERE status='quarantined' "
            "AND superseded_by IS NULL")]
    finally:
        c.close()


def _audit(mem, action: str | None = None) -> list[sqlite3.Row]:
    c = sqlite3.connect(str(mem.semantic.db_path))
    c.row_factory = sqlite3.Row
    try:
        if not c.execute("SELECT name FROM sqlite_master WHERE type='table' "
                         "AND name='audit_mutations'").fetchone():
            return []
        sql = "SELECT * FROM audit_mutations"
        if action:
            return list(c.execute(sql + " WHERE action = ?", (action,)))
        return list(c.execute(sql))
    finally:
        c.close()


@pytest.fixture()
def mem_con_quarantinati(tmp_path):
    """Uno store con quarantinati di ENTRAMBE le specie, che è il caso reale.

    ⚠️ Il primo banco che ho scritto conteneva solo i VANTI, e non provava
    niente: L1 li ferma ANCORA oggi, quindi il riesame li lascia dove sono e
    non c'era nulla da tracciare. Serve anche la specie che il riesame recupera
    davvero — un fatto benigno finito in quarantena, come quelli che un falso
    positivo poi corretto aveva nascosto. Lo metto lì dalla porta inversa
    (``quarantine_fact``), che è esattamente ciò che il gate faceva prima della
    correzione.
    """
    m = Memory(str(tmp_path / "s.db"))
    for v in VANTI:
        m.add(v, topic="az/q")                      # restano quarantinati: giusto
    r = m.add("Il magazzino di Prato contiene 300 pallet.", topic="az/ok",
              source="Inventario: il magazzino di Prato contiene 300 pallet.")
    assert r.get("status") != "quarantined", r
    assert m.semantic.quarantine_fact(r["id"], reason="falso positivo storico")
    m._recuperabile = r["id"]
    assert _quarantinati(m), "il banco non ha quarantinati: non prova niente"
    return m


def test_ogni_fatto_riammesso_lascia_una_riga_di_audit(mem_con_quarantinati):
    """IL CUORE: dopo un riesame applicato, chi guarda il database domani deve
    poter sapere che quei fatti sono stati riammessi — e da chi."""
    m = mem_con_quarantinati
    prima = len(_audit(m, "restore"))
    res = requalify_quarantined(str(m.semantic.db_path), dry_run=False,
                                principal="cli:test")
    promossi = res["promoted"]
    assert promossi > 0, f"nulla da promuovere, il banco non prova niente: {res}"
    righe = _audit(m, "restore")
    assert len(righe) - prima == promossi, (
        f"promossi {promossi} fatti ma scritte {len(righe) - prima} righe di "
        f"audit: la riammissione è invisibile a chi legge il database dopo")


def test_la_traccia_dice_CHI_e_CON_QUALE_VERSIONE(mem_con_quarantinati):
    """La riga non basta che esista: deve rispondere alle domande per cui è
    stata scritta — chi ha deciso, e con quale versione del criterio (se il
    criterio cambia, un riesame vecchio non è confrontabile con uno nuovo)."""
    m = mem_con_quarantinati
    requalify_quarantined(str(m.semantic.db_path), dry_run=False,
                          principal="cli:test")
    righe = _audit(m, "restore")
    assert righe, "nessuna riga di restore"
    r = righe[0]
    assert r["principal"] == "cli:test", f"principal={r['principal']!r}"
    assert r["ts"], "senza quando"
    assert r["resource_id"], "senza quale fatto"
    import json
    detail = json.loads(r["detail"] or "{}")
    assert detail.get("version"), (
        f"il detail non dice con quale versione è stato riammesso: {detail}")
    assert detail.get("from") == "quarantined", (
        f"il detail non dice da quale stato viene: {detail}")


def test_CONTROLLO_POSITIVO_il_dry_run_non_scrive_NESSUNA_traccia(
        mem_con_quarantinati):
    """⚠️ IL PRESIDIO: un'anteprima che lascia tracce sarebbe peggio del
    silenzio — riempirebbe la catena di righe per operazioni mai avvenute, e
    chi legge non saprebbe più distinguere ciò che è successo da ciò che era
    solo stato ipotizzato."""
    m = mem_con_quarantinati
    prima = len(_audit(m))
    res = requalify_quarantined(str(m.semantic.db_path), dry_run=True,
                                principal="cli:test")
    assert res["promoted"] == 0
    assert len(_audit(m)) == prima, (
        "il dry-run ha scritto nella catena di audit: un'anteprima non è un "
        "evento")


def test_senza_principal_esplicito_l_identita_viene_dall_ambiente(
        mem_con_quarantinati, monkeypatch):
    """Il requisito è «mai in anonimo», che NON è «mai senza argomento».

    ⚠️ La prima versione di questo test pretendeva un `ValueError` quando il
    chiamante ometteva `principal`, e quella pretesa ha reso rossi tre test che
    passavano da sempre (`test_requalify_quarantined.py`): chi invocava la
    scansione senza argomenti non poteva più farlo. Il contratto giusto è
    quello che il resto del codice usa già — l'identità si LEGGE dall'ambiente
    (``VERIMEM_ACTOR``, cli.py:114) e solo in sua assenza si ripiega su
    un'etichetta esplicita. **La traccia ha bisogno che un'identità ESISTA, non
    che il chiamante la digiti.**"""
    m = mem_con_quarantinati
    monkeypatch.setenv("VERIMEM_ACTOR", "agente:notturno")
    res = requalify_quarantined(str(m.semantic.db_path), dry_run=False)
    assert res["promoted"] > 0, res
    righe = _audit(m, "restore")
    assert righe, "promosso senza lasciare una riga di audit"
    assert righe[-1]["principal"] == "agente:notturno", (
        f"l'identità dell'ambiente non è arrivata nella traccia: "
        f"{righe[-1]['principal']!r}")


def test_CONTROLLO_POSITIVO_senza_ambiente_la_traccia_ha_comunque_un_autore(
        mem_con_quarantinati, monkeypatch):
    """⚠️ IL PRESIDIO che protegge il requisito originale: tolto anche
    l'ambiente, la riga di audit non può restare senza autore. Se un giorno il
    ripiego sparisse, questo diventa rosso — ed è l'unico modo di distinguere
    «legge l'ambiente» da «accetta l'anonimato»."""
    m = mem_con_quarantinati
    monkeypatch.delenv("VERIMEM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_ACTOR", raising=False)
    res = requalify_quarantined(str(m.semantic.db_path), dry_run=False)
    assert res["promoted"] > 0, res
    righe = _audit(m, "restore")
    assert righe and righe[-1]["principal"], (
        "riga di audit senza principal: la riammissione è diventata anonima")


def test_il_dry_run_dichiara_cosa_ne_pensa_il_GIUDICE(mem_con_quarantinati):
    """«265 recuperabili» non è un numero onesto se non dice quanti di quelli
    portano un verdetto negativo del moat già scritto nella loro riga. Sul
    corpus di casa sono 165 su 265: chi legge solo il totale sta per riammettere
    in blocco anche quelli."""
    m = mem_con_quarantinati
    res = requalify_quarantined(str(m.semantic.db_path), dry_run=True,
                                principal="cli:test")
    assert "by_moat" in res, (
        f"il dry-run non dice cosa ne pensa il giudice: {sorted(res)}")
    b = res["by_moat"]
    for chiave in ("respinti", "approvati", "mai_giudicati", "incerti"):
        assert chiave in b, f"manca {chiave} in by_moat: {b}"
    assert sum(b.values()) == res["recoverable"], (
        f"la ripartizione non somma al totale: {b} vs {res['recoverable']}")
