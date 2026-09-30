"""RIGA 8 — una confabulazione fermata non torna da nessuna porta.

LA PROMESSA. README, righe 449-455, «THE MOAT, live — the reason Verimem exists»::

    src = "We migrated the analytics store to Postgres last quarter."
    m.add("Analytics runs on Postgres.", source=src)   # entailed  -> admitted
    r = m.add("Analytics runs on MongoDB.", source=src)  # confab -> QUARANTINED
    assert r["status"] == "quarantined"   # stored but OUT of default recall —
                                          # your agent will never repeat it as truth

Cura 8 del mandato del 29/09 («questo non deve mai tornare»): la frase fermata non torna
da NESSUNA delle porte con cui un utente legge la memoria.

COSA VEDE L'UTENTE. Scrive l'esempio del README con l'SDK, poi chiede «what does analytics
run on» da ogni lettura che il README gli mette in mano sullo stesso store:

  · SDK   `Memory().search` e `Memory().explain` (il dossier «how do you know?»);
  · CLI   `verimem recall`;
  · MCP   `verimem_facts_recall`, `verimem_facts_search` (per parola: «Analytics runs on»)
          e `verimem_trust_report` — i tre strumenti di lettura dei fatti che il README
          nomina (`verimem_recall` legge gli EPISODI, non i fatti: la prima versione di
          questa riga lo usava, e il controllo positivo l'ha fermata sui due sistemi);
  · HTTP  `verimem console` (README r. 558: «your OWN local store … no keys»), cioe'
          `GET /v1/search` e `GET /v1/explain` sullo stesso store.

In nessuna risposta c'e' «Analytics runs on MongoDB.» come fatto servito. Per le letture di
tipo dossier (`explain`, `trust_report`, `/v1/explain`) conta la frase dei fatti SERVITI
(`facts[].proposition`): lo stesso dossier puo' nominare altre frasi nella storia o fra le
contestazioni, dichiarate come tali, e non sono una risposta.

LA PROVA E I SUOI CONTROLLI. Uno store solo, perche' le porte leggono lo stesso store, come
nel README. CONTROLLO POSITIVO: il fatto sostenuto («Analytics runs on Postgres.») torna da
OGNI lettura, altrimenti una porta che non legge niente — o che non parte — passerebbe per
una porta che non ripete la confabulazione; una porta che non parte finisce fra le mute con
la sua uscita. E la confabulazione e' stata SCRITTA e fermata (ricevuta dell'SDK, esito
«fermato»): «stored but OUT», non «mai entrata».

CHI LA TIENE: il cancello alla scrittura e il filtro di default della lettura, su tutte le
porte. Il verdetto lo da' il job di accettazione dal wheel.
"""
from __future__ import annotations

import json

FONTE = "We migrated the analytics store to Postgres last quarter."
SOSTENUTO = "Analytics runs on Postgres."
CONFABULAZIONE = "Analytics runs on MongoDB."
DOMANDA = "what does analytics run on"
PAROLA = "Analytics runs on"   # la lettura per parola (SQL LIKE sulla frase)

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
m = Memory()
testi = [h["text"] for h in m.search(DOMANDA_QUI, k=10)]
rapporto = m.explain(DOMANDA_QUI, k=10)
print("ESITO " + json.dumps({"search": testi, "explain": rapporto}, ensure_ascii=False,
                            default=str))
'''.replace("DOMANDA_QUI", repr(DOMANDA))


def _esito(uscita):
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("ESITO ")]
    assert righe, (f"lo script dell'utente non e' arrivato in fondo (returncode "
                   f"{uscita.returncode}); stderr: {uscita.stderr[-800:]}")
    return json.loads(righe[-1][len("ESITO "):])


def _serviti(dossier) -> str:
    """Le frasi dei fatti SERVITI da un dossier (explain / trust_report)."""
    fatti = dossier.get("facts") if isinstance(dossier, dict) else None
    if not isinstance(fatti, list):
        return ""
    return " | ".join(str(f.get("proposition", "")) for f in fatti if isinstance(f, dict))


def test_riga_8_la_confabulazione_fermata_non_torna_da_nessuna_porta(utente):
    scritto = _esito(utente.python(CODICE_SCRIVE))
    assert scritto["sostenuto"] == "ammesso", scritto
    assert scritto["confabulazione"] == "fermato", (
        "la confabulazione del README non e' stata fermata alla scrittura: la riga "
        f"misurerebbe la lettura di un fatto ammesso, non di uno fermato. {scritto}")

    #: porta -> il testo che quella lettura SERVE; grezze: la risposta intera, per i messaggi
    risposte: dict[str, str] = {}
    grezze: dict[str, str] = {}

    def registra(porta: str, servito: str, grezzo) -> None:
        risposte[porta] = servito
        grezze[porta] = grezzo if isinstance(grezzo, str) else json.dumps(
            grezzo, ensure_ascii=False, default=str)

    sdk = _esito(utente.python(CODICE_LEGGE))
    registra("sdk.search", " ".join(sdk["search"]), sdk["search"])
    registra("sdk.explain", _serviti(sdk["explain"]), sdk["explain"])

    cli = utente.cli("recall", DOMANDA, "--k", "10")
    assert cli.returncode == 0, (
        f"verimem recall: returncode={cli.returncode}; stderr: {cli.stderr[-600:]}")
    registra("cli.recall", cli.stdout, cli.stdout)

    with utente.mcp() as sessione:
        r = sessione.chiama("verimem_facts_recall", {"query": DOMANDA, "k": 10})
        registra("mcp.verimem_facts_recall", json.dumps(r, ensure_ascii=False), r)
        r = sessione.chiama("verimem_facts_search", {"query": PAROLA, "limit": 10})
        registra("mcp.verimem_facts_search", json.dumps(r, ensure_ascii=False), r)
        r = sessione.chiama("verimem_trust_report", {"query": DOMANDA, "k": 10})
        registra("mcp.verimem_trust_report", _serviti(r), r)

    letture_http = (("http.console /v1/search", "/v1/search",
                     lambda r: json.dumps(r, ensure_ascii=False)),
                    ("http.console /v1/explain", "/v1/explain", _serviti))
    try:
        with utente.console() as http:
            for porta, percorso, servito in letture_http:
                try:
                    r = http.get(percorso, q=DOMANDA, k=10)
                except OSError as exc:  # HTTPError/URLError: la lettura non e' riuscita
                    registra(porta, "", f"LETTURA FALLITA: {exc!r}")
                    continue
                registra(porta, servito(r), r)
    except AssertionError as porta_chiusa:   # la porta non e' partita: e' muta, e si dice perche'
        for porta, _, _ in letture_http:
            if porta not in risposte:
                registra(porta, "", f"PORTA NON PARTITA: {porta_chiusa}")

    mute = [porta for porta, testo in risposte.items() if SOSTENUTO not in testo]
    assert not mute, (
        f"CONTROLLO POSITIVO SPENTO: il fatto sostenuto non torna da {mute}, quindi quelle "
        f"porte non dimostrano niente sulla confabulazione: "
        f"{ {p: grezze[p][:400] for p in mute} }")

    ripetuta = [porta for porta, testo in risposte.items() if CONFABULAZIONE in testo]
    assert not ripetuta, (
        f"la confabulazione fermata torna come vera da {ripetuta}: «stored but OUT of "
        f"default recall — your agent will never repeat it as truth» non regge. "
        f"{ {p: grezze[p][:400] for p in ripetuta} }")
