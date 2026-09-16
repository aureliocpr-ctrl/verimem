"""T49 — un fatto che il moat ha FERMATO non deve tornare come vero da nessuna porta.

Ticket: `docs/stato-reale/RESOCONTO-MAPPA-09-09.md` §2 (T49). Owner ws2 Giano.
Ramo `giano/t49`. Data: 2026-09-09.

LA PROMESSA CHE QUESTO FILE MISURA — non e' una nostra interpretazione, e'
scritta nelle istruzioni che il server MCP consegna a ogni client che si
collega (`mcp_server.py`, blocco `instructions`):

    «a fact its source does not support is QUARANTINED — stored, but kept
     OUT of default recall, so you never get it back as truth»

COSA HA TROVATO LA MAPPA (le righe, lette prima di eseguire):

    9716 9755 9984 9998 10012 ... 31 chiamate in `mcp_server.py` nella forma
        `a.semantic.list_facts(limit=10000, offset=0)` — cioe' con il default
        `hide_low_trust=False` (`semantic.py:3753`), che NON filtra
        'orphaned' / 'quarantined' / 'user_belief'.
    `briefing.py:136` e' l'UNICO chiamante su 38 che passa `hide_low_trust=True`,
        dal 2026-07-20, e nel commento dice gia' il perche' («context
        poisoning»). La cura esiste da 51 giorni in un chiamante solo.
    `client.py:3959` `Memory.get_all` — stessa forma, e non e' MCP: e' l'SDK
        (reperto di @ws3 Galileo, ottavo ingresso).

LE OTTO PORTE, E NON SONO TUTTE LA STESSA COSA. La distinzione decide la cura,
quindi sta qui e non in un commento a valle:

  (a) RECUPERO — chi chiede alla memoria «cosa sai di X» e si aspetta materiale
      su cui RAGIONARE: `hippo_oracle_query`, `hippo_chain_facts`,
      `hippo_prompt_skeleton`, `hippo_cross_agent_consensus`,
      `hippo_forward_chain`, e l'SDK `Memory.get_all`.
      Qui il quarantenato NON deve uscire. E' la promessa, alla lettera.
  (b) PULIZIA — chi cerca duplicati per RIPARARE il corpus:
      `hippo_find_duplicate_facts`, `hippo_facts_find_duplicates`.
      Qui nascondere sarebbe SBAGLIATO: per pulire un quarantenato bisogna
      vederlo. Cio' che manca e' lo `status` per membro, cosi' che chi ripara
      sappia quale dei due lati della coppia il gate aveva gia' fermato.

  E il settimo tool e' peggio degli altri sei, e per questo ha un test suo:
  `hippo_forward_chain` (10493) non ELENCA il quarantenato — lo CONSUMA come
  PREMESSA, e mette in circolo una proposizione NUOVA che nello store non
  esiste e che non porta nessuno status. Un chiamante attento puo' scartare un
  quarantenato che vede in una lista; non puo' scartare una conclusione di cui
  non sa che discende da un fatto fermato.

⚠️ IL CONTROLLO POSITIVO, e senza di esso questo file non prova NIENTE.
Il rosso naturale di questo ticket e' «la porta rende zero quarantenati». Ma
zero e' anche cio' che rende una porta che rende zero e basta: store vuoto,
argomento sbagliato, il tetto dei 10.000, o uno dei 30 `except: pass` muti che
@ws5 Tara ha contato su 37 chiamanti. Sarebbe verde per la ragione sbagliata,
e la cura sembrerebbe fatta. Quindi OGNI test qui asserisce DUE cose:
il quarantenato NON c'e' **e** il fatto sano C'E'.
(Oggi ho gia' pagato tre volte questa classe: `provider="mock"` respinto dallo
schema prima del codice, `check_contradictions` invece di `detect_contradictions`,
un campo letto al livello sbagliato del payload. Cinque funzioni date per morte,
tutte vive.)

⚠️ IL QUARANTENATO E' VERO, NON SCRITTO A MANO. Nessun `status='quarantined'`
messo nel DB da questo file: le sei righe passano dalla porta `hippo_remember`
e le giudica il gate del prodotto. Un banco che si fabbrica lo stato che poi
misura non misura il prodotto — misura se stesso.

⚠️ COME SI LANCIA (la variabile cambia l'esito, quindi va tolta a mano):

    env -u HIPPO_ENCODE_DELEGATE_ONLY python -m pytest -x -q \\
        tests/test_nessuna_porta_serve_un_fatto_che_il_moat_ha_fermato.py

    `main()` mette `HIPPO_ENCODE_DELEGATE_ONLY=1` con `setdefault` su ogni
    processo server e la variabile vive in `~/.claude/settings.json`: la
    ereditano tutte le istanze senza accorgersene. Con quella accesa una
    scrittura che sarebbe `quarantined` esce `admitted` con `L4-skipped`
    (misurato l'08/09), e questo banco misurerebbe la variabile invece del gate.

⛔ PERIMETRO: store in tempdir, e la fixture VERIFICA di esserci prima di
scrivere una riga — `mcp_server._agent` e' un globale cachato (`:79`), quindi
un agente costruito prima di noi punterebbe allo store di produzione di Aurelio.
Se il controllo non passa, il banco muore senza scrivere.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from verimem import mcp_server  # noqa: E402

# ═══════════════════ le sei righe, e perche' ognuna ═══════════════════
#
# Fonte che SOSTIENE: dice la proposizione. Fonte che NON sostiene: parla di
# un altro argomento — non contraddice, semplicemente non porta la cosa. E' il
# caso piu' onesto da chiedere a un moat di entailment.

FONTE_ALTRO_ARGOMENTO = (
    "Il verbale del 3 marzo registra che il portone del magazzino B e' stato "
    "ridipinto e che la serratura elettronica e' stata sostituita in giornata."
)

#: (A) SANO. Serve due volte: e' lo STATO da cui `forward_chain` deduce, ed e'
#: il fatto che ogni porta di recupero DEVE continuare a rendere.
A_SANO = "il tornello 42 e' aperto"
A_FONTE = ("Verbale di prova del 7 settembre: il tornello 42 e' aperto, come "
           "risulta dal registro degli accessi del varco nord.")

#: (B) QUARANTENATO, scritto dalla ronda A. La fonte parla d'altro.
B_QUARANTENATO = "la serratura del deposito nord e' stata forzata"

#: (B') SANO, stessa cosa detta dalla ronda B, con la prova. Serve per due
#: motivi: e' il controllo positivo delle query sul deposito, ed e' il secondo
#: agente senza il quale `cross_agent_consensus` non forma nessun gruppo (e il
#: suo test passerebbe a vuoto).
B1_SANO = "la serratura del deposito nord risulta forzata"
B1_FONTE = ("Rapporto della ronda B, 7 settembre, ore 03:10: la serratura del "
            "deposito nord risulta forzata; allegate due fotografie.")

#: (B'') SANO, la TERZA ronda. Non e' ridondanza: senza di lei il controllo
#: positivo di `cross_agent_consensus` non esiste. Il tool tiene un gruppo solo
#: se ha >= min_agents agenti DISTINTI: tolto il quarantenato resterebbe un
#: agente solo, il gruppo sparirebbe, e «nessun quarantenato nel consenso»
#: sarebbe vero anche a consenso VUOTO. Con tre ronde, due sane e una fermata
#: dal gate, il gruppo deve restare e deve restarci senza la fermata.
B2_SANO = "la serratura del deposito nord e' risultata forzata"
B2_FONTE = ("Verbale della ronda C, 7 settembre, ore 05:40: la serratura del "
            "deposito nord e' risultata forzata; sostituita alle 06:15.")

#: (E) REGOLA SANA il cui ANTECEDENTE e' la proposizione del quarantenato B.
#: Senza di lei il test su `state_fact_ids` passa per la ragione sbagliata, e
#: infatti al giro delle 23:14 passava: passavo l'id di B come stato, ma
#: nessuna regola aveva B come antecedente, quindi non usciva nessuna
#: deduzione — e il verde diceva «non c'era niente da dedurre», non «il
#: quarantenato e' stato filtrato». Con E la domanda diventa secca: regola
#: sana, stato passato per id, e l'unica variabile che cambia fra il controllo
#: positivo e il caso in esame e' lo STATUS dello stato.
E_REGOLA_SANA_SUL_QUARANTENATO = (
    "If la serratura del deposito nord e' stata forzata "
    "then il deposito va ispezionato")
E_FONTE = ("Procedura di sicurezza, punto 9: if la serratura del deposito nord "
           "e' stata forzata then il deposito va ispezionato prima della "
           "riapertura.")

#: (C) REGOLA QUARANTENATA. E' la premessa che `forward_chain` non deve usare.
C_REGOLA_QUARANTENATA = "If il tornello 42 e' aperto then il varco e' insicuro"

#: (D) REGOLA SANA. Il controllo positivo di `forward_chain`: se da questa non
#: esce nessuna deduzione, il verde di (C) direbbe solo che il motore e' fermo.
D_REGOLA_SANA = "If il tornello 42 e' aperto then il registro va aggiornato"
D_FONTE = ("Regolamento interno, articolo 4: if il tornello 42 e' aperto then "
           "il registro va aggiornato entro la fine del turno.")


def _chiama(nome: str, argomenti: dict) -> dict:
    """Passa dalla PORTA (il request handler), non dall'handler privato: e' il
    livello a cui arriva un client MCP, ed e' il livello che il ticket accusa."""
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=nome, arguments=argomenti))
    r = asyncio.run(handler(req))
    payload = r.root if hasattr(r, "root") else r
    testo = " ".join(c.text for c in payload.content if hasattr(c, "text"))
    try:
        return json.loads(testo)
    except Exception:
        return {"_grezzo": testo}


def _scrivi(proposizione: str, fonte: str, topic: str, **extra) -> dict:
    d = _chiama("hippo_remember", {
        "proposition": proposizione, "topic": topic, "source": fonte, **extra})
    return d


def _testo(x) -> str:
    """Il payload di una porta e' JSON annidato e ogni tool lo annida a modo
    suo. Cercare la proposizione nel testo dell'INTERO payload e' volutamente
    grossolano: sbaglia solo verso il ROSSO (puo' trovare il quarantenato dove
    un lettore attento non lo vedrebbe), mai verso il verde. Un righello che
    sbaglia a proprio sfavore si puo' pubblicare."""
    return json.dumps(x, ensure_ascii=False, default=str).lower()


#: I campi di CONFIG da ri-ancorare, e la ragione per cui non basta l'ambiente:
#: `CONFIG` e' una frozen dataclass costruita A IMPORT-TIME (lo dice il conftest
#: alla riga 377, e il prodotto lo denuncia da solo con
#: `RuntimeWarning: DATA_DIR aliases disagree`). Impostare le tre variabili DOPO
#: l'import non sposta un CONFIG gia' congelato: serve `object.__setattr__`.
#: MISURATO SU QUESTO BANCO, primo giro delle 22:57 — con le tre variabili
#: impostate e senza questo pin, `a.semantic` puntava a
#: `C:\\Users\\aurel\\.engram\\semantic\\semantic.db`, cioe' allo store VERO.
def _campi(radice: Path) -> dict:
    return {
        "data_dir": radice,
        "episodes_db": radice / "episodes" / "episodes.db",
        "skills_dir": radice / "skills",
        "skills_db": radice / "skills" / "skills_index.db",
        "semantic_db": radice / "semantic" / "semantic.db",
        "runs_dir": radice / "runs",
        "reports_dir": radice / "reports",
    }


def _pinna(radice: Path) -> dict:
    """Ancora CONFIG a `radice` e rende i valori di prima."""
    from verimem.config import CONFIG
    for sotto in ("episodes", "skills", "semantic"):
        (radice / sotto).mkdir(parents=True, exist_ok=True)
    prima = {}
    for k, v in _campi(radice).items():
        prima[k] = getattr(CONFIG, k)
        object.__setattr__(CONFIG, k, v)
    return prima


@pytest.fixture(scope="module")
def store():
    """Uno store isolato con dentro le sei righe, giudicate dal gate vero.

    Module-scoped di proposito: il moat e' inferenza pesante e le otto porte
    leggono lo STESSO corpus. Sei giudizi in tutto, non sei per test.
    """
    import tempfile

    from verimem.config import CONFIG
    from verimem.test_isolation import assert_store_isolato

    tmp = Path(tempfile.mkdtemp(prefix="ws2-t49-"))
    vecchie = {k: os.environ.get(k) for k in (
        "HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR", "ENGRAM_DIR",
        "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_GROUNDING_WRITE")}
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR",
                 "ENGRAM_DIR"):
        os.environ[nome] = str(tmp)
    #: quattro nomi perche' il prodotto ne legge piu' d'uno a seconda del
    #: modulo, e sbagliarne uno apre un SECONDO store che sembra solo vuoto.
    os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
    os.environ.pop("ENGRAM_GROUNDING_WRITE", None)

    prima = _pinna(tmp)
    agente_di_prima = mcp_server._agent
    mcp_server._agent = None  # :79 e' cachato: senza questo scriveremmo altrove

    try:
        # ⛔ GUARDIA, e non e' scritta qui: e' `verimem.test_isolation`, la
        # stessa che il conftest chiama alla riga 437. Riscriverla a mano
        # sarebbe stata la nona copia della stessa primitiva (R3).
        assert_store_isolato(CONFIG.semantic_db, tmp_root=tmp)
        a = mcp_server._ag()
        percorso = ""
        for attr in ("db_path", "path", "_path", "_db_path"):
            v = getattr(a.semantic, attr, None)
            if v:
                percorso = str(v)
                break
        assert percorso, ("non so dire su quale file scrive lo store: mi fermo "
                          "prima di scrivere. Attributi provati: db_path, path, "
                          "_path, _db_path")
        #: la seconda volta sul percorso APERTO DAVVERO, non su quello
        #: dichiarato: fra CONFIG e l'oggetto costruito ci sono due risolutori,
        #: ed e' esattamente li' che il primo giro e' scappato.
        assert_store_isolato(percorso, tmp_root=tmp)

        scritti = {
            "A": _scrivi(A_SANO, A_FONTE, "banco/ws2/t49/stato"),
            "B": _scrivi(B_QUARANTENATO, FONTE_ALTRO_ARGOMENTO,
                         "banco/ws2/t49/ronda", agent_id="ronda-a"),
            "B1": _scrivi(B1_SANO, B1_FONTE,
                          "banco/ws2/t49/ronda", agent_id="ronda-b"),
            "B2": _scrivi(B2_SANO, B2_FONTE,
                          "banco/ws2/t49/ronda", agent_id="ronda-c"),
            "C": _scrivi(C_REGOLA_QUARANTENATA, FONTE_ALTRO_ARGOMENTO,
                         "banco/ws2/t49/regola"),
            "D": _scrivi(D_REGOLA_SANA, D_FONTE, "banco/ws2/t49/regola"),
            "E": _scrivi(E_REGOLA_SANA_SUL_QUARANTENATO, E_FONTE,
                         "banco/ws2/t49/regola"),
        }

        vivi = a.semantic.list_facts(limit=1000, offset=0)
        per_prop = {(getattr(f, "proposition", "") or "").strip().lower():
                    getattr(f, "status", None) for f in vivi}

        def _stato(p: str):
            return per_prop.get(p.strip().lower(), "**ASSENTE DALLO STORE**")

        diagnosi = ("\n  ".join(
            f"{k}: status={_stato(p)!r}  ricevuta={scritti[k].get('status')!r} "
            f"grounding={scritti[k].get('grounding_score')!r} "
            f"rejected={scritti[k].get('rejected')!r}"
            for k, p in (("A", A_SANO), ("B", B_QUARANTENATO),
                         ("B1", B1_SANO), ("B2", B2_SANO),
                         ("C", C_REGOLA_QUARANTENATA),
                         ("D", D_REGOLA_SANA),
                         ("E", E_REGOLA_SANA_SUL_QUARANTENATO))))

        # I tre controlli senza i quali ogni verde a valle sarebbe vuoto.
        if _stato(B_QUARANTENATO) != "quarantined":
            pytest.fail("il gate NON ha quarantenato la riga che la fonte non "
                        "sostiene: senza un quarantenato nello store questo "
                        "banco non misura niente. Hai lanciato con "
                        "HIPPO_ENCODE_DELEGATE_ONLY accesa?\n  " + diagnosi)
        if _stato(C_REGOLA_QUARANTENATA) != "quarantined":
            pytest.fail("la REGOLA non e' stata quarantenata: il test di "
                        "forward_chain non avrebbe niente da misurare.\n  "
                        + diagnosi)
        for chiave, prop in (("A", A_SANO), ("B1", B1_SANO), ("B2", B2_SANO),
                             ("D", D_REGOLA_SANA),
                             ("E", E_REGOLA_SANA_SUL_QUARANTENATO)):
            st = _stato(prop)
            if st in ("quarantined", "**ASSENTE DALLO STORE**"):
                pytest.fail(
                    f"la riga SANA {chiave} non e' viva e pulita nello store "
                    f"(status={st!r}): senza di lei ogni 'la porta non rende il "
                    "quarantenato' sarebbe verde anche a porta muta. Puo' anche "
                    "essere una SUPERSESSIONE fra le due righe della ronda.\n  "
                    + diagnosi)

        #: l'id lo prendo dallo STORE, non dalla ricevuta: i tool di pulizia
        #: parlano per id e una ricevuta che cambiasse nome al campo mi
        #: lascerebbe con None senza dirlo.
        id_quar = next((getattr(f, "id", "") for f in vivi
                        if (getattr(f, "proposition", "") or "").strip().lower()
                        == B_QUARANTENATO.lower()), "")
        id_sano = next((getattr(f, "id", "") for f in vivi
                        if (getattr(f, "proposition", "") or "").strip().lower()
                        == B1_SANO.lower()), "")
        assert id_quar and id_sano, (
            "non trovo gli id nello store: le porte parlano per id e senza "
            f"questi non misurerebbero niente. quar={id_quar!r} sano={id_sano!r}")

        yield {"dir": tmp, "agente": a, "percorso": percorso,
               "ricevute": scritti, "diagnosi": diagnosi,
               "id_quarantenato": id_quar, "id_sano": id_sano}
    finally:
        mcp_server._agent = agente_di_prima
        from verimem.config import CONFIG as _C
        for k, v in prima.items():
            object.__setattr__(_C, k, v)
        for k, v in vecchie.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture(autouse=True)
def _tieni_il_pin(request):
    """La fixture autouse del conftest (riga 377) ri-ancora CONFIG a una tmp
    NUOVA a ogni test, e gira DOPO quella module-scoped qui sopra. Senza questa,
    dal secondo test in poi CONFIG guarderebbe una cartella vuota mentre
    l'agente cachato tiene aperto il nostro store: due posti, e i test
    passerebbero o cadrebbero a seconda di quale dei due viene letto."""
    if "store" in request.fixturenames:
        _pinna(Path(request.getfixturevalue("store")["dir"]))
    yield


# ═════════════════ (a) LE PORTE DI RECUPERO: non deve uscire ═════════════════

def _asserisci_recupero(payload: dict, dove: str, store: dict) -> None:
    """⚠️ SI GUARDA L'ID, NON IL TESTO, e questo criterio e' costato un rosso.

    Il primo criterio era «la proposizione del quarantenato compare nel JSON».
    Sembra innocuo e non lo e': alle 23:31 quattro porte risultavano ancora
    rosse **a cura funzionante**, perche' la proposizione quarantenata

        "la serratura del deposito nord e' stata forzata"

    compare per intero DENTRO la proposizione della regola SANA (E)

        "if la serratura del deposito nord e' stata forzata then
         il deposito va ispezionato"

    che il payload serviva legittimamente. Il grep serve a TROVARE, mai a
    contare: l'id e' univoco, la sottostringa no.
    """
    testo = _testo(payload)
    id_quar = store["id_quarantenato"]
    id_sano = store["id_sano"]
    assert id_sano and id_sano in testo, (
        f"{dove} non rende nemmeno il fatto SANO (id={id_sano!r}): questo test "
        "non sta misurando il filtro, sta misurando una porta muta. Payload: "
        f"{json.dumps(payload, ensure_ascii=False, default=str)[:600]}")
    _i = testo.find(id_quar)
    assert _i < 0, (
        f"{dove} rende un fatto che il moat ha QUARANTENATO. Il server "
        "promette ai client «kept OUT of default recall, so you never get it "
        f"back as truth». id={id_quar!r} — {B_QUARANTENATO!r}\n"
        f"  DOVE COMPARE: ...{testo[max(0, _i - 260):_i + 140]}...\n"
        f"  ricevuta della scrittura: {store['diagnosi']}")


def test_oracle_query_non_serve_un_quarantenato(store):
    """`hippo_oracle_query` (10133) — «cross-tier memory retrieval ... plus
    aggregated confidence verdict»: e' la porta del «cosa sai di X»."""
    _asserisci_recupero(
        _chiama("hippo_oracle_query",
                {"query": "serratura deposito nord forzata", "top_k_each": 20}),
        "hippo_oracle_query", store)


def test_chain_facts_non_serve_un_quarantenato(store):
    """`hippo_chain_facts` (10117) — BFS multi-hop: un quarantenato qui non e'
    solo servito, e' il ponte verso i fatti successivi."""
    _asserisci_recupero(
        _chiama("hippo_chain_facts",
                {"seed_query": "serratura deposito nord", "max_depth": 2,
                 "min_overlap": 0.05}),
        "hippo_chain_facts", store)


def test_prompt_skeleton_non_serve_un_quarantenato(store):
    """`hippo_prompt_skeleton` (10082) — il payload FINISCE IN UN PROMPT: e'
    esattamente il «context poisoning» che `briefing.py:136` evita da 51
    giorni con una riga."""
    _asserisci_recupero(
        _chiama("hippo_prompt_skeleton",
                {"task": "indagine sulla serratura del deposito nord",
                 "top_k_each": 20}),
        "hippo_prompt_skeleton", store)


def test_cross_agent_consensus_non_conta_un_quarantenato_come_un_accordo(store):
    """`hippo_cross_agent_consensus` (10340) — «independent agents arrived at
    the same proposition. Strong evidence for the agent team».

    Tre ronde dicono la stessa cosa: due con la prova (ronda-b, ronda-c) e una
    che il gate ha FERMATO (ronda-a). Il prodotto le conta tutte e tre e
    presenta il gruppo come evidenza forte. Un fatto quarantenato non e'
    evidenza indipendente: e' rumore che vota.

    ⚠️ IL CRITERIO NON E' «la proposizione non compare nel payload», ed e' un
    errore che ho commesso e che il verde del primo giro (23:01, `FFF.FF`, un
    solo passed, questo) mi ha nascosto: il payload NON elenca i membri, porta
    `representative` (la proposizione del PRIMO fatto del gruppo), `n_agents`,
    `agent_ids` e `fact_ids` (`cross_agent_consensus.py:66-71`). Il quarantenato
    quindi **vota senza comparire**: cercarne il testo dava verde su un tool
    difettoso. Il criterio giusto e' CHI HA VOTATO — `agent_ids`."""
    #: ⚠️ 0.4 e non 0.5, e la ragione e' un fatto sul PRODOTTO che vale la pena
    #: scrivere: `find_consensus_facts` raggruppa in modo GREEDY confrontando
    #: ogni fatto con il PRIMO del gruppo (`cross_agent_consensus.py:46-53`),
    #: e l'ordine e' `created_at DESC`. Quando la regola (E) e' entrata nello
    #: store, e' diventata lei il primo elemento: a 0.5 catturava la ronda-c
    #: (Jaccard 0.50) e lasciava fuori la ronda-b (0.43), e il consenso spariva
    #: — non perche' il filtro fosse sbagliato, ma perche' l'ESITO DIPENDE
    #: DALL'ORDINE DI SCRITTURA. E' la stessa forma che @ws4 Nadia ha misurato
    #: su `forward_chain` («con le stesse regole l'esito dipende dall'ordine»),
    #: in un secondo modulo.
    payload = _chiama("hippo_cross_agent_consensus",
                      {"min_agents": 2, "sim_threshold": 0.4})
    gruppi = payload.get("consensus") or []
    quarantenato = "ronda-a"
    insieme = [g for g in gruppi
               if {"ronda-b", "ronda-c"} <= set(g.get("agent_ids") or [])]
    assert insieme, (
        "le due ronde SANE (ronda-b, ronda-c) non finiscono in nessun gruppo "
        "insieme: senza quel gruppo «nessun quarantenato nel consenso» sarebbe "
        "vero anche a consenso VUOTO, e questo test non misurerebbe niente. "
        f"Payload: {json.dumps(payload, ensure_ascii=False, default=str)[:600]}")
    votanti = sorted({a for g in gruppi for a in (g.get("agent_ids") or [])})
    assert quarantenato not in votanti, (
        f"il gruppo di CONSENSO conta {quarantenato!r} fra gli agenti "
        "concordi, e quell'agente ha scritto una riga che il moat ha fermato "
        f"(grounding 0,25). n_agents dei gruppi: "
        f"{[g.get('n_agents') for g in gruppi]}, agent_ids: {votanti}. "
        "Il prodotto presenta come «strong evidence» un accordo a cui "
        "partecipa un fatto non verificato — e chi legge il payload non puo' "
        f"accorgersene, perche' i membri non ci sono.\n  {store['diagnosi']}")


def test_sdk_memory_get_all_non_serve_un_quarantenato(store):
    """`Memory.get_all` (`client.py:3959`) — l'ottavo ingresso, trovato da
    @ws3 Galileo. Non e' MCP: e' l'SDK python, la porta di chi INTEGRA il
    prodotto. Il docstring promette «List stored facts (with provenance)»."""
    from verimem.client import Memory
    m = Memory(path=store["percorso"])
    righe = m.get_all(limit=1000)
    testo = _testo(righe)
    # per id, non per testo: vedi la nota in `_asserisci_recupero`.
    assert store["id_sano"] in testo, (
        "get_all non rende nemmeno il fatto sano: sto guardando un altro "
        f"store. percorso={store['percorso']!r} n_righe={len(righe)}")
    assert store["id_quarantenato"] not in testo, (
        "l'SDK rende un quarantenato fra i fatti dell'utente. E' la stessa "
        "riga dei sei tool MCP, in un punto che il ticket T49 non copriva "
        f"finche' @ws3 non l'ha trovata.\n  {store['diagnosi']}")


# ═══════ il settimo: non lo elenca, lo USA — ed e' peggio ═══════

def test_forward_chain_non_deduce_da_una_premessa_quarantenata(store):
    """`hippo_forward_chain` (10493) divide TUTTI i fatti in regole e stato
    parsando la proposizione (`parse_rule`), e non guarda nessuno `status`.

    Misurato dalla porta il 09/09 (mappa ws2): una regola con grounding 0,14 e
    `status=quarantined` ha prodotto una deduzione con `depth` ed `evidence_id`,
    e la proposizione che ne esce nello store NON ESISTE e non porta nessuno
    status. Chi la riceve non ha modo di sapere da dove viene.

    Il controllo positivo e' nella stessa chiamata: la regola SANA (D) deve
    dedurre. Se non deducesse nulla, il verde direbbe solo «il motore e' fermo»."""
    payload = _chiama("hippo_forward_chain", {"max_depth": 3})
    testo = _testo(payload)
    conclusione_sana = "il registro va aggiornato"
    conclusione_avvelenata = "il varco e' insicuro"
    assert conclusione_sana in testo, (
        "forward_chain non deduce NULLA nemmeno dalla regola sana: il motore "
        "non ha girato e questo test non misura il filtro. "
        f"Payload: {json.dumps(payload, ensure_ascii=False, default=str)[:800]}")
    assert conclusione_avvelenata not in testo, (
        "forward_chain ha usato come PREMESSA una regola quarantenata e ha "
        f"emesso la conclusione {conclusione_avvelenata!r}. E' peggio di un "
        "quarantenato in lista: qui esce una proposizione NUOVA, che nello "
        "store non c'e', senza status, e chi la legge non puo' risalire al "
        f"fatto fermato.\n  {store['diagnosi']}")


def test_forward_chain_non_riammette_un_quarantenato_passato_per_id(store):
    """Il NONO ingresso, e non e' un tool nuovo: e' la stessa porta con la
    maniglia esplicita. `hippo_forward_chain` accetta `state_fact_ids` (schema
    a 5493): il chiamante passa gli id A MANO e il codice a 10513 li usa per
    selezionare lo stato, senza guardare nessuno `status`.

    Il README lo promette come proprieta' di SICUREZZA, alle righe 230-231:

        «an exfiltration payload the gate quarantined stays quarantined
         even if a caller passes its id»

    E' scritto della coppia `quarantine_log` / `restore`, ma la frase e'
    generale e un lettore la applica al prodotto: un id non e' un lasciapassare.
    Qui si misura se regge su questa porta.

    ⚠️ Il controllo positivo e' l'altra chiamata: passando l'id del fatto SANO
    la deduzione deve uscire. Senza, «nessuna deduzione» direbbe solo che
    `state_fact_ids` non funziona affatto."""
    ids = {}
    for f in store["agente"].semantic.list_facts(limit=1000, offset=0):
        ids[(getattr(f, "proposition", "") or "").strip().lower()] = getattr(f, "id", "")

    id_sano = ids.get(A_SANO.lower())
    id_quarantenato = store["id_quarantenato"]
    assert id_sano and id_quarantenato, f"id non trovati: {ids}"

    # (1) CONTROLLO POSITIVO, e dev'essere SIMMETRICO al caso in esame: uno
    #     stato passato per id, una regola sana che lo consuma, una deduzione
    #     che esce. Al giro delle 23:14 questo test PASSAVA con un controllo
    #     positivo non simmetrico, e passava per la ragione sbagliata: nessuna
    #     regola aveva il quarantenato come antecedente, quindi «nessuna
    #     deduzione» non voleva dire «filtrato», voleva dire «niente da
    #     dedurre». La regola (E) esiste per chiudere quel buco.
    sano = _chiama("hippo_forward_chain",
                   {"max_depth": 3, "state_fact_ids": [id_sano]})
    assert "il registro va aggiornato" in _testo(sano), (
        "passando l'id del fatto SANO non esce nessuna deduzione: "
        "`state_fact_ids` non seleziona niente e il caso sotto non "
        f"misurerebbe il filtro. Payload: {json.dumps(sano, ensure_ascii=False, default=str)[:500]}")

    # (2) e adesso l'id del QUARANTENATO. La regola (E) che lo consuma e' SANA
    #     e viva: fra questa chiamata e quella sopra cambia solo lo STATUS.
    avvelenato = _chiama("hippo_forward_chain",
                         {"max_depth": 3, "state_fact_ids": [id_quarantenato]})
    testo = _testo(avvelenato)
    assert "il deposito va ispezionato" not in testo, (
        "un chiamante ha passato l'id di un fatto QUARANTENATO in "
        "`state_fact_ids`, la porta l'ha usato come stato e ne ha dedotto "
        "«il deposito va ispezionato». Il README alle righe 230-231 promette "
        "che un contenuto fermato dal gate «stays quarantined even if a "
        "caller passes its id»: su questa porta un id E' un lasciapassare.\n"
        f"  id={id_quarantenato!r}\n"
        f"  payload={json.dumps(avvelenato, ensure_ascii=False, default=str)[:500]}")


# ═══════ (b) LE PORTE DI PULIZIA: deve uscire, ma DEVE dire lo status ═══════
#
# Qui il verde NON e' «zero quarantenati». Nascondere i quarantenati a chi
# ripara il corpus renderebbe il corpus irreparabile. Cio' che manca e' che il
# payload DICA quale membro della coppia il gate aveva gia' fermato.
#
# La soglia di similarita' e' abbassata a mano nelle due chiamate: le due righe
# della ronda hanno Jaccard ~0,67 e il default (0,7) non le accoppierebbe. Con
# zero coppie il test passerebbe senza aver guardato niente.

def _asserisci_pulizia(payload: dict, dove: str, store: dict) -> None:
    testo = _testo(payload)
    #: ⚠️ NON si cerca la proposizione: `hippo_find_duplicate_facts` rende
    #: `representative_proposition` piu' una lista di `fact_ids`, cioe' i membri
    #: NON rappresentativi compaiono solo come ID. Cercare il testo diceva
    #: «nessuna coppia» su un payload che la coppia ce l'aveva (giro delle
    #: 23:07, `max_similarity: 0.778`). Se ne e' accorto il controllo positivo,
    #: che e' l'unica ragione per cui questa riga adesso e' giusta.
    ident = store["id_quarantenato"]
    assert ident and ident in testo, (
        f"{dove} non ha trovato nessuna coppia che contenga il quarantenato "
        f"(id={ident!r}): senza quella coppia non c'e' niente da dichiarare e "
        "questo test sarebbe verde a vuoto. Payload: "
        f"{json.dumps(payload, ensure_ascii=False, default=str)[:600]}")
    assert "quarantined" in testo, (
        f"{dove} mette in coppia un fatto SANO e uno QUARANTENATO e nel "
        "payload non compare mai lo status: chi ripara non ha modo di sapere "
        "quale dei due il gate aveva gia' fermato, e puo' fondere il buono "
        f"dentro il cattivo.\n  {store['diagnosi']}")


def test_find_duplicate_facts_dice_lo_status_dei_membri(store):
    """`hippo_find_duplicate_facts` (10214) — via `memory_compaction`."""
    _asserisci_pulizia(
        _chiama("hippo_find_duplicate_facts",
                {"sim_threshold": 0.3, "top_k": 50}),
        "hippo_find_duplicate_facts", store)


def test_facts_find_duplicates_dice_lo_status_dei_membri(store):
    """`hippo_facts_find_duplicates` (11851) — via `find_duplicate_facts`.
    Due tool con lo stesso nome girato e due moduli diversi dietro: e' la
    classe «una copia invece della superficie unica» (R3)."""
    _asserisci_pulizia(
        _chiama("hippo_facts_find_duplicates",
                {"threshold": 0.3, "top_k": 50}),
        "hippo_facts_find_duplicates", store)
