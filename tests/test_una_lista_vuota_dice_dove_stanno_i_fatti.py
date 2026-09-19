"""`hippo_recall` risponde `[]` e non dice che i fatti stanno da un'altra parte.

⚠️ IL DIFETTO NON E' CHE RECALL SIA ROTTO, ed e' il punto che ha cambiato la
cura. La sua descrizione dichiara «Semantic recall over past EPISODES» e il
codice rende una LISTA di episodi: se episodi non ce ne sono, `[]` e' la
risposta GIUSTA al suo contratto. Quello che manca e' un CARTELLO — chi ha
bussato alla porta sbagliata non viene mandato a quella giusta.

Misurato alla porta il 2026-09-19, stesso store e stessa domanda, un fatto
appena scritto e zero episodi::

    hippo_remember      -> id=076e9c4c85da  status='model_claim'
    hippo_recall        -> lista di 0
    hippo_facts_recall  -> items: 1   (il fatto, con id e proposizione)

⚠️ E LA PORTA DI RINVIO E' STATA VERIFICATA PRIMA DI PROPORLA: al primo giro il
mio estrattore aveva detto «n=0» e stavo per scriverlo. Era il mio codice che
leggeva le chiavi sbagliate. Mandare chi legge a una porta vuota sarebbe stata
una cura peggiore del difetto.

🔑 DOVE VA IL CARTELLO, e non dentro la lista: un oggetto che non e' un episodio
in mezzo agli episodi lo iterrebbe chi itera. Va in un SECONDO BLOCCO di
contenuto — il protocollo ne ammette piu' d'uno — cosi' `content[0]` non cambia
di un byte. E una riga nella DESCRIZIONE dello strumento, che e' cio' che un
modello legge PRIMA di scegliere la porta: li' il difetto nasce.

⚠️ OGNI CELLA IN UN PROCESSO PULITO: l'ambiente dello store va posto PRIMA che
`mcp_server` venga importato, e dentro pytest il modulo potrebbe gia' esserci.
Un banco che misura un modulo importato da qualcun altro non misura niente.
"""
from __future__ import annotations

import json
import subprocess
import sys

PROP = "Il badge di servizio sta nel primo cassetto della guardiola"
FONTE = ("Verbale del custode: il badge di servizio e' nel primo cassetto "
         "della guardiola.")
DOMANDA = "dove sta il badge di servizio"


def _in_un_processo_pulito(tmp_path, corpo: str) -> dict:
    """Esegue `corpo` con lo store puntato a `tmp_path`, in un interprete nuovo."""
    testa = (
        "import asyncio, json, os, sys\n"
        f"d = {str(tmp_path)!r}\n"
        "for n in ('HIPPO_DATA_DIR','ENGRAM_DATA_DIR','VERIMEM_DATA_DIR'):\n"
        "    os.environ[n] = d\n"
        "os.environ['ENGRAM_EVENT_LOG'] = d + '/e.jsonl'\n"
        "from verimem import mcp_server as M\n"
        "def porta(nome, arg):\n"
        "    return asyncio.run(M._call_tool_impl(nome, arg))\n"
        f"PROP = {PROP!r}\nFONTE = {FONTE!r}\nDOMANDA = {DOMANDA!r}\n")
    p = subprocess.run([sys.executable, "-c", testa + corpo],
                       capture_output=True, text=True, timeout=900)
    assert p.returncode == 0, f"uscito con {p.returncode}: {p.stderr[-900:]}"
    righe = [r for r in p.stdout.splitlines() if r.startswith("{")]
    assert righe, f"nessun JSON: {p.stdout[-400:]} / {p.stderr[-400:]}"
    return json.loads(righe[-1])


def test_il_cartello_appare_quando_la_lista_e_vuota_e_ci_sono_fatti(tmp_path):
    """IL CUORE: un fatto nello store, zero episodi, e la lista esce vuota."""
    r = _in_un_processo_pulito(tmp_path, (
        "porta('hippo_remember', {'proposition': PROP, 'source': FONTE,\n"
        "                         'topic': 'prova/t107'})\n"
        "b = porta('hippo_recall', {'query': DOMANDA, 'limit': 5})\n"
        "print(json.dumps({'blocchi': len(b),\n"
        "                  'testi': [x.text for x in b]}))\n"))
    assert r["blocchi"] == 2, (
        f"la risposta ha {r['blocchi']} blocchi invece di 2: chi ha chiesto un "
        f"FATTO ha ricevuto una lista vuota e nessuno gli ha detto dove "
        f"guardare. Testi: {r['testi']}")
    assert "hippo_facts_recall" in r["testi"][1], (
        f"il secondo blocco non nomina la porta dei fatti: {r['testi'][1][:300]}")


def test_il_primo_blocco_NON_cambia_di_un_byte(tmp_path):
    """L'ACCETTAZIONE CHE PROTEGGE I CHIAMANTI: chi legge `content[0]` oggi
    deve leggere domani la stessa identica cosa — una lista, e vuota."""
    r = _in_un_processo_pulito(tmp_path, (
        "porta('hippo_remember', {'proposition': PROP, 'source': FONTE,\n"
        "                         'topic': 'prova/t107'})\n"
        "b = porta('hippo_recall', {'query': DOMANDA, 'limit': 5})\n"
        "print(json.dumps({'primo': b[0].text}))\n"))
    assert json.loads(r["primo"]) == [], (
        f"il primo blocco non e' piu' la lista nuda: {r['primo'][:300]}. "
        f"Chi lo parsava si rompe, e il cartello non vale una rottura.")


def test_con_episodi_NESSUN_cartello(tmp_path):
    """Se la lista NON e' vuota il cartello non si accende: sarebbe rumore, e
    il rumore si impara a saltare."""
    r = _in_un_processo_pulito(tmp_path, (
        "porta('hippo_remember', {'proposition': PROP, 'source': FONTE,\n"
        "                         'topic': 'prova/t107'})\n"
        "porta('hippo_record_episode', {'task_text': DOMANDA,\n"
        "        'final_answer': 'primo cassetto', 'outcome': 'success'})\n"
        "b = porta('hippo_recall', {'query': DOMANDA, 'limit': 5})\n"
        "print(json.dumps({'blocchi': len(b),\n"
        "                  'quanti': len(json.loads(b[0].text))}))\n"))
    assert r["quanti"] > 0, (
        f"la cella non misura niente: con un episodio registrato la lista e' "
        f"ancora vuota ({r}). Senza episodi nel risultato, «nessun cartello» "
        f"sarebbe vero per il motivo sbagliato.")
    assert r["blocchi"] == 1, (
        f"la lista ha {r['quanti']} episodi e il cartello si e' acceso lo "
        f"stesso ({r['blocchi']} blocchi): e' rumore.")


def test_la_descrizione_di_recall_nomina_la_porta_dei_fatti(tmp_path):
    """LA META' DELLA CURA, e la piu' economica: la riga che un modello legge
    PRIMA di scegliere la porta. Nessuno store, nessuna scrittura."""
    r = _in_un_processo_pulito(tmp_path, (
        "ts = asyncio.run(M._list_tools_unfiltered())\n"
        "d = {x.name: (x.description or '') for x in ts}\n"
        "print(json.dumps({'recall': d.get('hippo_recall', ''),\n"
        "                  'quanti': len(ts)}))\n"))
    assert "hippo_facts_recall" in r["recall"], (
        f"la descrizione di hippo_recall non manda ai FATTI: chi sceglie la "
        f"porta legge questa riga e non sa che i fatti stanno altrove. "
        f"Letto: {r['recall'][:300]}")
