# -*- coding: utf-8 -*-
"""«Il paziente e' deceduto» -> «il paziente e' stato dimesso» viene AMMESSO.

Trovato il 26/08 verificando un'altra cosa. La mia garanzia in vetrina (README,
commit c62da996) dice: «a claim the source **contradicts** does not come back
as truth», con 0/10, 1/10 e 2/10 su tre classi.

Ma tutte e tre le classi che ho misurato usano contraddizioni **ESPLICITE**:
la fonte dice «non e' stato approvato» e il claim dice «e' stato approvato»,
oppure la fonte dice «nord» e il claim dice «sud». Il conflitto e' visibile
nelle parole.

Una contraddizione **IMPLICITA** non nega il claim: lo esclude per implicazione.
«Deceduto» non contiene «non dimesso» — lo rende impossibile. E il primo caso
provato passa::

    fonte  «Referto: il paziente e' deceduto il 30 luglio nel reparto di
            terapia intensiva.»
    claim  «Il paziente e' stato dimesso il 30 luglio.»
    esito  ADMITTED

⚠️ Con un caso solo non e' una misura — e' la lezione che stamattina mi ha
fatto ritirare una conclusione pubblica. Da qui la batteria.

DISEGNO: dieci contraddizioni implicite, IT/EN appaiate sulla stessa fonte,
VERI di controllo. Nessuna nega il claim con un negatore: ogni fonte afferma un
fatto che rende il claim impossibile.
🔑 E per separare questa classe dalle tre gia' misurate, ogni caso ha anche la
sua versione ESPLICITA: stessa fonte, ma il claim contraddetto da un negatore.
Se l'esplicita si ferma e l'implicita passa, la differenza e' l'inferenza — e
la mia riga in vetrina copre meno di quanto dice.
⛔ Nessun numero cambia fra fonte e claim: L4.1 non deve intervenire.

COSA DECIDE: se le implicite passano in quota non trascurabile, «a claim the
source contradicts does not come back as truth» e' vero solo per le
contraddizioni LESSICALMENTE VISIBILI, e la riga va qualificata di nuovo — ed
e' mia, l'ho scritta io due ore fa.

MISURATO 26/08 — IN ITALIANO L'IMPLICITA PASSA 3/10, L'ESPLICITA ZERO::

    falsita' ammesse  IT  IMPLICITA  3/10      IT  esplicita  0/10
    falsita' ammesse  EN  IMPLICITA  0/10      EN  esplicita  0/10
    VERI rifiutati    IT 0/10   EN 0/10

① LA DIFFERENZA E' L'INFERENZA, e il controllo e' nella stessa riga: sulla
STESSA fonte, il claim contraddetto da un negatore viene sempre fermato (0/10),
quello contraddetto per implicazione passa tre volte su dieci. Non e' la fonte,
non e' il dominio, non e' la lunghezza: e' se il conflitto sia visibile nelle
parole.
② I TRE CASI CHE PASSANO, e non sono di laboratorio:
    «il paziente e' DECEDUTO il 30 luglio»    -> «e' stato DIMESSO il 30 luglio»
    «Ferraris dichiarata FALLITA a giugno»    -> «ha chiuso il bilancio in UTILE»
    «il magazzino nord risulta VUOTO»         -> «sono stoccati i lotti di aprile»
   Referto medico, sentenza, inventario. Sono i documenti che questo prodotto
   esiste per ricordare, e il claim ammesso e' quello che un LLM produce quando
   riassume male.
③ E L'INGLESE REGGE: 0/10 su entrambe. L'asimmetria IT/EN su questa classe e'
reale e va nella direzione peggiore per noi — Aurelio chiede «impeccabile
almeno in inglese e italiano».

⇒ LA MIA RIGA IN VETRINA E' ANCORA TROPPO GENEROSA. «a claim the source
contradicts does not come back as truth» e' vera in EN e falsa 3 volte su 10 in
IT quando la contraddizione richiede un passo di inferenza. E' la SECONDA volta
stasera che devo qualificare una riga scritta da me: la prima era troppo severa
sulle scritture, questa e' troppo generosa sull'italiano. Le due correzioni
vanno in direzioni opposte, il che dice che il problema non era la prudenza ma
la POPOLAZIONE su cui avevo misurato.

Regime: porta pubblica `verimem remember --source`, store temporaneo, FUORI
pytest.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_implicita_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (nome, fonte_IT, vero_IT, implicito_IT, esplicito_IT,
#:        fonte_EN, vero_EN, implicito_EN, esplicito_EN)
CASI = [
    ("deceduto",
     "Referto: il paziente e' deceduto il 30 luglio in terapia intensiva.",
     "Il paziente e' deceduto il 30 luglio.",
     "Il paziente e' stato dimesso il 30 luglio.",
     "Il paziente non e' deceduto il 30 luglio.",
     "Report: the patient died on 30 July in intensive care.",
     "The patient died on 30 July.",
     "The patient was discharged on 30 July.",
     "The patient did not die on 30 July."),
    ("difforme",
     "Collaudo: due pezzi del lotto B12 risultano difformi dalle specifiche.",
     "Due pezzi del lotto B12 risultano difformi dalle specifiche.",
     "Il lotto B12 e' conforme alle specifiche.",
     "Nessun pezzo del lotto B12 risulta difforme dalle specifiche.",
     "Inspection: two items of batch B12 are out of specification.",
     "Two items of batch B12 are out of specification.",
     "Batch B12 conforms to specification.",
     "No item of batch B12 is out of specification."),
    ("demolito",
     "Atto: il capannone di Rovigo e' stato demolito a marzo.",
     "Il capannone di Rovigo e' stato demolito a marzo.",
     "Il capannone di Rovigo e' stato ristrutturato a marzo.",
     "Il capannone di Rovigo non e' stato demolito a marzo.",
     "Deed: the Rovigo shed was demolished in March.",
     "The Rovigo shed was demolished in March.",
     "The Rovigo shed was refurbished in March.",
     "The Rovigo shed was not demolished in March."),
    ("dimissioni",
     "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio.",
     "Il direttore ha rassegnato le dimissioni il 4 maggio.",
     "Il direttore e' stato confermato nell'incarico il 4 maggio.",
     "Il direttore non ha rassegnato le dimissioni il 4 maggio.",
     "Minutes: the director resigned on 4 May.",
     "The director resigned on 4 May.",
     "The director was confirmed in office on 4 May.",
     "The director did not resign on 4 May."),
    ("fallimento",
     "Sentenza: la societa' Ferraris e' stata dichiarata fallita a giugno.",
     "La societa' Ferraris e' stata dichiarata fallita a giugno.",
     "La societa' Ferraris ha chiuso il bilancio in utile a giugno.",
     "La societa' Ferraris non e' stata dichiarata fallita a giugno.",
     "Ruling: Ferraris was declared bankrupt in June.",
     "Ferraris was declared bankrupt in June.",
     "Ferraris closed the year in profit in June.",
     "Ferraris was not declared bankrupt in June."),
    ("scaduto",
     "Registro: il contratto con il fornitore e' scaduto il 31 dicembre.",
     "Il contratto con il fornitore e' scaduto il 31 dicembre.",
     "Il contratto con il fornitore era in vigore a gennaio.",
     "Il contratto con il fornitore non e' scaduto il 31 dicembre.",
     "Registry: the supplier contract expired on 31 December.",
     "The supplier contract expired on 31 December.",
     "The supplier contract was in force in January.",
     "The supplier contract did not expire on 31 December."),
    ("vuoto",
     "Inventario: il magazzino nord risulta completamente vuoto.",
     "Il magazzino nord risulta completamente vuoto.",
     "Nel magazzino nord sono stoccati i lotti di aprile.",
     "Il magazzino nord non risulta vuoto.",
     "Inventory: the north warehouse is completely empty.",
     "The north warehouse is completely empty.",
     "The April batches are stored in the north warehouse.",
     "The north warehouse is not empty."),
    ("annullata",
     "Comunicazione: la riunione del 12 aprile e' stata annullata.",
     "La riunione del 12 aprile e' stata annullata.",
     "Alla riunione del 12 aprile hanno partecipato tutti i soci.",
     "La riunione del 12 aprile non e' stata annullata.",
     "Notice: the 12 April meeting was cancelled.",
     "The 12 April meeting was cancelled.",
     "All members attended the 12 April meeting.",
     "The 12 April meeting was not cancelled."),
    ("respinto",
     "Protocollo: il ricorso e' stato respinto con sentenza definitiva.",
     "Il ricorso e' stato respinto con sentenza definitiva.",
     "Il ricorso e' stato accolto.",
     "Il ricorso non e' stato respinto.",
     "Registry: the appeal was dismissed by final judgment.",
     "The appeal was dismissed by final judgment.",
     "The appeal was upheld.",
     "The appeal was not dismissed."),
    ("sospeso",
     "Nota: il servizio di pagamento e' sospeso fino a nuovo avviso.",
     "Il servizio di pagamento e' sospeso fino a nuovo avviso.",
     "Il servizio di pagamento e' operativo.",
     "Il servizio di pagamento non e' sospeso.",
     "Note: the payment service is suspended until further notice.",
     "The payment service is suspended until further notice.",
     "The payment service is operational.",
     "The payment service is not suspended."),
]

_L = re.compile(r"\b(L1(?:\.\d+)?|L3[\w-]*|L4(?:\.\d+)?[\w-]*|store-screen)\b")


def esegui(claim: str, source: str):
    buf = io.StringIO()
    sys.argv = ["verimem", "remember", claim, "--source", source]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            main()
    except SystemExit:
        pass
    except Exception as e:                                    # noqa: BLE001
        return "ECCEZIONE", None, type(e).__name__
    o = buf.getvalue()
    esito = ("admitted" if re.search(r"\badmitted\b", o)
             else "quarantined" if re.search(r"\bquarantined\b", o) else "?")
    m = re.search(r"grounding ([\d.]+)", o)
    return esito, (float(m.group(1)) if m else None), (
        "+".join(sorted(set(_L.findall(o)))) or "-")


def main_banco() -> None:
    print("%-12s %-3s %-11s %-12s %7s  %s"
          % ("caso", "lg", "tipo", "esito", "g", "layer"))
    amm = {("IT", "IMPLICITA"): 0, ("IT", "esplicita"): 0,
           ("EN", "IMPLICITA"): 0, ("EN", "esplicita"): 0}
    rif = {"IT": 0, "EN": 0}
    for c in CASI:
        nome = c[0]
        for lg, src, vero, impl, espl in (
                ("IT", c[1], c[2], c[3], c[4]),
                ("EN", c[5], c[6], c[7], c[8])):
            e_v, g_v, l_v = esegui(vero, src)
            if e_v != "admitted":
                rif[lg] += 1
            print("%-12s %-3s %-11s %-12s %7s  %-20s %s"
                  % (nome, lg, "VERO", e_v,
                     ("%.1f" % g_v) if g_v is not None else "-", l_v,
                     "" if e_v == "admitted" else "<<< VERO RIFIUTATO"))
            for tipo, claim in (("IMPLICITA", impl), ("esplicita", espl)):
                e, g, layer = esegui(claim, src)
                if e != "quarantined":
                    amm[(lg, tipo)] += 1
                print("%-12s %-3s %-11s %-12s %7s  %-20s %s"
                      % ("", lg, tipo, e,
                         ("%.1f" % g) if g is not None else "-", layer,
                         "" if e == "quarantined" else "<<< AMMESSA"))
        print()
    n = len(CASI)
    print("=" * 80)
    for lg in ("IT", "EN"):
        for tipo in ("IMPLICITA", "esplicita"):
            print("  falsita' ammesse  %s  %-11s %2d/%d"
                  % (lg, tipo, amm[(lg, tipo)], n))
    print("  VERI rifiutati    IT %d/%d   EN %d/%d" % (rif["IT"], n, rif["EN"], n))
    print()
    print("  IMPLICITA alta ed esplicita zero -> la garanzia in vetrina copre")
    print("  solo le contraddizioni LESSICALMENTE VISIBILI, e la riga e' mia.")


if __name__ == "__main__":
    main_banco()
