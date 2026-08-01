"""«NON» non e' un acronimo, ed era il terzo nodo del grafo di conoscenza.

Reperto dell'altra istanza (in sola lettura), 2026-08-01: «nel grafo entity_kg
la parola NON e' registrata come entita' di tipo acronym», e le prime tre entita'
del ranking PPR per la query «verimem» erano «Loop», «HippoAgent» e «NON».

QUANTIFICATO sul grafo vero (8625 entita', 87879 archi)::

    TOP entita' per GRADO            TOP acronimi per fatti collegati
      1962  [proper ] Loop             416  NON
      1761  [anchor ] HippoAgent       204  CLI
      1494  [acronym] NON              195  LLM
      1061  [anchor ] MCP              189  PASS
       768  [acronym] CYCLE            146  MASTER
       722  [acronym] MASTER           116  NO

La parola «non» e' il TERZO nodo piu' connesso dell'intero grafo. Il PPR ci
cammina sopra per fare retrieval: ecco perche' rispondeva «NON» a una query su
verimem.

LA CAUSA e' una riga: `("acronym", re.compile(r"\\b[A-Z]{2,6}\\b"))`. Qualunque
parola di 2-6 lettere tutta maiuscola diventa una sigla — e nei nostri fatti le
maiuscole sono ENFASI: «NON funziona», «PASS», «MASTER FACT», «LIVE».

QUANTO E' GRANDE: **868 dei 1606 acronimi** del grafo compaiono anche in
minuscolo nel corpus almeno 20 volte. Piu' della meta' del vocabolario di sigle
non sono sigle: ACCEPT, ACCESS, ACTION, ACTIVE, ADMIT, ALLA, ALLE, ALTA, ALTO,
ALTRI…

IL CRITERIO, e perche' NON e' l'ennesima soglia scelta a occhio. La prima idea
era la «quota di occorrenze maiuscole»: misurata, separa quasi — non 0.325, no
0.166, fix 0.068, cycle 0.047 contro api 0.621, cli 0.657, llm 0.889, tdd 0.997
— ma sbaglia su pass 0.742 e master 0.843, che sigle non sono. Un taglio a 0.5
sarebbe stato un numero deciso a occhio, l'errore gia' pagato tre volte questa
settimana.

Il criterio che regge e' una domanda BINARIA, non un punteggio: **questa parola
esiste in minuscolo nella lingua che il corpus usa?** «non», «alla», «pass»,
«master» si'; «tdd», «llm», «api», «mcp» no o quasi mai. Non serve tarare
niente: si guarda il corpus stesso.

Questo file inchioda le due meta':
* una parola comune urlata NON diventa un'entita' di tipo acronimo;
* una sigla vera resta una sigla — altrimenti la cura svuoterebbe il grafo, che
  sarebbe peggio del difetto.
"""
from __future__ import annotations

from verimem.entity_extract_lite import extract_entities_lite


def _tipi(testo: str) -> dict[str, str]:
    """{nome: tipo} per le entita' estratte da `testo`."""
    fuori = {}
    for e in extract_entities_lite(testo):
        nome = e.get("name") if isinstance(e, dict) else getattr(e, "name", None)
        tipo = e.get("type") if isinstance(e, dict) else getattr(e, "type", None)
        if nome:
            fuori[str(nome)] = str(tipo)
    return fuori


def test_una_negazione_urlata_non_e_una_sigla():
    """Il caso che ha originato tutto: 1494 archi nel grafo per «NON»."""
    t = _tipi("Il gate NON ha girato: la scrittura NON e' stata giudicata.")
    assert t.get("NON") != "acronym", (
        f"«NON» e' stata classificata come acronimo: e' il terzo nodo per grado "
        f"del grafo, e il PPR ci cammina sopra. Estratte: {t}")


def test_IL_PERIMETRO_di_questa_cura_e_dichiarato():
    """QUANTO copro, e quanto NO — perche' un verde qui non deve leggersi come
    «il grafo e' pulito».

    La cura usa `document_index._PAROLE_VUOTE`, la lista funzionale che il repo
    ha gia' e che contiene «non»: chiude il caso DOMINANTE (416 fatti, 1494
    archi, terzo nodo del grafo) senza inventare niente.

    NON chiude gli altri 868 acronimi falsi misurati: PASS, MASTER, CYCLE,
    LIVE, ALTA, ALLE non sono parole vuote, sono parole PIENE scritte in
    maiuscolo. Separarle richiede un dizionario della lingua — una scelta di
    prodotto, non un'improvvisazione: la quota-maiuscola misurata sbaglia
    proprio su PASS (0.742) e MASTER (0.843), e una soglia a occhio e' l'errore
    che questo repo ha gia' pagato tre volte.

    Questo test FALLISCE il giorno in cui qualcuno chiude anche quel pezzo, ed
    e' il momento giusto per riscriverlo."""
    t = _tipi("PASS su MASTER: il CYCLE e' LIVE, ALTA priorita'.")
    ancora_sigle = [p for p in ("PASS", "MASTER", "CYCLE", "LIVE", "ALTA")
                    if t.get(p) == "acronym"]
    assert ancora_sigle, (
        "queste parole non sono piu' classificate come acronimi: qualcuno ha "
        "esteso la cura oltre le parole vuote — bene, ma allora questo test va "
        "riscritto per inchiodare il nuovo criterio invece del vecchio limite")


def test_una_SIGLA_VERA_resta_una_sigla():
    """La meta' che conta: senza questa, la cura svuoterebbe il grafo — che
    sarebbe peggio del difetto che cura."""
    t = _tipi("Il server MCP espone i tool via CLI, e il giudice usa un LLM. "
              "Ciclo TDD con misura MRR.")
    for sigla in ("MCP", "CLI", "LLM", "TDD", "MRR"):
        assert t.get(sigla) == "acronym", (
            f"«{sigla}» non e' piu' riconosciuta come sigla: la cura ha tolto "
            f"anche le entita' vere. Estratte: {t}")
