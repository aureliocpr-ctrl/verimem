"""Una frase irrilevante nella fonte puo' ribaltare il verdetto del moat.

Misurato il 2026-08-26 alle 21:30, `aad97bcd`, fuori da pytest, store isolato
con `Memory(path=...)`. Claim fisso, nucleo che lo smentisce sempre presente e
mai modificato; l'unica variabile e' cio' che si aggiunge dopo:

    claim:   «Il lotto B12 e' conforme alle specifiche.»
    nucleo:  «Due pezzi del lotto B12 risultano difformi.»

    frasi   char   esito    grounding
    1       43     TRATT      1.8
    2       92     passa     98.9   <- «La mensa aziendale resta chiusa il primo maggio.»
    3       132    passa     99.2
    5       218    passa     99.8

La zavorra ESTRANEA (mensa, corso d'inglese, parcheggio) alza piu' di quella
pertinente al lotto (98.9 contro 97.5): non e' che il contorno sostenga il claim.

⚠️ NON E' UNIVERSALE, e il banco lo dice tenendo dentro il caso che regge. Su
quattro coppie ribalta una sola:

    conforme/difforme  (smentita lontana)  TRATT  1.8  ->  passa  98.9   ribalta
    copertura          (smentita lontana)  TRATT  0.4  ->  TRATT  78.4   +78,0
    collaudo           (smentita vicina)   TRATT 10.3  ->  TRATT   1.6    -8,7
    pagamento          (smentita vicina)   TRATT  2.6  ->  TRATT   1.9    -0,7

Il SEGNO dello spostamento separa le due classi 2 su 2 per direzione: dove la
smentita ripete la parola del claim il punteggio scende, dove non la ripete sale.
Pattern su quattro casi, non legge. Meccanismo compatibile ma NON verificato: il
giudizio prenderebbe la miglior corrispondenza locale — con una frase sola non ha
scelta, con piu' frasi trova una finestra che non contraddice.

Cio' che questo banco afferma e' ESISTENZIALE — «esiste una fonte in cui una
frase irrilevante ribalta il verdetto» — e un caso lo stabilisce. «Succede
sempre» sarebbe universale, vorrebbe una popolazione, e non e' misurato.

⇒ Conseguenza per le misure di casa: le batterie sulla contraddizione (0/10 IT e
EN di ws3, 4/4 con grounding 0.6-1.3 mia) usavano fonti brevi. Restano corrette
nel loro regime; il trasferimento alle fonti reali — output di pytest, log di CI,
documenti — non e' dimostrato.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

ZAVORRA = "La mensa aziendale resta chiusa il primo maggio."
CLAIM = "Il lotto B12 e conforme alle specifiche."
NUCLEO = "Due pezzi del lotto B12 risultano difformi."
# il caso che REGGE: la smentita ripete la parola del claim
CLAIM_VICINO = "Il collaudo del lotto B12 e stato superato."
NUCLEO_VICINO = "Il collaudo del lotto B12 non e stato eseguito."


def _stato(claim: str, fonte: str) -> tuple[str, float | None]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "z.db"))
    ric = mem.add(claim, topic="t/zavorra", source=fonte, validate="full")
    return str(ric.get("status")), ric.get("grounding_score")


def test_CONTROLLO_con_la_sola_smentita_il_moat_la_ferma():
    """Il righello: se non ferma nemmeno questo, l'xfail sotto non dice nulla."""
    stato, punteggio = _stato(CLAIM, NUCLEO)
    assert stato == "quarantined", (
        f"il moat non ferma il claim contro la sola smentita ({stato}, g={punteggio}): "
        "senza questo il banco non misura l'effetto della zavorra"
    )


@pytest.mark.xfail(
    strict=True,
    reason="una frase irrilevante ribalta il verdetto: da quarantined g=1.8 a "
    "ammesso g=98.9, con la smentita invariata nella fonte (26/08)",
)
def test_una_frase_irrilevante_non_dovrebbe_cambiare_il_verdetto():
    stato, punteggio = _stato(CLAIM, f"{NUCLEO} {ZAVORRA}")
    assert stato == "quarantined", f"ammesso con g={punteggio} grazie a una frase sulla mensa"


def test_E_NON_E_UNIVERSALE_dove_la_smentita_ripete_la_parola_del_claim_regge():
    """L'altra popolazione, e sta qui perche' il banco non deve esagerare.

    Su quattro coppie ne ribalta una: le due in cui la smentita ripete la parola
    del claim reggono, e il punteggio scende invece di salire.
    """
    solo, g_solo = _stato(CLAIM_VICINO, NUCLEO_VICINO)
    con, g_con = _stato(CLAIM_VICINO, f"{NUCLEO_VICINO} {ZAVORRA}")
    assert solo == "quarantined", f"il righello del caso vicino e' caduto: {solo}"
    assert con == "quarantined", (
        f"anche il caso «vicino» ora ribalta (g={g_con} contro {g_solo}): l'effetto "
        "e' piu' esteso di quanto il banco dichiari, allargare la misura"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-26, 23:10 — la forma DETERMINISTICA e piu' nuda dello stesso fenomeno,
# trovata partendo da una fonte vera (l'output di `pytest` di un altro file).
#
# La smentita e' SEMPRE l'ultima frase e non cambia mai; l'unica variabile e'
# quanto testo NEUTRO la precede:
#
#     riempimento x1     191 char   TRATT   1.2   avvisi=1
#     riempimento x10   1433 char   passa  99.2   avvisi=0
#     riempimento x30   4193 char   passa  99.2   avvisi=0
#     riempimento x60   8333 char   passa  99.2   avvisi=0
#
# Il riempimento e' italiano corretto e completamente neutro — parla di presenze
# a una riunione — e non nomina ne' il direttore ne' le dimissioni. Il punteggio
# SATURA a 99.2 e non si muove piu' fra 1433 e 8333 char.
#
# ⚠️ TRE SPIEGAZIONI ESCLUSE CON LA MISURA, perche' nessuno le riprovi:
#  · «e' il MAX su finestre»: g(A+B)=99.9 con max(g(A),g(B))=1.6 — il punteggio
#    del tutto non e' derivabile dalle parti.
#  · «e' la LUNGHEZZA in caratteri» — 🪞 ESCLUSIONE RITIRATA il 26/08 alle 23:53.
#    L'avevo dichiarata su UN SOLO PUNTO (riempimento «xxxx yyyy zzzz», 83 char,
#    lascia 0.7). Rifatta a lunghezza crescente con lo STESSO riempimento non
#    linguistico, la smentita sempre in coda e mai modificata:
#
#        copie   char   esito  grounding
#            1     74   TRATT    0.5
#            4    137   TRATT    0.5
#           10    263   TRATT    1.2
#           20    473   passa   85.4
#           40    893   passa   99.9
#           80   1733   TRATT    1.0
#
#    Passa in una FINESTRA (473-893 char) e torna a reggere sopra e sotto. Quindi
#    la lunghezza conta, ma NON in modo monotono — e un'esclusione basata su un
#    punto solo non era un'esclusione. Stessa forma della curva sulla fonte vera:
#    0.4 · 0.1 · 88.7 · 2.4 · 2.4 · 99.5 · 99.8.
#  · E non e' nemmeno la NATURA del contorno (misurato 23:52, 20 frasi ciascuno):
#        italiano prosa   98.4      pseudo-parole IT   99.3
#        tedesco prosa    84.2      soli numeri        99.9
#        inglese prosa    25.2  <- l'unico che regge
#    Un contorno di soli numeri porta il falso a 99.9. L'inglese e' il piu'
#    robusto, coerente con la batteria di ws3 (implicite EN 0/10).
#  · «e' il TRONCAMENTO a 512 token» (transformers avvisa «607 > 512» sulla
#    fonte vera): gli ultimi 1500 char, che stanno sotto la finestra E
#    contengono la smentita, passano lo stesso a 99.0.
#  · «e' la SOVRAPPOSIZIONE LESSICALE col claim» — la tesi di ws5, che sulle sue
#    leve (ricombinare i token della fonte, il traino di una verita' accanto alla
#    falsita') e' esatta. Sul contorno neutro NON regge, misurato il 26/08 alle
#    23:37 con tre grandezze diverse per non falsificarla su una sola lettura:
#
#      prova           presenza  freq.ASS  freq.REL  token  grounding
#      nucleo solo        0.500       2      0.500      4       0.7
#      ripetuto x2        0.500       4      0.500      8      97.6
#      + neutro x10       0.500       2      0.018    114      84.5
#      + neutro x30       0.500       2      0.006    334      98.4
#
#    La presenza e' COSTANTE a 0.500 in tutte le righe; nel contorno neutro la
#    frequenza relativa CROLLA di ottanta volte e il punteggio sale a 98.4.
#    ⇒ il claim attinge MENO dalla fonte, in proporzione, ed e' giudicato PIU'
#    sostenuto. Sono due meccanismi distinti, non uno.
# Il meccanismo di QUESTO caso non lo so. Il fenomeno e' deterministico.
#
# 🔑 E SU UNA FONTE VERA NON E' NEMMENO MONOTONO: con l'output di pytest, al
# crescere del contorno l'esito fa TRATT 0.4 · TRATT 0.1 · passa 88.7 · TRATT
# 2.4 · TRATT 2.4 · passa 99.5 · passa 99.8 — si ribalta tre volte su sette.
# Non e' una soglia da alzare: e' instabile.

RIEMPIMENTO_NEUTRO = (
    "Il verbale riporta le presenze dei partecipanti alla riunione mensile "
    "del comitato tecnico, con i relativi orari di ingresso e di uscita. "
)
SMENTITA_SECCA = "Il direttore ha rassegnato le dimissioni il 4 maggio."
CLAIM_FALSO = "Il direttore e ancora in carica il 4 maggio."


def _con_contorno(copie: int) -> tuple[str, float | None, int]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "n.db"))
    fonte = (RIEMPIMENTO_NEUTRO * copie) + SMENTITA_SECCA
    ric = mem.add(CLAIM_FALSO, topic="t/neutro", source=fonte, validate="full")
    return (
        str(ric.get("status")),
        ric.get("grounding_score"),
        len(ric.get("warnings") or []),
    )


def test_CONTROLLO_senza_contorno_la_falsita_e_fermata():
    """Il righello della sezione: la smentita da sola basta."""
    stato, punteggio, _ = _con_contorno(1)
    assert stato == "quarantined", (
        f"la falsita' entra gia' senza contorno ({stato}, g={punteggio}): "
        "questa sezione non misura piu' l'effetto del riempimento"
    )


@pytest.mark.xfail(
    strict=True,
    reason="basta 1433 char di testo NEUTRO davanti alla smentita perche' il "
    "claim falso entri a 99.2, e satura li' fino a 8333 char (26/08)",
)
@pytest.mark.parametrize("copie", [10, 30, 60])
def test_il_contorno_neutro_non_dovrebbe_far_entrare_la_falsita(copie):
    stato, punteggio, _ = _con_contorno(copie)
    assert stato == "quarantined", f"ammessa con g={punteggio} dopo {copie} copie di contorno"


def test_E_LA_RICEVUTA_NON_DICE_CHE_LA_FONTE_E_TROPPO_LUNGA():
    """Difetto separato e piu' facile da curare: propagare un avviso che esiste.

    ⚠️ E LA GUARDIA ESISTE GIA', SOLO CHE PROTEGGE UN'ALTRA COSA (misurato
    27/08 19:14). `semantic.py:1916` definisce `_rerank_max_doc_chars()` — 2000
    char, «~512 tokens» per suo stesso docstring — e il prodotto la usa in DUE
    punti, entrambi in LETTURA:

        semantic.py:4559        salta il CE se la MEDIANA delle `proposition`
                                del pool supera il cap (stage-2 rerank fatti)
        document_index.py:199   stessa guardia sul rerank dei documenti

    Nessuno dei due e' il MOAT. La guardia protegge il RANKING dal troncamento e
    lascia il GIUDIZIO scoperto: in scrittura una `source` piu' lunga della
    finestra viene giudicata comunque, e la ricevuta tace.

    ⇒ La cura e' a portata: la funzione c'e', il valore e' gia' tarato su una
    misura (LongMemEval 2026-06-10, recall@5 0.723 contro 0.800 sui documenti
    lunghi), e basterebbe chiamarla sul percorso di scrittura — o almeno
    emettere l'avviso invece di tacere.

    Su una fonte che eccede la finestra del giudice, `transformers` avvisa su
    stderr («Token indices sequence length is longer … 607 > 512») ma la
    ricevuta non riporta nulla: chi scrive vede `moat: passed` e un punteggio
    alto, e non ha modo di sapere che il giudice ha letto un pezzo.
    Se un giorno l'avviso compare, questo test diventa rosso — ed e' una buona
    notizia: aggiornarlo.
    """
    stato, punteggio, n_avvisi = _con_contorno(60)
    assert stato != "quarantined", f"ora e' trattenuta ({punteggio}): rimisurare la sezione"
    assert n_avvisi == 0, (
        f"la ricevuta ora porta {n_avvisi} avvisi su una fonte da 8333 char: se uno "
        "di questi dichiara il troncamento, il difetto e' curato e il banco va aggiornato"
    )
