# -*- coding: utf-8 -*-
"""I VERI rifiutati si concentrano sulla forma «X was <participio>». E' la forma?

Aperto lasciato scritto e non classificato il 26/08. Nelle batterie di stasera i
falsi allarmi — cioe' CITAZIONI VERE della fonte rifiutate dal gate — non erano
distribuiti a caso::

    banco delle due classi thai   EN 2/10 veri rifiutati   forma «X was <part>»
    banco della vetrina           EN 1/10, ZH 1/10         forma «X was <part>»
    batteria negazione            EN 0/10, IT 0/10         forme miste
    batteria dettaglio            EN 0/10, IT 1/10         forme miste

Le due batterie dove la forma passiva era l'UNICA struttura sono le due dove i
veri rifiutati compaiono. Con tre casi non e' una tesi: e' il motivo di questo
banco.

⚖️ UN FALSO ALLARME NON E' MENO GRAVE DI UNA FALSITA' AMMESSA, e' solo meno
visibile: chi salva un fatto VERO e se lo vede quarantinare smette di fidarsi
del gate, e la memoria perde un fatto buono. Tutta la sera abbiamo misurato la
direzione «ammette il falso»; questa e' l'altra.

DISEGNO — A/B SULLA FORMA, non sul contenuto: dieci fatti, ciascuno scritto in
DUE modi che dicono la stessa identica cosa::

    PASSIVA   fonte «Note: the contract was signed on 4 May.»
              claim «The contract was signed on 4 May.»
    ATTIVA    fonte «Note: the board signed the contract on 4 May.»
              claim «The board signed the contract on 4 May.»

In entrambi i casi il claim e' la CITAZIONE della sua fonte, quindi VERO per
costruzione: ogni rifiuto e' un falso allarme. Se la passiva ne produce di piu'
dell'attiva a contenuto invariato, e' la forma.
🔑 IT/EN appaiati: se succede solo in EN e' la lingua, se succede in entrambe e'
la struttura.
⛔ Nessun caso numerico da verificare: i numeri sono identici fra fonte e claim.

MISURATO 26/08 — E' LA FORMA, MA IN ITALIANO. E l'aperto che avevo lasciato
scritto sbagliava LINGUA::

    VERI rifiutati  IT  PASSIVA  2/10      IT  attiva  0/10
    VERI rifiutati  EN  PASSIVA  0/10      EN  attiva  0/10
    chi li ha rifiutati:  L1.16  (2 su 2)

① CORRETTO IL 26/08 DOPO LA MISURA DI @ws1 — «E' LA FORMA» E' IMPRECISO.
I due casi caduti sono `contratto` («e' stato FIRMATO») e `bilancio` («e' stato
APPROVATO»); gli otto che passano hanno spedito, collaudato, respinta,
pubblicata, dimesso, consegnata, archiviata, ripristinato. `firmato` e
`approvato` sono i due verbi su cui stasera sono stati fatti commit di lista
(f48a45b9, 5c3d341b). ⇒ **A scegliere i casi e' la PAROLA, non la forma.**
🪞 E il dato era GIA' in questo output senza che lo leggessi — guardavo la
colonna dei RIFIUTATI e non i layer degli AMMESSI::

    contratto  IT attiva  admitted  layer = L1+L1.16    <- scatta anche in attiva
    bilancio   IT attiva  admitted  layer = L1+L1.16
    lotto      IT attiva  admitted  layer = -

⇒ MA LA FORMA DECIDE L'ESITO: su quelle stesse due parole, in PASSIVA L1.16
VETA (quarantined), in ATTIVA resta AVVISO (admitted). Stesso contenuto, stessa
parola, stesso claim che cita la sua fonte: cambia la voce del verbo e cambia
il verdetto.
🔑 La formulazione che regge a entrambe le misure — la mia alla porta e quella
di @ws1 su `_carve_out` come funzione pura: **la parola sceglie CHI guarda, la
forma decide SE veta.** Nessuna delle due da sola descrive il comportamento.
⚠️ Limite dichiarato: `git grep` su `"firmato"`/`"approvato"` nelle liste non li
trova — saranno derivati o generati. Qui si afferma il COMPORTAMENTO misurato,
non la loro presenza in una lista che non ho letto.
② MA E' ITALIANO, NON INGLESE. L'aperto che avevo lasciato scritto diceva «in
EN due VERI rifiutati sulla forma positiva»: qui l'inglese e' 0/10 in entrambe
le forme. I due casi EN che avevo visto venivano da due banchi diversi e non si
riproducono su questa popolazione. ⇒ Avevo la struttura giusta e la lingua
sbagliata, e con due casi sparsi non poteva essere altrimenti.
🔑 ③ IL COLPEVOLE E' `L1.16`, ed e' la QUARTA volta stasera che compare come
causa di un falso allarme: 3 volte nel banco dei nomi propri, 2 qui (su 2 su 2).
E' lo stesso layer, sulla stessa direzione dell'errore.
⇒ QUINTA misura indipendente che punta a L1, dopo l'A/B del 25/08 su
ENGRAM_L1_DOMAIN_ADVISORY (spegnendo L1: falsita' fermate invariate Delta 0/8,
VERI ammessi +2/16). Il quadro e' coerente attraverso cinque popolazioni
diverse: **L1 non contribuisce alla copertura e sottrae veri.**

⚠️ PERCHE' QUESTO NUMERO PESA PIU' DI 2/10: la forma passiva e' la struttura
DOMINANTE dei documenti che questo prodotto e' fatto per digerire — verbali
(«e' stato approvato»), referti («e' stato dimesso»), registri («e' stata
archiviata»), bolle («e' stata consegnata»). Un falso allarme su una forma rara
e' un fastidio; su quella piu' frequente del dominio e' un difetto d'uso.
⚖️ E un VERO rifiutato non e' meno grave di una falsita' ammessa: e' solo meno
visibile. Chi salva un fatto vero e se lo vede quarantinare smette di fidarsi
del gate, e la memoria perde un fatto buono.

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

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_passiva_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (nome, passiva_IT, attiva_IT, passiva_EN, attiva_EN)
#: ogni voce e' (fonte, claim) e il claim CITA la fonte -> sempre VERO
CASI = [
    ("contratto",
     ("Nota: il contratto e' stato firmato il 4 maggio.",
      "Il contratto e' stato firmato il 4 maggio."),
     ("Nota: il consiglio ha firmato il contratto il 4 maggio.",
      "Il consiglio ha firmato il contratto il 4 maggio."),
     ("Note: the contract was signed on 4 May.",
      "The contract was signed on 4 May."),
     ("Note: the board signed the contract on 4 May.",
      "The board signed the contract on 4 May.")),
    ("lotto",
     ("Registro: il lotto B12 e' stato spedito il 9 giugno.",
      "Il lotto B12 e' stato spedito il 9 giugno."),
     ("Registro: il deposito ha spedito il lotto B12 il 9 giugno.",
      "Il deposito ha spedito il lotto B12 il 9 giugno."),
     ("Log: batch B12 was shipped on 9 June.",
      "Batch B12 was shipped on 9 June."),
     ("Log: the depot shipped batch B12 on 9 June.",
      "The depot shipped batch B12 on 9 June.")),
    ("bilancio",
     ("Verbale: il bilancio e' stato approvato il 12 aprile.",
      "Il bilancio e' stato approvato il 12 aprile."),
     ("Verbale: l'assemblea ha approvato il bilancio il 12 aprile.",
      "L'assemblea ha approvato il bilancio il 12 aprile."),
     ("Minutes: the budget was approved on 12 April.",
      "The budget was approved on 12 April."),
     ("Minutes: the assembly approved the budget on 12 April.",
      "The assembly approved the budget on 12 April.")),
    ("impianto",
     ("Rapporto: l'impianto e' stato collaudato a settembre.",
      "L'impianto e' stato collaudato a settembre."),
     ("Rapporto: il tecnico ha collaudato l'impianto a settembre.",
      "Il tecnico ha collaudato l'impianto a settembre."),
     ("Report: the plant was inspected in September.",
      "The plant was inspected in September."),
     ("Report: the engineer inspected the plant in September.",
      "The engineer inspected the plant in September.")),
    ("richiesta",
     ("Nota: la richiesta e' stata respinta il 3 marzo.",
      "La richiesta e' stata respinta il 3 marzo."),
     ("Nota: la commissione ha respinto la richiesta il 3 marzo.",
      "La commissione ha respinto la richiesta il 3 marzo."),
     ("Note: the request was rejected on 3 March.",
      "The request was rejected on 3 March."),
     ("Note: the committee rejected the request on 3 March.",
      "The committee rejected the request on 3 March.")),
    ("relazione",
     ("Verbale: la relazione e' stata pubblicata a ottobre.",
      "La relazione e' stata pubblicata a ottobre."),
     ("Verbale: l'ufficio ha pubblicato la relazione a ottobre.",
      "L'ufficio ha pubblicato la relazione a ottobre."),
     ("Minutes: the report was published in October.",
      "The report was published in October."),
     ("Minutes: the office published the report in October.",
      "The office published the report in October.")),
    ("paziente",
     ("Referto: il paziente e' stato dimesso il 30 luglio.",
      "Il paziente e' stato dimesso il 30 luglio."),
     ("Referto: il reparto ha dimesso il paziente il 30 luglio.",
      "Il reparto ha dimesso il paziente il 30 luglio."),
     ("Report: the patient was discharged on 30 July.",
      "The patient was discharged on 30 July."),
     ("Report: the ward discharged the patient on 30 July.",
      "The ward discharged the patient on 30 July.")),
    ("merce",
     ("Bolla: la merce e' stata consegnata il 4 maggio.",
      "La merce e' stata consegnata il 4 maggio."),
     ("Bolla: il corriere ha consegnato la merce il 4 maggio.",
      "Il corriere ha consegnato la merce il 4 maggio."),
     ("Note: the goods were delivered on 4 May.",
      "The goods were delivered on 4 May."),
     ("Note: the courier delivered the goods on 4 May.",
      "The courier delivered the goods on 4 May.")),
    ("pratica",
     ("Protocollo: la pratica e' stata archiviata il 21 gennaio.",
      "La pratica e' stata archiviata il 21 gennaio."),
     ("Protocollo: l'ufficio ha archiviato la pratica il 21 gennaio.",
      "L'ufficio ha archiviato la pratica il 21 gennaio."),
     ("Registry: the file was archived on 21 January.",
      "The file was archived on 21 January."),
     ("Registry: the office archived the file on 21 January.",
      "The office archived the file on 21 January.")),
    ("servizio",
     ("Nota tecnica: il servizio e' stato ripristinato lunedi mattina.",
      "Il servizio e' stato ripristinato lunedi mattina."),
     ("Nota tecnica: il team ha ripristinato il servizio lunedi mattina.",
      "Il team ha ripristinato il servizio lunedi mattina."),
     ("Technical note: the service was restored on Monday morning.",
      "The service was restored on Monday morning."),
     ("Technical note: the team restored the service on Monday morning.",
      "The team restored the service on Monday morning.")),
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
    print("%-11s %-3s %-8s %-12s %7s  %s"
          % ("caso", "lg", "forma", "esito", "g", "layer"))
    rif = {}
    chi = {}
    for (nome, p_it, a_it, p_en, a_en) in CASI:
        for lg, passiva, attiva in (("IT", p_it, a_it), ("EN", p_en, a_en)):
            for forma, (src, claim) in (("PASSIVA", passiva), ("attiva", attiva)):
                e, g, layer = esegui(claim, src)
                k = (lg, forma)
                if e != "admitted":
                    rif[k] = rif.get(k, 0) + 1
                    chi[layer] = chi.get(layer, 0) + 1
                print("%-11s %-3s %-8s %-12s %7s  %-22s %s"
                      % (nome, lg, forma, e,
                         ("%.1f" % g) if g is not None else "-", layer,
                         "" if e == "admitted" else "<<< VERO RIFIUTATO"))
        print()
    n = len(CASI)
    print("=" * 78)
    for lg in ("IT", "EN"):
        for forma in ("PASSIVA", "attiva"):
            print("  VERI rifiutati  %s  %-8s %d/%d"
                  % (lg, forma, rif.get((lg, forma), 0), n))
    print()
    if chi:
        print("  CHI li ha rifiutati:")
        for lay, k in sorted(chi.items(), key=lambda x: -x[1]):
            print("    %-28s %d" % (lay, k))
    else:
        print("  Nessun falso allarme: l'aperto si chiude come non riproducibile.")
    print()
    print("  PASSIVA alta e attiva zero -> e' la FORMA, a contenuto invariato")
    print("  entrambe alte              -> non e' la forma, e' altro")
    print("  entrambe zero              -> i tre casi visti erano rumore")


if __name__ == "__main__":
    main_banco()
