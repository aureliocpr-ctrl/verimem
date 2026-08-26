# -*- coding: utf-8 -*-
"""L'entita' sostituita: l'ultima delle tre classi misurate a un caso per cella.

Il 25/08 avevo consegnato «falso ATTRIBUTO passa in AR, TH, HI · falso NOME
passa in TH, HI», con UN caso per lingua e per forma. Il 26/08 la batteria sui
dettagli ha mostrato che quel disegno produce aneddoti: il tipo `mezzo` era
l'unico su dieci che l'inglese fermasse, e ci avevo letto «EN regge».
La negazione, rifatta a batteria, ha invece confermato la sua riga (0/10 e
0/10). Questa e' la terza e ultima da verificare.

DUE FORME, cinque casi ciascuna, perche' il gate le tratta diversamente per
costruzione — il ramo `_proper` di `_entita_diverse` (59fb0862) esiste apposta
per i nomi propri::

    ATTRIBUTO      l'entita' e' distinta da un aggettivo o da un complemento
                   (magazzino NORD -> magazzino SUD, reparto VENDITE ->
                   reparto ACQUISTI)
    NOME PROPRIO   l'entita' e' distinta da un nome
                   (Anselmi -> Boveri, Rovigo -> Treviso)

In entrambe la falsita' e' della stessa natura: il fatto detto dalla fonte
viene attribuito a UN'ALTRA entita', lasciando tutto il resto identico —
numeri compresi. E' cio' che un moat deve prendere sempre.

⚖️ Ogni caso porta il suo VERO: i VERI misurano i falsi allarmi.
⛔ Nessuna falsita' e' numerica: i numeri restano IDENTICI fra fonte e claim,
   proprio perche' L4.1 non deve poter intervenire. Se un caso venisse fermato
   da L4.1 il banco misurerebbe il layer deterministico, non il giudice.
🔑 IT/EN appaiati sulla stessa fonte: e' l'unico modo di attribuire una
   differenza alla lingua invece che al contenuto.

COSA DECIDE:
  ammesse ~0/10 in IT e EN  -> la riga del 25/08 reggeva per EN/IT, e restava
                               aperta solo la questione delle scritture;
  ammesse alte              -> anche questa terza riga era un aneddoto, e le
                               tre classi vanno tutte ridichiarate.

MISURATO 26/08 — LA RIGA REGGE PER IT/EN, E DENTRO C'E' UNA STRUTTURA::

    falsita' ammesse  IT  attributo  0/5      EN  attributo  0/5
    falsita' ammesse  IT  nome       1/5      EN  nome       2/5
    TOTALE            IT  1/10                EN  2/10
    VERI rifiutati    IT  1/10                EN  1/10

① La riga del 25/08 reggeva per IT/EN: 1 e 2 su 10, non 8 e 9. Su questa classe
non ho una tabella da ritirare.
② LE DUE FORME NON SONO EQUIVALENTI, e la differenza e' dove il codice dice che
sarebbe: l'ATTRIBUTO e' perfetto (0/5 e 0/5), il NOME PROPRIO cede (1/5 e 2/5).
Il ramo `_proper` di `_entita_diverse` (59fb0862) tratta i nomi propri a parte,
ed e' li' che il gate perde. Chi lo tocca ha ora cinque casi per lingua invece
di uno.
③ DUE VERI RIFIUTATI, uno per lingua, entrambi da `L1.16` — il lessicale che
scarta una citazione VERA su un nome proprio. E' la stessa direzione misurata
il 25/08 con l'A/B su ENGRAM_L1_DOMAIN_ADVISORY: spegnendo L1 le falsita'
fermate non cambiavano (Delta 0/8) e i VERI ammessi salivano (+2/16).

═══ IL QUADRO DELLE TRE CLASSI, TUTTE A BATTERIA ═══

    classe               natura della falsita'      IT      EN
    negazione            la fonte CONTRADDICE      0/10    0/10
    entita' sostituita   la fonte CONTRADDICE      1/10    2/10
    dettaglio aggiunto   la fonte TACE             8/10    9/10

Tre classi, due gruppi, separazione netta. Le prime due dicono qualcosa che la
fonte NEGA; la terza dice qualcosa di cui la fonte non parla. ⇒ La tesi «il
gate distingue cio' che la fonte CONTRADDICE, non cio' che TACE» non regge piu'
su un confronto a due: regge su tre classi, con la classe intermedia che si
schiera dalla parte prevista.

⛔ COSA QUESTO BANCO NON DICE: e' IT/EN soltanto. La riga del 25/08 sulle
scritture non latine (AR, TH, HI) resta misurata a UN caso per cella e NON
citabile. Idem il thai a 99.87.

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

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_entbatt_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (forma, fonte_IT, vero_IT, falso_IT, fonte_EN, vero_EN, falso_EN)
CASI = [
    ("attributo",
     "Rapporto: il magazzino nord misura 1800 metri quadrati.",
     "Il magazzino nord misura 1800 metri quadrati.",
     "Il magazzino sud misura 1800 metri quadrati.",
     "Report: the north warehouse measures 1800 square metres.",
     "The north warehouse measures 1800 square metres.",
     "The south warehouse measures 1800 square metres."),
    ("attributo",
     "Verbale: la richiesta del reparto vendite e' stata respinta.",
     "La richiesta del reparto vendite e' stata respinta.",
     "La richiesta del reparto acquisti e' stata respinta.",
     "Minutes: the sales department request was rejected.",
     "The sales department request was rejected.",
     "The purchasing department request was rejected."),
    ("attributo",
     "Nota: il turno di notte ha completato la manutenzione della linea 3.",
     "Il turno di notte ha completato la manutenzione della linea 3.",
     "Il turno di giorno ha completato la manutenzione della linea 3.",
     "Note: the night shift completed the maintenance on line 3.",
     "The night shift completed the maintenance on line 3.",
     "The day shift completed the maintenance on line 3."),
    ("attributo",
     "Referto: il paziente del reparto cardiologia e' stato dimesso il 30 luglio.",
     "Il paziente del reparto cardiologia e' stato dimesso il 30 luglio.",
     "Il paziente del reparto oncologia e' stato dimesso il 30 luglio.",
     "Report: the cardiology ward patient was discharged on 30 July.",
     "The cardiology ward patient was discharged on 30 July.",
     "The oncology ward patient was discharged on 30 July."),
    ("attributo",
     "Registro: il contratto quadriennale e' scaduto a marzo.",
     "Il contratto quadriennale e' scaduto a marzo.",
     "Il contratto triennale e' scaduto a marzo.",
     "Registry: the four-year contract expired in March.",
     "The four-year contract expired in March.",
     "The three-year contract expired in March."),
    ("nome",
     "Atto: il magazzino di Rovigo e' stato venduto al signor Anselmi.",
     "Il magazzino di Rovigo e' stato venduto al signor Anselmi.",
     "Il magazzino di Rovigo e' stato venduto al signor Boveri.",
     "Deed: the Rovigo warehouse was sold to Mr Anselmi.",
     "The Rovigo warehouse was sold to Mr Anselmi.",
     "The Rovigo warehouse was sold to Mr Baxter."),
    ("nome",
     "Comunicazione: il fornitore Baldini ha consegnato il lotto B12 il 9 giugno.",
     "Il fornitore Baldini ha consegnato il lotto B12 il 9 giugno.",
     "Il fornitore Corsini ha consegnato il lotto B12 il 9 giugno.",
     "Notice: supplier Baldini delivered batch B12 on 9 June.",
     "Supplier Baldini delivered batch B12 on 9 June.",
     "Supplier Corsini delivered batch B12 on 9 June."),
    ("nome",
     "Verbale: la relazione e' stata presentata dalla dottoressa Merli.",
     "La relazione e' stata presentata dalla dottoressa Merli.",
     "La relazione e' stata presentata dalla dottoressa Fabbri.",
     "Minutes: the report was presented by Dr Merli.",
     "The report was presented by Dr Merli.",
     "The report was presented by Dr Fabbri."),
    ("nome",
     "Rapporto: il cantiere di Mestre e' stato consegnato a novembre.",
     "Il cantiere di Mestre e' stato consegnato a novembre.",
     "Il cantiere di Treviso e' stato consegnato a novembre.",
     "Report: the Mestre site was handed over in November.",
     "The Mestre site was handed over in November.",
     "The Treviso site was handed over in November."),
    ("nome",
     "Nota: la migrazione a Postgres e' stata approvata il 9 giugno.",
     "La migrazione a Postgres e' stata approvata il 9 giugno.",
     "La migrazione a MySQL e' stata approvata il 9 giugno.",
     "Note: the migration to Postgres was approved on 9 June.",
     "The migration to Postgres was approved on 9 June.",
     "The migration to MySQL was approved on 9 June."),
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
          % ("forma", "lg", "caso", "esito", "g", "layer"))
    amm = {("IT", "attributo"): 0, ("IT", "nome"): 0,
           ("EN", "attributo"): 0, ("EN", "nome"): 0}
    tot = dict.fromkeys(amm, 0)
    veri_rif = {"IT": 0, "EN": 0}
    for (forma, s_it, v_it, f_it, s_en, v_en, f_en) in CASI:
        for lg, src, vero, falso in (("IT", s_it, v_it, f_it),
                                     ("EN", s_en, v_en, f_en)):
            e_v, g_v, l_v = esegui(vero, src)
            if e_v != "admitted":
                veri_rif[lg] += 1
            e_f, g_f, l_f = esegui(falso, src)
            tot[(lg, forma)] += 1
            if e_f != "quarantined":
                amm[(lg, forma)] += 1
            print("%-10s %-3s %-6s %-12s %7s  %-22s %s"
                  % (forma, lg, "VERO", e_v,
                     ("%.1f" % g_v) if g_v is not None else "-", l_v,
                     "" if e_v == "admitted" else "<<< VERO RIFIUTATO"))
            print("%-10s %-3s %-6s %-12s %7s  %-22s %s"
                  % ("", lg, "falso", e_f,
                     ("%.1f" % g_f) if g_f is not None else "-", l_f,
                     "" if e_f == "quarantined" else "<<< FALSITA' AMMESSA"))
        print()
    print("=" * 84)
    for lg in ("IT", "EN"):
        for forma in ("attributo", "nome"):
            print("  falsita' ammesse  %s  %-10s %d/%d"
                  % (lg, forma, amm[(lg, forma)], tot[(lg, forma)]))
    it = amm[("IT", "attributo")] + amm[("IT", "nome")]
    en = amm[("EN", "attributo")] + amm[("EN", "nome")]
    print()
    print("  TOTALE falsita' ammesse   IT %d/10   EN %d/10" % (it, en))
    print("  VERI rifiutati            IT %d/10   EN %d/10"
          % (veri_rif["IT"], veri_rif["EN"]))
    print()
    print("  ~0/10 -> la riga del 25/08 reggeva per IT/EN")
    print("  alte  -> anche la terza riga era un aneddoto")


if __name__ == "__main__":
    main_banco()
