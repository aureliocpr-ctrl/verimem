# -*- coding: utf-8 -*-
"""In italiano il dettaglio aggiunto passa. E' QUEL CASO o e' LA CLASSE?

Il 26/08 ho misurato che un dettaglio non numerico aggiunto a un'entita' vera
passa in IT (e in JA, AR, TH) mentre EN lo ferma. Era UN caso per lingua:
«l'ordine 77 e' partito il 3 marzo CON CORRIERE ESPRESSO». Con un caso solo non
si distingue una lingua che cede da una frase sfortunata.

Questa batteria tiene fermo tutto tranne DUE cose:
  · il TIPO di dettaglio — dieci categorie diverse (mezzo, luogo, causa,
    autore, modalita', tempo, destinatario, stato, strumento, esito), su dieci
    fonti diverse, cosi' un tipo che cade da solo si vede;
  · la LINGUA — ogni caso e' appaiato IT/EN, stessa fonte e stesso claim
    tradotti. E' l'unico modo di attribuire la differenza alla lingua invece
    che al contenuto.

⚖️ Ogni fonte porta il suo VERO. Senza l'altra popolazione, un gate che
rifiutasse tutto sembrerebbe perfetto: i VERI misurano i falsi allarmi.

⛔ NESSUN dettaglio e' numerico, di proposito: L4.1 e' deterministico e sui
numeri ferma 8 lingue su 8 (misurato). Un dettaglio numerico misurerebbe L4.1,
non il giudice — e la domanda qui e' sul giudice.

COME SI LEGGE IL RISULTATO:
  IT alto e EN zero      -> e' LA LINGUA, e il claim centrale e' falso in
                            italiano su una forma comunissima di allucinazione;
  IT e EN entrambi alti  -> non e' la lingua, e' la CLASSE: il difetto vale
                            per ogni utente e la tabella per scritture non
                            c'entra;
  IT basso               -> il caso del 26/08 era una frase sfortunata, e la
                            riga «IT NO» nella tabella va corretta da me.

MISURATO 26/08 — NON E' LA LINGUA, E' LA CLASSE. E RITIRO LA MIA CONCLUSIONE
DI POCHE ORE PRIMA::

    falsita' AMMESSE   IT  8/10   EN  9/10
    VERI rifiutati     IT  1/10   EN  0/10

    tipi che passano in IT: mezzo, causa, autore, modalita, tempo,
                            destinatario, strumento, esito
    tipi che passano in EN: luogo, causa, autore, modalita, tempo,
                            destinatario, stato, strumento, esito

L'inglese va PEGGIO dell'italiano, non meglio. Nessuna delle tre letture
previste regge: e' la terza colonna della griglia, «e' LA CLASSE».

🪞 E IL BANCO DI POCHE ORE PRIMA AVEVA PESCATO L'UNICO CASO CHE SI FERMA.
`ws3-il-dettaglio-aggiunto-la-terza-classe.py` usava UN dettaglio per lingua —
«con corriere espresso», cioe' il tipo `mezzo` — e concludeva «EN ferma, IT
ammette». Qui `mezzo` e' l'unico tipo su dieci che EN ferma. ⇒ Quella
conclusione era un artefatto del campione, e con essa la riga «IT NO / EN si»
della tabella per scritture: su questa classe cadono ENTRAMBE.
🔑 Un caso per cella non e' una misura: e' un aneddoto con una tabella intorno.
Le prime due classi (negazione, entita' sostituita) sono state misurate con lo
STESSO disegno a un caso per lingua, e vanno rimisurate a batteria prima di
essere citate.

⚖️ IL CONTROLLO REGGE, ed e' cio' che rende leggibile il numero: i VERI sono
ammessi 19 volte su 20. Il gate non sta rifiutando tutto ne' ammettendo tutto —
discrimina, e su questa classe discrimina dalla parte sbagliata.

📌 IL MECCANISMO E' GIA' NOTO IN CASA, e questa e' la sua forma pura: il gate
distingue cio' che la fonte CONTRADDICE, non cio' che la fonte TACE. Un
dettaglio aggiunto non contraddice niente — la fonte semplicemente non ne
parla. `anti_confab_gate.py:2377-2392` lo diceva gia' («B e' la forma in cui un
LLM allucina davvero») e ne aveva chiusa la meta' numerica con L4.1.

Regime: porta pubblica `verimem remember --source`, store temporaneo, FUORI
pytest. Un solo store fra i casi, quindi L3 puo' farli vedere fra loro: i casi
che PASSANO vanno ri-verificati uno per processo con store vuoto.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_batteria_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (tipo, fonte_IT, vero_IT, falso_IT, fonte_EN, vero_EN, falso_EN)
CASI = [
    ("mezzo",
     "Registro spedizioni: l'ordine 77 e' partito il 3 marzo dal deposito di Rovigo.",
     "L'ordine 77 e' partito il 3 marzo.",
     "L'ordine 77 e' partito il 3 marzo con corriere espresso.",
     "Shipping log: order 77 was dispatched on 3 March from the Rovigo depot.",
     "Order 77 was dispatched on 3 March.",
     "Order 77 was dispatched on 3 March by express courier."),
    ("luogo",
     "Verbale: il consiglio ha approvato il bilancio il 12 aprile.",
     "Il consiglio ha approvato il bilancio il 12 aprile.",
     "Il consiglio ha approvato il bilancio il 12 aprile nella sala riunioni principale.",
     "Minutes: the board approved the budget on 12 April.",
     "The board approved the budget on 12 April.",
     "The board approved the budget on 12 April in the main meeting room."),
    ("causa",
     "Nota tecnica: il servizio di pagamento e' rimasto fermo per tutta la mattina di lunedi.",
     "Il servizio di pagamento e' rimasto fermo lunedi mattina.",
     "Il servizio di pagamento e' rimasto fermo lunedi mattina per un guasto ai server.",
     "Technical note: the payment service was down for the whole of Monday morning.",
     "The payment service was down on Monday morning.",
     "The payment service was down on Monday morning because of a server failure."),
    ("autore",
     "Comunicazione interna: la nuova procedura di rimborso entra in vigore da settembre.",
     "La nuova procedura di rimborso entra in vigore da settembre.",
     "La nuova procedura di rimborso, scritta dal direttore finanziario, entra in vigore da settembre.",
     "Internal memo: the new refund procedure takes effect from September.",
     "The new refund procedure takes effect from September.",
     "The new refund procedure, written by the finance director, takes effect from September."),
    ("modalita",
     "Verbale: l'assemblea ha respinto la proposta di fusione.",
     "L'assemblea ha respinto la proposta di fusione.",
     "L'assemblea ha respinto la proposta di fusione all'unanimita.",
     "Minutes: the assembly rejected the merger proposal.",
     "The assembly rejected the merger proposal.",
     "The assembly rejected the merger proposal unanimously."),
    ("tempo",
     "Rapporto cantiere: il ponte sul canale e' stato consegnato a novembre.",
     "Il ponte sul canale e' stato consegnato a novembre.",
     "Il ponte sul canale e' stato consegnato a novembre, in anticipo sui tempi.",
     "Site report: the canal bridge was delivered in November.",
     "The canal bridge was delivered in November.",
     "The canal bridge was delivered in November, ahead of schedule."),
    ("destinatario",
     "Registro magazzino: il lotto B12 e' uscito dal deposito il 9 giugno.",
     "Il lotto B12 e' uscito dal deposito il 9 giugno.",
     "Il lotto B12 e' uscito dal deposito il 9 giugno ed e' stato consegnato al cliente finale.",
     "Warehouse log: batch B12 left the depot on 9 June.",
     "Batch B12 left the depot on 9 June.",
     "Batch B12 left the depot on 9 June and was delivered to the end customer."),
    ("stato",
     "Verbale di consegna: i macchinari sono arrivati allo stabilimento il 4 maggio.",
     "I macchinari sono arrivati allo stabilimento il 4 maggio.",
     "I macchinari sono arrivati allo stabilimento il 4 maggio in perfette condizioni.",
     "Delivery note: the machinery arrived at the plant on 4 May.",
     "The machinery arrived at the plant on 4 May.",
     "The machinery arrived at the plant on 4 May in perfect condition."),
    ("strumento",
     "Protocollo: la richiesta di accesso agli atti e' stata protocollata il 21 gennaio.",
     "La richiesta di accesso agli atti e' stata protocollata il 21 gennaio.",
     "La richiesta di accesso agli atti e' stata protocollata il 21 gennaio tramite posta certificata.",
     "Registry: the freedom-of-information request was filed on 21 January.",
     "The freedom-of-information request was filed on 21 January.",
     "The freedom-of-information request was filed on 21 January by certified email."),
    ("esito",
     "Referto: il paziente e' stato dimesso dal reparto il 30 luglio.",
     "Il paziente e' stato dimesso dal reparto il 30 luglio.",
     "Il paziente e' stato dimesso dal reparto il 30 luglio con prognosi favorevole.",
     "Report: the patient was discharged from the ward on 30 July.",
     "The patient was discharged from the ward on 30 July.",
     "The patient was discharged from the ward on 30 July with a favourable prognosis."),
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
    print("%-14s %-3s %-7s %-12s %7s  %s"
          % ("tipo", "lg", "caso", "esito", "g", "layer"))
    passa = {"IT": [], "EN": []}
    veri_rifiutati = {"IT": [], "EN": []}
    for (tipo, s_it, v_it, f_it, s_en, v_en, f_en) in CASI:
        for lg, src, vero, falso in (("IT", s_it, v_it, f_it),
                                     ("EN", s_en, v_en, f_en)):
            e_v, g_v, l_v = esegui(vero, src)
            if e_v != "admitted":
                veri_rifiutati[lg].append(tipo)
            e_f, g_f, l_f = esegui(falso, src)
            if e_f != "quarantined":
                passa[lg].append(tipo)
            print("%-14s %-3s %-7s %-12s %7s  %-22s %s"
                  % (tipo, lg, "VERO", e_v,
                     ("%.1f" % g_v) if g_v is not None else "-", l_v,
                     "" if e_v == "admitted" else "<<< VERO RIFIUTATO"))
            print("%-14s %-3s %-7s %-12s %7s  %-22s %s"
                  % ("", lg, "falso", e_f,
                     ("%.1f" % g_f) if g_f is not None else "-", l_f,
                     "" if e_f == "quarantined" else "<<< FALSITA' AMMESSA"))
        print()
    n = len(CASI)
    print("=" * 84)
    print("  falsita' AMMESSE   IT %2d/%d   EN %2d/%d"
          % (len(passa["IT"]), n, len(passa["EN"]), n))
    print("  VERI rifiutati     IT %2d/%d   EN %2d/%d"
          % (len(veri_rifiutati["IT"]), n, len(veri_rifiutati["EN"]), n))
    print()
    print("  tipi che passano in IT: %s" % (", ".join(passa["IT"]) or "nessuno"))
    print("  tipi che passano in EN: %s" % (", ".join(passa["EN"]) or "nessuno"))
    print()
    print("  IT alto + EN zero -> e' LA LINGUA")
    print("  IT e EN alti      -> e' LA CLASSE, riguarda ogni utente")
    print("  IT basso          -> il caso del 26/08 era una frase sfortunata")


if __name__ == "__main__":
    main_banco()
