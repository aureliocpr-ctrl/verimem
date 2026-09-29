"""RIGA 8 — una confabulazione fermata non torna da nessuna porta.

LA PROMESSA. README, righe 449-455, «THE MOAT, live — the reason Verimem exists»::

    src = "We migrated the analytics store to Postgres last quarter."
    m.add("Analytics runs on Postgres.", source=src)   # entailed  -> admitted
    r = m.add("Analytics runs on MongoDB.", source=src)  # confab -> QUARANTINED
    assert r["status"] == "quarantined"   # stored but OUT of default recall —
                                          # your agent will never repeat it as truth

Cura 8 del mandato del 29/09 («questo non deve mai tornare»): la frase fermata non torna
da NESSUNA delle tre porte con cui un utente legge la memoria.

COSA VEDE L'UTENTE. Scrive l'esempio del README con l'SDK, poi chiede «what does
analytics run on» dall'SDK (`Memory().search`), dal comando `verimem recall` e dallo
strumento `verimem_recall`: in nessuna delle tre risposte c'e' «Analytics runs on
MongoDB.».

LA PROVA E I SUOI CONTROLLI. Uno store solo, perche' le tre porte leggono lo stesso store,
come nel README. CONTROLLO POSITIVO: il fatto sostenuto («Analytics runs on Postgres.»)
torna da ognuna delle tre porte, altrimenti una porta che non legge niente passerebbe per
una porta che non ripete la confabulazione. E la confabulazione e' stata SCRITTA e
fermata (ricevuta dell'SDK, esito «fermato»): «stored but OUT», non «mai entrata».

CHI LA TIENE: il cancello alla scrittura e il filtro di default della lettura, su tutte e
tre le porte. Il verdetto lo da' il job di accettazione dal wheel.
"""
from __future__ import annotations

import json

FONTE = "We migrated the analytics store to Postgres last quarter."
SOSTENUTO = "Analytics runs on Postgres."
CONFABULAZIONE = "Analytics runs on MongoDB."
DOMANDA = "what does analytics run on"

CODICE_SCRIVE = r'''
import json
from verimem import Memory
m = Memory()
a = m.add(SOSTENUTO_QUI, source=FONTE_QUI)
b = m.add(CONFAB_QUI, source=FONTE_QUI)
print("ESITO " + json.dumps({"sostenuto": a.get("esito"), "confabulazione": b.get("esito"),
                             "stato_della_confabulazione": b.get("status")}, default=str))
'''.replace("SOSTENUTO_QUI", repr(SOSTENUTO)).replace(
    "CONFAB_QUI", repr(CONFABULAZIONE)).replace("FONTE_QUI", repr(FONTE))

CODICE_LEGGE = r'''
import json
from verimem import Memory
testi = [h["text"] for h in Memory().search(DOMANDA_QUI, k=10)]
print("ESITO " + json.dumps(testi, ensure_ascii=False))
'''.replace("DOMANDA_QUI", repr(DOMANDA))


def _esito(uscita):
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("ESITO ")]
    assert righe, (f"lo script dell'utente non e' arrivato in fondo (returncode "
                   f"{uscita.returncode}); stderr: {uscita.stderr[-800:]}")
    return json.loads(righe[-1][len("ESITO "):])


def test_riga_8_la_confabulazione_fermata_non_torna_da_nessuna_porta(utente):
    scritto = _esito(utente.python(CODICE_SCRIVE))
    assert scritto["sostenuto"] == "ammesso", scritto
    assert scritto["confabulazione"] == "fermato", (
        "la confabulazione del README non e' stata fermata alla scrittura: la riga "
        f"misurerebbe la lettura di un fatto ammesso, non di uno fermato. {scritto}")

    risposte = {"sdk": " ".join(_esito(utente.python(CODICE_LEGGE)))}
    cli = utente.cli("recall", DOMANDA, "--k", "10")
    assert cli.returncode == 0, (
        f"verimem recall: returncode={cli.returncode}; stderr: {cli.stderr[-600:]}")
    risposte["cli"] = cli.stdout
    with utente.mcp() as sessione:
        risposte["mcp"] = json.dumps(
            sessione.chiama("verimem_recall", {"query": DOMANDA, "k": 10}),
            ensure_ascii=False)

    mute = [porta for porta, testo in risposte.items() if SOSTENUTO not in testo]
    assert not mute, (
        f"CONTROLLO POSITIVO SPENTO: il fatto sostenuto non torna da {mute}, quindi quella "
        f"porta non dimostra niente sulla confabulazione: "
        f"{ {p: risposte[p][:300] for p in mute} }")

    ripetuta = [porta for porta, testo in risposte.items() if CONFABULAZIONE in testo]
    assert not ripetuta, (
        f"la confabulazione fermata torna come vera da {ripetuta}: «stored but OUT of "
        f"default recall — your agent will never repeat it as truth» non regge. "
        f"{ {p: risposte[p][:300] for p in ripetuta} }")
