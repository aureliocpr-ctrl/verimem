# -*- coding: utf-8 -*-
"""La classe NEGAZIONE l'avevo data per chiusa 0/8. Con UN caso per lingua.

Il 25/08 ho consegnato «F-NEG: 0/8 falsita' ammesse, in IT e in EN, in due
regimi» e ci ho costruito sopra una riga di tabella e mezzo voto sulla
direzione. Il 26/08 la batteria sui dettagli ha mostrato che il disegno a UN
caso per cella produce aneddoti: il tipo `mezzo` era l'unico su dieci che
l'inglese fermasse, e ci avevo letto «EN regge».

Questa batteria rifa' la negazione con lo stesso disegno che ha smascherato
l'altra: dieci casi, dieci fonti diverse, ogni caso appaiato IT/EN sulla stessa
fonte, VERO di controllo per ciascuno.

DUE VERSI, perche' non sono lo stesso fenomeno e il 25/08 ne avevo misurato uno
solo per lato:
  neg->pos   la fonte dice che NON e' avvenuto, il claim dice che e' avvenuto
  pos->neg   la fonte dice che E' avvenuto, il claim dice che NON e' avvenuto
Un gate che vedesse solo i negatori del CLAIM prenderebbe il secondo verso e
mancherebbe il primo (o viceversa), e con cinque casi per verso la differenza
si vede.

⚖️ Ogni fonte porta il suo VERO: i VERI misurano i falsi allarmi, senza i quali
un gate che rifiuta tutto sembra perfetto.
⛔ Nessuna falsita' e' numerica: L4.1 e' deterministico e sui numeri ferma 8
lingue su 8. Un caso numerico misurerebbe L4.1, non il giudice.

COSA DECIDE:
  ammesse ~0/10   -> la riga «negazione chiusa» del 25/08 REGGE, ed era vera
                     anche se misurata male;
  ammesse alte    -> ho consegnato una tabella sbagliata per due giorni e va
                     detto subito, prima che qualcuno la usi per decidere.

MISURATO 26/08 — LA RIGA REGGE, E IL CONTRASTO E' LA SCOPERTA::

    falsita' ammesse  IT  neg->pos  0/5     EN  neg->pos  0/5
    falsita' ammesse  IT  pos->neg  0/5     EN  pos->neg  0/5
    TOTALE            IT  0/10              EN  0/10
    VERI rifiutati    IT  0/10              EN  0/10

Zero errori su 40 chiamate, due lingue, DUE versi. Sui falsi scattano
`L4-grounding` e `L4-negazione` con g fra 1.4 e 1.6. La riga «negazione chiusa»
del 25/08 era vera anche se misurata con un caso solo: qui non ho una tabella
da ritirare, e lo scrivo perche' avevo dichiarato che l'avrei fatto se fosse
caduta.

🔑 MA IL VALORE NON E' CHE LA MIA RIGA SOPRAVVIVA — E' L'A/B CHE NE ESCE.
Le due batterie hanno lo STESSO disegno (10 casi, IT/EN appaiati sulla stessa
fonte, VERI di controllo, nessun caso numerico, stessa porta, stesso regime) e
condividono in parte le fonti (lotto B12, Rovigo, servizio di pagamento,
accesso agli atti). Differiscono per UNA proprieta' sola::

    classe                              IT      EN
    negazione   (la fonte CONTRADDICE)  0/10    0/10
    dettaglio   (la fonte TACE)         8/10    9/10

⇒ Il gate distingue cio' che la fonte CONTRADDICE, non cio' che la fonte TACE.
Era un'ipotesi mia dal 25/08, nata dal 52,1% dell'osservatore; ora e' misurata
con popolazioni appaiate, e la distanza fra le due colonne e' 0% contro 85%.

⚖️ E i due estremi si tengono a vicenda: sulla negazione i VERI sono ammessi
20 volte su 20 e le falsita' fermate 20 su 20 — il gate non e' ne' cieco ne'
paranoico. Non e' un prodotto rotto: e' un prodotto che fa UNA cosa, la fa
benissimo, e non ne fa un'altra che il claim centrale promette.

📌 CONSEGUENZA PER CIO' CHE SI PUO' DICHIARARE: «un fatto che la fonte
CONTRADDICE non ti torna come verita'» e' vero, misurato, e forte. «Un fatto
che la fonte non SOSTIENE non ti torna come verita'» e' falso 8-9 volte su 10.
Sono due frasi diverse e oggi il prodotto ne mantiene una.

Regime: porta pubblica `verimem remember --source`, store temporaneo, FUORI
pytest. Un solo store fra i casi: i casi che PASSANO vanno ri-verificati uno
per processo con store vuoto.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_negbatt_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (verso, fonte_IT, vero_IT, falso_IT, fonte_EN, vero_EN, falso_EN)
CASI = [
    ("neg->pos",
     "Verbale: la richiesta di rimborso del reparto vendite non e' stata approvata.",
     "La richiesta di rimborso del reparto vendite non e' stata approvata.",
     "La richiesta di rimborso del reparto vendite e' stata approvata.",
     "Minutes: the sales department refund request was not approved.",
     "The sales department refund request was not approved.",
     "The sales department refund request was approved."),
    ("neg->pos",
     "Nota: il contratto di affitto del magazzino nord non e' stato rinnovato.",
     "Il contratto di affitto del magazzino nord non e' stato rinnovato.",
     "Il contratto di affitto del magazzino nord e' stato rinnovato.",
     "Note: the lease for the north warehouse was not renewed.",
     "The lease for the north warehouse was not renewed.",
     "The lease for the north warehouse was renewed."),
    ("neg->pos",
     "Referto: il paziente non ha risposto alla terapia antibiotica.",
     "Il paziente non ha risposto alla terapia antibiotica.",
     "Il paziente ha risposto alla terapia antibiotica.",
     "Report: the patient did not respond to the antibiotic therapy.",
     "The patient did not respond to the antibiotic therapy.",
     "The patient responded to the antibiotic therapy."),
    ("neg->pos",
     "Comunicazione: il fornitore Baldini non ha consegnato il lotto entro il termine.",
     "Il fornitore Baldini non ha consegnato il lotto entro il termine.",
     "Il fornitore Baldini ha consegnato il lotto entro il termine.",
     "Notice: supplier Baldini did not deliver the batch by the deadline.",
     "Supplier Baldini did not deliver the batch by the deadline.",
     "Supplier Baldini delivered the batch by the deadline."),
    ("neg->pos",
     "Rapporto: la migrazione a Postgres non e' stata completata nel trimestre.",
     "La migrazione a Postgres non e' stata completata nel trimestre.",
     "La migrazione a Postgres e' stata completata nel trimestre.",
     "Report: the migration to Postgres was not completed in the quarter.",
     "The migration to Postgres was not completed in the quarter.",
     "The migration to Postgres was completed in the quarter."),
    ("pos->neg",
     "Verbale: il consiglio ha approvato il bilancio annuale.",
     "Il consiglio ha approvato il bilancio annuale.",
     "Il consiglio non ha approvato il bilancio annuale.",
     "Minutes: the board approved the annual budget.",
     "The board approved the annual budget.",
     "The board did not approve the annual budget."),
    ("pos->neg",
     "Registro: il lotto B12 e' uscito dal deposito il 9 giugno.",
     "Il lotto B12 e' uscito dal deposito il 9 giugno.",
     "Il lotto B12 non e' uscito dal deposito il 9 giugno.",
     "Log: batch B12 left the depot on 9 June.",
     "Batch B12 left the depot on 9 June.",
     "Batch B12 did not leave the depot on 9 June."),
    ("pos->neg",
     "Atto: il magazzino di Rovigo e' stato venduto al signor Anselmi.",
     "Il magazzino di Rovigo e' stato venduto al signor Anselmi.",
     "Il magazzino di Rovigo non e' stato venduto al signor Anselmi.",
     "Deed: the Rovigo warehouse was sold to Mr Anselmi.",
     "The Rovigo warehouse was sold to Mr Anselmi.",
     "The Rovigo warehouse was not sold to Mr Anselmi."),
    ("pos->neg",
     "Nota tecnica: il servizio di pagamento e' tornato operativo lunedi mattina.",
     "Il servizio di pagamento e' tornato operativo lunedi mattina.",
     "Il servizio di pagamento non e' tornato operativo lunedi mattina.",
     "Technical note: the payment service came back online on Monday morning.",
     "The payment service came back online on Monday morning.",
     "The payment service did not come back online on Monday morning."),
    ("pos->neg",
     "Protocollo: la richiesta di accesso agli atti e' stata accolta.",
     "La richiesta di accesso agli atti e' stata accolta.",
     "La richiesta di accesso agli atti non e' stata accolta.",
     "Registry: the freedom-of-information request was granted.",
     "The freedom-of-information request was granted.",
     "The freedom-of-information request was not granted."),
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
    print("%-10s %-3s %-6s %-12s %7s  %s"
          % ("verso", "lg", "caso", "esito", "g", "layer"))
    amm = {("IT", "neg->pos"): 0, ("IT", "pos->neg"): 0,
           ("EN", "neg->pos"): 0, ("EN", "pos->neg"): 0}
    tot = dict.fromkeys(amm, 0)
    veri_rif = {"IT": 0, "EN": 0}
    for (verso, s_it, v_it, f_it, s_en, v_en, f_en) in CASI:
        for lg, src, vero, falso in (("IT", s_it, v_it, f_it),
                                     ("EN", s_en, v_en, f_en)):
            e_v, g_v, l_v = esegui(vero, src)
            if e_v != "admitted":
                veri_rif[lg] += 1
            e_f, g_f, l_f = esegui(falso, src)
            tot[(lg, verso)] += 1
            if e_f != "quarantined":
                amm[(lg, verso)] += 1
            print("%-10s %-3s %-6s %-12s %7s  %-22s %s"
                  % (verso, lg, "VERO", e_v,
                     ("%.1f" % g_v) if g_v is not None else "-", l_v,
                     "" if e_v == "admitted" else "<<< VERO RIFIUTATO"))
            print("%-10s %-3s %-6s %-12s %7s  %-22s %s"
                  % ("", lg, "falso", e_f,
                     ("%.1f" % g_f) if g_f is not None else "-", l_f,
                     "" if e_f == "quarantined" else "<<< FALSITA' AMMESSA"))
        print()
    print("=" * 84)
    for lg in ("IT", "EN"):
        for verso in ("neg->pos", "pos->neg"):
            print("  falsita' ammesse  %s  %-9s %d/%d"
                  % (lg, verso, amm[(lg, verso)], tot[(lg, verso)]))
    it = amm[("IT", "neg->pos")] + amm[("IT", "pos->neg")]
    en = amm[("EN", "neg->pos")] + amm[("EN", "pos->neg")]
    print()
    print("  TOTALE falsita' ammesse   IT %d/10   EN %d/10" % (it, en))
    print("  VERI rifiutati            IT %d/10   EN %d/10"
          % (veri_rif["IT"], veri_rif["EN"]))
    print()
    print("  ~0/10  -> la riga «negazione chiusa» del 25/08 REGGE")
    print("  alte   -> ho consegnato una tabella sbagliata per due giorni")


if __name__ == "__main__":
    main_banco()
