"""«Provenance on every read»: ogni porta di lettura consegna chi, da dove, e con quale verdetto.

PERCHE' QUESTO FILE ESISTE. Il README dichiara, nella tabella delle capacita':

    | Provenance on every read (who wrote it, source ref, gate status) | every hit |

Misurato il 2026-08-13, **nessun test nominava quella riga**: la promessa era
scritta e non ancorata. Non e' che mancassero i test sulla provenienza — ce ne
sono diciotto che toccano quei campi — ma nessuno legava **la riga** al
comportamento, ed e' una differenza che ci ha gia' morsi una volta: il README
dichiarava «abstains 2/2» mentre il bench citato diceva zero, e i test
sull'astensione erano verdi perche' provavano il comportamento, non la riga.

COSA COPRE, E COSA NO — dichiarato, perche' «every read» e' una parola grossa:
  · copre le porte di lettura dell'**SDK Python** (`Memory`), esercitate a
    runtime su un archivio vero costruito nel test;
  · **non** copre l'MCP ne' la CLI. Per l'MCP esiste gia'
    ``test_fact_ha_un_contratto_di_uscita``, che pero' e' un'analisi **statica**
    dei tredici punti di ``mcp_server.py`` che costruiscono a mano il dict di un
    fatto: misura che i campi ci siano nel CODICE, non che escano da una
    chiamata. I due sono complementari e nessuno dei due copre l'altro.

CHE COSA SIGNIFICA «provenienza», qui: i tre elementi che la riga del README
enumera, e non uno di piu' —
    chi l'ha scritto ....... ``writer_principal``
    da dove ................ ``source``
    con che verdetto ....... ``status`` **e** ``grounding_score``
``grounding_score`` fa parte del verdetto e non e' un di piu': `null` significa
mai giudicato, che e' diverso da giudicato e passato, e senza quel campo lo
stato da solo non distingue i due casi.

⚠️ IL SENSORE CHE POTREBBE SCOLLEGARSI, e la guardia che lo impedisce: se un
domani una porta venisse rinominata o aggiunta, un elenco fisso continuerebbe a
passare **sulle porte vecchie**, in silenzio. Il primo test confronta percio'
l'elenco con cio' che l'SDK espone davvero: una porta di lettura non
classificata fa fallire il file, e chi la aggiunge decide se va presidiata.
"""
from __future__ import annotations

import inspect

import pytest

from verimem import Memory

#: I tre elementi che la riga del README promette, con il campo che li porta.
PROVENIENZA = ("writer_principal", "source", "status", "grounding_score")

#: Le porte di lettura dell'SDK e come si chiamano. Il valore e' la chiamata:
#: prende la memoria e restituisce la lista di risultati.
PORTE = {
    "search": lambda m: m.search("pallet Rovigo"),
    "recall": lambda m: m.recall("pallet Rovigo"),
    "get_all": lambda m: m.get_all(),
}

#: Metodi pubblici che NON sono letture di fatti, o che restituiscono un
#: dossier invece di una lista di hit. Elencati perche' il primo test possa
#: distinguere «non presidiata» da «non pertinente» — e perche' aggiungerne una
#: qui sia una decisione scritta, non una dimenticanza.
NON_HIT = frozenset({
    "explain", "trust_report",          # dossier di provenienza, forma diversa
    "get",                              # un fatto per id, non una lista di hit
    "consistency_trust", "source_trust", "source_trust_observe", "trust_stats",
    "forget", "forget_with_report",     # scritture, non letture
    # ⚠️ `search_documents` legge, e la provenienza CE L'HA — ma di un altro
    # oggetto. Misurato il 2026-08-21 in ambiente pulito (venv nuovo, sdist,
    # HF_HOME vuoto), i campi di un hit sono::
    #
    #     doc_id · end · flagged · indexed_by · query_terms · query_terms_matched
    #     score · source_id · start · text · uri · version
    #
    # cioe' `source_id` col percorso del file, `uri`, `version` e persino gli
    # offset `start`/`end` nel documento. Non ha `writer_principal` / `status` /
    # `grounding_score` perche' quei campi descrivono un FATTO scritto da
    # qualcuno e giudicato dal moat, e un chunk di documento non e' ne' l'uno ne'
    # l'altro: e' testo indicizzato, con la sua provenienza propria.
    # ⇒ Non e' «non presidiata»: e' presidiata altrove, dal tier documenti.
    # Metterla in PORTE la farebbe fallire su campi che non le competono.
    "search_documents",
})

_TESTO = "Il magazzino di Rovigo contiene 480 pallet."


@pytest.fixture
def memoria(tmp_path_factory) -> Memory:
    """Un archivio vero con un fatto dentro. Modulo: l'embedder si carica una volta."""
    m = Memory(str(tmp_path_factory.mktemp("prov") / "p.db"))
    m.add(_TESTO, source=_TESTO)
    return m


def test_nessuna_porta_di_lettura_e_sfuggita_alla_classificazione() -> None:
    """La guardia contro il sensore scollegato: una porta nuova non passa in silenzio."""
    pubblici = {
        n for n, _ in inspect.getmembers(Memory, inspect.isfunction)
        if not n.startswith("_")
        and any(k in n for k in ("search", "recall", "get", "explain", "trust", "forget"))
    }
    ignoti = pubblici - set(PORTE) - NON_HIT
    assert not ignoti, (
        f"l'SDK espone porte non classificate: {sorted(ignoti)}. Il README "
        f"promette la provenienza su OGNI lettura: aggiungile a PORTE se "
        f"restituiscono hit, a NON_HIT se non sono letture di fatti — ma "
        f"decidilo, non lasciarle fuori"
    )
    spariti = set(PORTE) - pubblici
    assert not spariti, (
        f"PORTE elenca metodi che l'SDK non espone piu': {sorted(spariti)}. "
        f"Un elenco che nomina il nulla non presidia niente"
    )


@pytest.mark.parametrize("porta", sorted(PORTE))
def test_la_porta_consegna_la_provenienza_su_ogni_hit(porta: str, memoria: Memory) -> None:
    hit = PORTE[porta](memoria)
    if isinstance(hit, dict):
        hit = hit.get("results") or hit.get("facts") or [hit]
    assert hit, (
        f"precondizione: «{porta}» non restituisce nulla su un archivio che "
        f"contiene il fatto cercato — senza hit questo test non misura niente"
    )
    for i, h in enumerate(hit):
        assert isinstance(h, dict), f"«{porta}» hit {i}: atteso un dict, ottenuto {type(h).__name__}"
        mancanti = [c for c in PROVENIENZA if c not in h]
        assert not mancanti, (
            f"«{porta}» hit {i} esce senza {mancanti}: il README promette "
            f"«Provenance on every read (who wrote it, source ref, gate status)» "
            f"su OGNI hit. Chiavi presenti: {sorted(h)}"
        )


def test_la_provenienza_non_e_un_campo_vuoto(memoria: Memory) -> None:
    """I campi ci sono: e dicono qualcosa?

    ⚠️ Complementare al test sopra, e non ridondante: un dict puo' portare tutte
    e quattro le chiavi con dentro ``None``, e passerebbe. Un campo presente e
    vuoto e' una promessa mantenuta nella forma e mancata nella sostanza —
    esattamente cio' che questo file esiste per impedire.

    Su ``grounding_score`` NON si pretende un numero: `null` e' un valore
    legittimo e significa «mai giudicato». Si pretende che la CHIAVE esista,
    ed e' il test sopra a garantirlo.
    """
    hit = memoria.search("pallet Rovigo")
    assert hit, "precondizione: serve almeno un hit"
    h = hit[0]
    assert h.get("writer_principal"), (
        f"«search» consegna writer_principal vuoto ({h.get('writer_principal')!r}): "
        f"il README promette di dire CHI ha scritto il fatto"
    )
    assert h.get("status"), (
        f"«search» consegna status vuoto ({h.get('status')!r}): il README "
        f"promette lo stato del gate"
    )
    assert h.get("grounding_score") is not None or h.get("status") == "model_claim", (
        "il verdetto del gate deve essere leggibile: grounding_score assente su "
        "un fatto che non e' un model_claim mai giudicato"
    )


def test_il_riferimento_alla_fonte_esce_dalla_lettura(memoria: Memory) -> None:
    """Il terzo elemento della riga: «source ref». CURATO il 2026-08-13.

    IL DIFETTO, e la diagnosi vera e' diversa da quella che sembrava. Il campo
    `source` non era vuoto per un difetto di persistenza: era popolato dalla
    fonte SBAGLIATA — ``(source_episodes or [None])[0]``, cioe' l'EPISODIO di
    origine. Chi scrive con ``add(testo, source="…")`` non produce episodi,
    quindi per lui quel campo valeva sempre `None`. **Due cose diverse con lo
    stesso nome**, e il README ne promette una sola: «Provenance on every read
    (who wrote it, SOURCE REF, gate status)» — il primo e il terzo uscivano, il
    secondo no, su un fatto la cui fonte era stata GIUDICATA (grounding 98.85).

    LA CURA: esporre ``source_signature`` col suo nome. L'impronta esiste gia'
    — il write-path la calcola e la persiste proprio perche' la source in
    chiaro non viene conservata — e va servita **come impronta**, non travestita
    da `source`: chi trova `sha256:…` dove si aspetta un testo non riceve una
    risposta migliore, ne riceve una sbagliata.

    ⚠️ E il difetto era peggiore di un campo assente. Un campo ASSENTE dice
    «non lo so»; un campo PRESENTE e vuoto AFFERMA: chi leggeva quel dict
    concludeva che il fatto non avesse una fonte, mentre ne aveva una e il gate
    l'aveva giudicata. E' la stessa forma vista il 10/08 su un'altra porta —
    una superficie che non tace una differenza ma la dichiara al contrario.

    📌 Questo test era ``xfail(strict=True)`` fino alla cura; il marcatore e'
    stato tolto quando strict l'ha segnalato come XPASS, che e' il modo in cui
    doveva accorgersene.
    """
    h = memoria.search("pallet Rovigo")[0]
    riferimenti = [k for k in ("source", "source_ref", "source_signature") if h.get(k)]
    assert riferimenti, (
        f"nessun riferimento alla fonte esce dalla lettura: "
        f"source={h.get('source')!r}, e ne source_ref ne source_signature sono "
        f"fra le chiavi restituite ({sorted(h)}). Il README promette "
        f"«Provenance on every read (who wrote it, source ref, gate status)»"
    )
