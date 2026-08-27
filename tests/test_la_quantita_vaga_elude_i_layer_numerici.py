"""Una quantita' VAGA elude tutti i layer numerici: «quasi tutti» entra a 99.8.

Misurato il 2026-08-27 alle 18:34, fuori da pytest, store isolato,
`validate="full"`, CE locale. Nasce da una segnalazione di ws3: «il numerico e'
fermato 18 su 18 e SEMPRE da `L4.1` — se `L4.1` cade, nessun altro layer la
raccoglie». Provando ad aggirarlo escono DUE correzioni.

① «NESSUN ALTRO RACCOGLIE» NON REGGE. Sullo stesso claim falso, riscritto:

    cifre esplicite («7 su 40»)        TRATT  0.6   [L4.1, L4.2, L4-grounding]
    numero in LETTERE («sette»)        TRATT  0.5   [L4-grounding]   <- raccoglie
    frazione («un quinto»)             TRATT  0.4   [L4-grounding]   <- raccoglie
    percentuale a parole («diciassette per cento»)  passa 93.7
    quantita' VAGA («gran parte»)                   passa 99.0

Su lettere e frazioni `L4-grounding` prende il posto di `L4.1`. Il punto singolo
non e' cosi' singolo.

② MA IL BUCO C'E', ED E' LA QUANTIFICAZIONE VAGA. La fonte da' sempre una
quantita' piccola ed esatta; il claim ne afferma una grande e vaga:

    caso       claim falso                          esito        layer
    collaudo   «gran parte dei pezzi» / 3 su 40     passa 99.0   []
    ritardi    «la maggioranza» / 2 su 55           passa 93.0   []
    assenze    «quasi tutti» / 4 su 28              passa 99.8   []
    guasti     «guasti frequenti» / 1 su 120        TRATT  0.8   [L4-grounding]

    falsita' vaghe ammesse 3/4 · VERI di controllo ammessi 4/4

⇒ Tre su quattro entrano con ZERO layer che parlano. I layer numerici
confrontano CIFRE: una quantificazione vaga non ne ha, quindi non viene
confrontata — e il giudice semantico la trova sostenuta perche' la fonte parla
dello stesso fatto.

Il caso che regge («frequenti») e' l'unico dove la parola vaga non e' una
quantita' RELATIVA: suggerisce che il buco sia nelle relative (gran parte,
maggioranza, quasi tutti), non nella vaghezza in se'. Non e' verificato.

⚠️ Quattro casi, italiano, un solo tipo di fonte (piccola quantita' esatta). Non
e' un tasso. Mai col giudice llm.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

#: (nome, fonte con quantita' piccola ed esatta, claim VAGO e falso, claim VERO)
CASI = [
    ("collaudo",
     "Il collaudo del lotto B12 ha rilevato 3 pezzi difformi su 40 controllati.",
     "Il collaudo ha rilevato difformita in gran parte dei pezzi.",
     "Il collaudo ha rilevato 3 pezzi difformi su 40."),
    ("ritardi",
     "Nel trimestre 2 consegne su 55 sono arrivate in ritardo.",
     "Nel trimestre la maggioranza delle consegne e arrivata in ritardo.",
     "Nel trimestre 2 consegne su 55 sono arrivate in ritardo."),
    ("assenze",
     "Al corso 4 iscritti su 28 non hanno completato i moduli.",
     "Al corso quasi tutti gli iscritti non hanno completato i moduli.",
     "Al corso 4 iscritti su 28 non hanno completato i moduli."),
]


def _esito(claim: str, fonte: str) -> tuple[str, float | None]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "vago.db"))
    ric = mem.add(claim, topic="t/vago", source=fonte, validate="full")
    return str(ric.get("status")), ric.get("grounding_score")


@pytest.mark.parametrize("nome,fonte,_vago,vero", CASI)
def test_CONTROLLO_il_claim_con_le_cifre_ESATTE_resta_ammesso(nome, fonte, _vago, vero):
    """L'altra popolazione: la cura non deve rendere il gate cieco ai veri."""
    stato, punteggio = _esito(vero, fonte)
    assert stato != "quarantined", (
        f"[{nome}] un claim che ripete le cifre della fonte viene rifiutato "
        f"({stato}, g={punteggio})"
    )


@pytest.mark.parametrize("nome,fonte,vago,_vero", CASI)
def test_CONTROLLO_le_stesse_cifre_SBAGLIATE_sono_fermate(nome, fonte, vago, _vero):
    """Il righello: se il gate non ferma nemmeno le cifre sbagliate, l'xfail
    sotto non misura la vaghezza ma un gate spento."""
    del vago
    sbagliato = fonte.replace(" 3 ", " 7 ").replace(" 2 ", " 9 ").replace(" 4 ", " 21 ")
    if sbagliato == fonte:
        pytest.fail(f"[{nome}] non sono riuscita a costruire il claim con cifre sbagliate")
    stato, punteggio = _esito(sbagliato, fonte)
    assert stato == "quarantined", (
        f"[{nome}] il gate non ferma nemmeno cifre sbagliate ({stato}, g={punteggio}): "
        "il banco non misura piu' l'effetto della vaghezza"
    )


@pytest.mark.xfail(
    strict=True,
    reason="la quantificazione vaga non ha cifre da confrontare e sfugge a tutti "
    "i layer numerici: 3 falsita' su 4 ammesse con zero layer (27/08)",
)
@pytest.mark.parametrize("nome,fonte,vago,_vero", CASI)
def test_la_quantita_vaga_e_falsa_dovrebbe_essere_fermata(nome, fonte, vago, _vero):
    stato, punteggio = _esito(vago, fonte)
    assert stato == "quarantined", f"[{nome}] ammessa con g={punteggio}"


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-27, 18:40 — IL VERSO OPPOSTO, ed è PEGGIORE: 4 su 4.
#
# Sopra la fonte dà una quantità piccola e il claim ne afferma una grande
# («gran parte» contro 3 su 40). Qui la fonte dà una quantità GRANDE e il claim
# la MINIMIZZA con una vaga piccola:
#
#     reazioni  «pochi pazienti»        contro  30 su 40    passa 98.1  []
#     difetti   «qualche pezzo»         contro  35 su 40    passa 85.6  []
#     ritardi   «una minoranza»         contro  48 su 55    passa 99.7  []
#     guasti    «guasti sporadici»      contro  90 su 120   passa 96.1  []
#
#     falsità minimizzanti ammesse 4/4 · VERI di controllo ammessi 4/4
#
# Tutte e quattro con ZERO layer. E «sporadici» passa qui, mentre nel verso
# opposto «frequenti» era stato fermato da L4-grounding: non è la parola, è la
# direzione.
#
# 🔑 È il verso più pericoloso in un uso reale. Un referto riassunto male che
# dice «pochi pazienti hanno avuto reazioni avverse» quando la fonte ne conta 30
# su 40 NASCONDE un problema che la fonte dichiara — e il prodotto lo certifica
# a 98.1. Il verso opposto (esagerare) produce un allarme falso, che qualcuno
# controlla; questo produce un silenzio, che nessuno controlla.

MINIMIZZANTI = [
    ("reazioni",
     "Nello studio 30 pazienti su 40 hanno avuto reazioni avverse.",
     "Nello studio pochi pazienti hanno avuto reazioni avverse.",
     "Nello studio 30 pazienti su 40 hanno avuto reazioni avverse."),
    ("ritardi-min",
     "Nel trimestre 48 consegne su 55 sono arrivate in ritardo.",
     "Nel trimestre una minoranza delle consegne e arrivata in ritardo.",
     "Nel trimestre 48 consegne su 55 sono arrivate in ritardo."),
    ("guasti-min",
     "L impianto ha registrato 90 guasti su 120 giorni di esercizio.",
     "L impianto ha registrato guasti sporadici nel periodo.",
     "L impianto ha registrato 90 guasti su 120 giorni."),
]


@pytest.mark.parametrize("nome,fonte,_vago,vero", MINIMIZZANTI)
def test_CONTROLLO_anche_qui_il_claim_con_le_cifre_resta_ammesso(nome, fonte, _vago, vero):
    stato, punteggio = _esito(vero, fonte)
    assert stato != "quarantined", (
        f"[{nome}] un claim che ripete le cifre della fonte viene rifiutato "
        f"({stato}, g={punteggio})"
    )


@pytest.mark.xfail(
    strict=True,
    reason="il verso minimizzante è peggiore: 4 falsità su 4 ammesse, tutte con "
    "zero layer — «pochi pazienti» contro 30 su 40 entra a 98.1 (27/08)",
)
@pytest.mark.parametrize("nome,fonte,vago,_vero", MINIMIZZANTI)
def test_la_vaghezza_che_MINIMIZZA_dovrebbe_essere_fermata(nome, fonte, vago, _vero):
    stato, punteggio = _esito(vago, fonte)
    assert stato == "quarantined", f"[{nome}] ammessa con g={punteggio}: nasconde ciò che la fonte dichiara"


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-27, 18:45 — E NON È UN DIFETTO ITALIANO: 3/3 in entrambe le lingue.
#
#     caso       ITALIANO            INGLESE
#     reazioni   passa 98.1  []      passa 90.5  []
#     ritardi    passa 99.7  []      passa 87.7  []
#     collaudo   passa 98.7  []      passa 84.6  []
#     ⇒ falsità vaghe ammesse: italiano 3/3 · inglese 3/3
#
# 🔑 È il PRIMO difetto simmetrico fra le due lingue misurato su questo gate.
# Tutti gli altri del 26/08 davano l'inglese più robusto — contorno in prosa EN
# 25.2 contro IT 98.4, contraddizioni implicite EN 0/10 contro IT 3/10. Qui no.
# I punteggi inglesi sono più bassi (84-90 contro 98-99): il giudice è più
# prudente, ma non abbastanza per fermarne una.
#
# ⇒ Non è una debolezza dell'italiano da curare con una lista: è una lacuna del
# modello, e va dichiarata come limite in entrambe le lingue.

EN = ("reactions",
      "In the study 30 patients out of 40 had adverse reactions.",
      "In the study few patients had adverse reactions.",
      "In the study 30 patients out of 40 had adverse reactions.")


def test_CONTROLLO_in_inglese_il_claim_con_le_cifre_resta_ammesso():
    _, fonte, _vago, vero = EN
    stato, punteggio = _esito(vero, fonte)
    assert stato != "quarantined", f"il claim con le cifre è rifiutato in EN ({stato}, g={punteggio})"


@pytest.mark.xfail(
    strict=True,
    reason="la vaghezza elude anche in inglese: 3/3 come in italiano, primo "
    "difetto simmetrico fra le due lingue su questo gate (27/08)",
)
def test_E_NON_E_UN_DIFETTO_ITALIANO_la_vaghezza_elude_anche_in_inglese():
    _, fonte, vago, _vero = EN
    stato, punteggio = _esito(vago, fonte)
    assert stato == "quarantined", f"«few patients» contro 30 out of 40 ammessa con g={punteggio}"


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-27, 18:59 — E NON È TEORICO: passa dalla PORTA UFFICIALE dei documenti.
#
# `promote_chunk_to_fact` è la via per cui un chunk recuperato diventa un fatto,
# e il suo docstring dice: «The caller may pass a distilled `claim` (one clean
# sentence) instead of the raw chunk text». Cioè: un LLM legge il chunk e ne
# scrive una frase — esattamente il caso di questo banco.
#
# Il modulo è cablato BENE: passa il chunk come `source` e chiede
# `ground_write=True` (document_promote.py:89-91), e il commento sopra quella
# riga dice già la cosa giusta — «il caso d'uso principale del modulo È il caso
# d'uso principale del moat». Il moat gira davvero:
#
#     chunk: «…il collaudo del lotto B12 ha rilevato 3 pezzi difformi su 40…»
#
#     claim distillato        status         grounding NELLO STORE
#     VERO («3 su 40»)        model_claim    99.9
#     VAGO («gran parte»)     model_claim    99.6      <- 3 decimi dal vero
#     MINIMIZZA («qualche»)   model_claim    99.7
#     CONTRADDICE («non ha»)  quarantined     0.8
#
# ⇒ La contraddizione esplicita è fermata. Le due vaghe entrano con un punteggio
#   indistinguibile da quello del claim vero — e con la citazione esatta del file
#   in `verified_by`.
# 🔑 Il commento del modulo aveva già nominato il rischio: «il fatto esce con
#   l'aria di essere verificato DAL DOCUMENTO mentre il documento può dire il
#   contrario. La provenienza diventa una decorazione». Qui la decorazione è
#   misurata su una quantità.
#
# ⚠️ Il dict che `promote_chunk_to_fact` restituisce NON ha `grounding_score`:
# ha `grounding_note` (None). Chi legge il punteggio da lì trova sempre None e
# può concludere che il moat non sia girato. Il punteggio sta NELLO STORE.

CHUNK_COLLAUDO = (
    "Verbale di collaudo del 3 marzo. Il collaudo del lotto B12 ha rilevato "
    "3 pezzi difformi su 40 controllati. Il lotto e stato accettato con riserva."
)


def _promuovi(claim: str) -> tuple[str, float | None]:
    """Promuove un chunk con un claim distillato e legge il verdetto NELLO STORE."""
    import sqlite3

    from verimem.document_promote import promote_chunk_to_fact
    from verimem.semantic import SemanticMemory

    db = Path(tempfile.mkdtemp()) / "promo.db"
    mem = SemanticMemory(db_path=db)
    hit = {
        "text": CHUNK_COLLAUDO,
        "source_id": "verbale-b12.md",
        "start": 0,
        "end": len(CHUNK_COLLAUDO),
    }
    ric = promote_chunk_to_fact(mem, hit, claim=claim, topic="t/promo")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    riga = con.execute(
        "SELECT status, grounding_score FROM facts WHERE id=?", (ric.get("fact_id"),)
    ).fetchone()
    con.close()
    if not riga:
        pytest.fail(f"il fatto promosso non e' nello store: {ric}")
    return str(riga[0]), riga[1]


def test_CONTROLLO_dalla_porta_documenti_il_claim_VERO_e_ammesso():
    stato, punteggio = _promuovi("Il collaudo ha rilevato 3 pezzi difformi su 40.")
    assert stato != "quarantined", f"il claim vero e' rifiutato ({stato}, g={punteggio})"


def test_CONTROLLO_dalla_porta_documenti_la_CONTRADDIZIONE_e_fermata():
    """Il righello: se non ferma nemmeno questa, la promozione non giudica."""
    stato, punteggio = _promuovi("Il collaudo non ha rilevato pezzi difformi.")
    assert stato == "quarantined", (
        f"la contraddizione esplicita passa dalla promozione ({stato}, g={punteggio}): "
        "il moat non sta girando su questa porta, rimisurare tutto il blocco"
    )


@pytest.mark.xfail(
    strict=True,
    reason="dalla porta ufficiale dei documenti il claim vago entra a 99.6 contro "
    "il 99.9 del claim vero, con la citazione del file in verified_by (27/08)",
)
@pytest.mark.parametrize(
    "vago",
    [
        "Il collaudo ha rilevato difformita in gran parte dei pezzi.",
        "Il collaudo ha rilevato qualche pezzo difforme.",
    ],
)
def test_dalla_porta_documenti_la_vaghezza_dovrebbe_essere_fermata(vago):
    stato, punteggio = _promuovi(vago)
    assert stato == "quarantined", f"ammessa con g={punteggio} e la citazione del file"


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-27, 19:06 — LA RICEVUTA DELLA PROMOZIONE OMETTE UN VERDETTO CHE ESISTE.
#
# `promote_chunk_to_fact` non mette `grounding_score` nel dict che restituisce
# (ha `grounding_note`, sempre None). La scelta è DELIBERATA e ben motivata nel
# modulo: «un punteggio tautologico non è un verdetto» — senza `claim` la
# proposizione È il chunk, il moat verifica «X implica X» e risponde ~100 per
# costruzione (99.95, 99.96, 99.98 misurati il 04/08). Lì `None` è la
# descrizione esatta, e il modulo azzera il punteggio anche nello store.
#
# ⚠️ Ma quel ragionamento vale SENZA claim, e l'omissione vale SEMPRE. Con un
# `claim` distillato il punteggio non è tautologico affatto — si separa:
#
#     SENZA claim (chunk grezzo)         model_claim    None
#     CON claim: vero «3 su 40»          model_claim    99.94
#     CON claim: vago «gran parte»       model_claim    99.60
#     CON claim: contraddetto «non ha»   quarantined     0.79
#     CON claim: estraneo «la mensa»     quarantined     0.11
#
# ⇒ 99.94 / 99.60 / 0.79 / 0.11 non è una tautologia: è un verdetto, e lo store
#   lo conserva. Il dict di ritorno lo butta lo stesso.
# ⇒ Chi promuove con un claim distillato NON può sapere dal ritorno se il moat
#   l'ha giudicato 99.6 o 0.79 — deve andare a leggere lo store. E il caso con
#   claim è il caso d'uso principale del modulo, per suo stesso docstring.
#
# La cura sarebbe esporre `grounding_score` nel dict SOLO quando `claim` è
# passato — dove il numero è un verdetto e non una tautologia. Non la faccio:
# il modulo non è il mio fronte e la scelta attuale è argomentata.

def _promuovi_grezzo() -> tuple[str, float | None]:
    """Promuove SENZA claim: la proposizione è il chunk stesso."""
    import sqlite3

    from verimem.document_promote import promote_chunk_to_fact
    from verimem.semantic import SemanticMemory

    db = Path(tempfile.mkdtemp()) / "grezzo.db"
    mem = SemanticMemory(db_path=db)
    hit = {
        "text": CHUNK_COLLAUDO,
        "source_id": "verbale-b12.md",
        "start": 0,
        "end": len(CHUNK_COLLAUDO),
    }
    ric = promote_chunk_to_fact(mem, hit, topic="t/grezzo")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    riga = con.execute(
        "SELECT status, grounding_score FROM facts WHERE id=?", (ric.get("fact_id"),)
    ).fetchone()
    con.close()
    if not riga:
        pytest.fail(f"il chunk grezzo non e' nello store: {ric}")
    return str(riga[0]), riga[1]


def test_SENZA_claim_il_punteggio_e_azzerato_ed_e_GIUSTO_cosi():
    """La metà che il modulo fa bene, e sta qui perché il banco non esageri.

    Senza `claim` la proposizione è il chunk: il moat verificherebbe «X implica
    X» e risponderebbe ~100 per costruzione. Il modulo azzera il punteggio, e
    `None` è la descrizione esatta di «mai giudicato».
    """
    stato, punteggio = _promuovi_grezzo()
    assert stato != "quarantined", f"il chunk grezzo viene rifiutato ({stato})"
    assert punteggio is None, (
        f"il punteggio tautologico ora e' pubblicato ({punteggio}): se il modulo ha "
        "imparato a distinguerlo, questo banco va rimisurato"
    )


def test_CON_claim_il_punteggio_NON_e_tautologico_e_si_separa():
    """Il righello del test sotto: senza separazione, l'omissione non toglie nulla."""
    _, g_vero = _promuovi("Il collaudo ha rilevato 3 pezzi difformi su 40.")
    _, g_estraneo = _promuovi("La mensa aziendale resta chiusa il primo maggio.")
    assert isinstance(g_vero, (int, float)) and isinstance(g_estraneo, (int, float)), (
        f"un punteggio manca: vero={g_vero} estraneo={g_estraneo}"
    )
    assert g_vero - g_estraneo > 50, (
        f"i punteggi non si separano piu' ({g_vero} contro {g_estraneo}): se sono "
        "diventati tautologici anche con claim, l'omissione dal dict e' giusta e "
        "questo banco va rimisurato"
    )


@pytest.mark.xfail(
    strict=True,
    reason="con un claim distillato il punteggio e' un verdetto vero (99.94 · 99.60 "
    "· 0.79 · 0.11) ma il dict di ritorno non lo espone: chi promuove deve andare "
    "a leggere lo store (27/08)",
)
def test_con_claim_la_ricevuta_dovrebbe_portare_il_punteggio():
    from verimem.document_promote import promote_chunk_to_fact
    from verimem.semantic import SemanticMemory

    mem = SemanticMemory(db_path=Path(tempfile.mkdtemp()) / "ric.db")
    hit = {
        "text": CHUNK_COLLAUDO,
        "source_id": "verbale-b12.md",
        "start": 0,
        "end": len(CHUNK_COLLAUDO),
    }
    ric = promote_chunk_to_fact(
        mem, hit, claim="Il collaudo ha rilevato 3 pezzi difformi su 40.", topic="t/ric"
    )
    assert ric.get("grounding_score") is not None, f"chiavi restituite: {sorted(ric)}"
