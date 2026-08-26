# -*- coding: utf-8 -*-
"""Perche' 3 contraddizioni implicite su 10 passano e 7 no? Ipotesi: l'ANTONIMIA.

Misurato il 26/08 (`ws3-la-contraddizione-implicita.py`): in italiano le
contraddizioni implicite passano 3/10, le esplicite 0/10. Guardando QUALI::

    PASSANO   deceduto -> dimesso · fallita -> chiuso in utile · vuoto -> stoccati
    SI FERMANO  respinto -> accolto · sospeso -> operativo · scaduto -> in vigore
                annullata -> hanno partecipato · demolito -> ristrutturato
                difforme -> conforme · dimissioni -> confermato

I sette che si fermano hanno una coppia di ANTONIMI LESSICALI — parole che in
un vocabolario stanno l'una sotto l'altra come opposti (respinto/accolto,
sospeso/operativo, conforme/difforme). I tre che passano no: «deceduto» e
«dimesso» non sono opposti, sono due esiti che il MONDO rende incompatibili.

⇒ IPOTESI FALSIFICABILE: il gate prende la contraddizione implicita quando il
conflitto e' iscritto nel LESSICO, e la manca quando serve sapere com'e' fatto
il mondo. Se regge, la cura non e' lessicale per costruzione: nessuna lista di
antonimi puo' contenere «un morto non viene dimesso».

DISEGNO — dieci coppie per gruppo, stessa struttura, stessa lingua, stesso
tipo di fonte::

    A  ANTONIMI      il claim usa l'opposto lessicale del termine della fonte
    B  NON antonimi  il claim usa un termine che il mondo rende incompatibile
                     ma che nessun dizionario elenca come contrario

⚖️ Ogni caso porta il suo VERO. ⛔ Nessun numero cambia fra fonte e claim.
🔑 Il controllo che rende leggibile il confronto: i due gruppi hanno la STESSA
forma sintattica e la stessa lunghezza tipica. Se il gruppo A si ferma e il B
passa, la differenza e' l'antonimia e non la struttura.
⚠️ Chi classifica le coppie sono io, e «antonimo» non ha un confine netto: il
limite e' dichiarato, non nascosto. Ho messo in A solo coppie che un dizionario
elenca come contrari diretti.

COSA DECIDE:
  A basso e B alto   -> l'ipotesi regge: serve conoscenza del mondo, e nessuna
                        lista di parole puo' bastare;
  A e B simili       -> l'antonimia non c'entra, e i 3/10 di prima erano altro.

MISURATO 26/08 — L'IPOTESI REGGE, MA IL LAYER DICE QUALCOSA DI MEGLIO::

    A antonimi      falsita' ammesse  1/10     VERI rifiutati 2
    B non-antonimi  falsita' ammesse  5/10     VERI rifiutati 0

① CINQUE VOLTE PIU' ERRORI quando il conflitto richiede conoscenza del mondo
invece che del vocabolario. L'ipotesi regge.
🔑 ② MA IL GATE NON E' CIECO AL CONFLITTO: LO CLASSIFICA COME EVOLUZIONE.
Guardando CHI ammette, invece del solo numero::

    deceduto     admitted   layer = L3-supersession
    vuoto        admitted   layer = L3-supersession
    ghiacciato   admitted   layer = L3-supersession
    prosciugato  admitted   layer = L3-coexistence
    fallita      admitted   layer = L1+L1.13+L3-supersession+L4-relazione
    valido (A)   admitted   layer = L3-supersession

Tutti e sei i casi ammessi passano da `L3-supersession` o `L3-coexistence`. Il
gate VEDE due affermazioni sullo stesso soggetto e le instrada come
AGGIORNAMENTO — «prima era X, ora e' Y» — invece che come conflitto. Non e' un
giudizio sbagliato: e' un ROUTING sbagliato, e i casi che si fermano non ci
arrivano nemmeno (`L4-grounding`, g fra 0.3 e 3.0).

⇒ ③ E QUESTO LO RENDE CURABILE, al contrario di quanto avevo scritto ieri
(«serve un giudizio che non esiste»). Nei sei casi ammessi la fonte e il claim
portano **lo stesso istante**::

    «il paziente e' deceduto IL 30 LUGLIO»  vs  «e' stato dimesso IL 30 LUGLIO»
    «il magazzino risulta vuoto»            vs  «sono stoccati i lotti di aprile»
    «il bacino si e' prosciugato AD AGOSTO» vs  «AD AGOSTO ha alimentato la centrale»

Una supersessione temporale richiede che i due fatti stiano in istanti
DIVERSI. Con la stessa data, «prima X poi Y» e' impossibile per costruzione —
e questa e' una verifica deterministica, non conoscenza del mondo.
📌 LA CURA CHE PROPONGO E NON SCRIVO STASERA (e' di chi possiede L3): prima di
instradare una coppia come supersessione, chiedere se i due fatti portino un
istante incompatibile con la successione. Se la data e' la stessa, la coppia
non e' un aggiornamento: e' un conflitto, e va al giudice come tale.
⚠️ NON dico che copra tutti e sei — «il magazzino e' vuoto» non porta una data.
Dico che e' un criterio deterministico applicabile ad almeno tre dei sei, ed e'
molto piu' di «serve un giudizio che non esiste».

⚠️ E DUE VERI RIFIUTATI NEL GRUPPO A: il prezzo lo paga anche l'altra
popolazione. Chi tocca L3 misuri entrambe le direzioni.

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

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_anton_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (gruppo, nome, fonte, vero, falso)
CASI = [
    # ── A: ANTONIMI LESSICALI ────────────────────────────────────────────
    ("A antonimi", "respinto",
     "Protocollo: il ricorso e' stato respinto.",
     "Il ricorso e' stato respinto.", "Il ricorso e' stato accolto."),
    ("A antonimi", "sospeso",
     "Nota: il servizio di pagamento e' sospeso.",
     "Il servizio di pagamento e' sospeso.", "Il servizio di pagamento e' attivo."),
    ("A antonimi", "aperto",
     "Avviso: lo sportello di via Verdi e' chiuso al pubblico.",
     "Lo sportello di via Verdi e' chiuso al pubblico.",
     "Lo sportello di via Verdi e' aperto al pubblico."),
    ("A antonimi", "pieno",
     "Inventario: il serbatoio della sede nord e' vuoto.",
     "Il serbatoio della sede nord e' vuoto.",
     "Il serbatoio della sede nord e' pieno."),
    ("A antonimi", "assente",
     "Registro: il tecnico Baldini era presente al collaudo.",
     "Il tecnico Baldini era presente al collaudo.",
     "Il tecnico Baldini era assente al collaudo."),
    ("A antonimi", "valido",
     "Verifica: il certificato del lotto B12 e' scaduto.",
     "Il certificato del lotto B12 e' scaduto.",
     "Il certificato del lotto B12 e' valido."),
    ("A antonimi", "obbligatorio",
     "Circolare: la formazione sulla sicurezza e' facoltativa.",
     "La formazione sulla sicurezza e' facoltativa.",
     "La formazione sulla sicurezza e' obbligatoria."),
    ("A antonimi", "interno",
     "Nota: la relazione e' stata redatta da un consulente esterno.",
     "La relazione e' stata redatta da un consulente esterno.",
     "La relazione e' stata redatta da un consulente interno."),
    ("A antonimi", "gratuito",
     "Listino: il servizio di assistenza e' a pagamento.",
     "Il servizio di assistenza e' a pagamento.",
     "Il servizio di assistenza e' gratuito."),
    ("A antonimi", "provvisorio",
     "Atto: la nomina del direttore e' definitiva.",
     "La nomina del direttore e' definitiva.",
     "La nomina del direttore e' provvisoria."),
    # ── B: NON antonimi — incompatibili per come e' fatto il mondo ────────
    ("B non-anton", "deceduto",
     "Referto: il paziente e' deceduto il 30 luglio in terapia intensiva.",
     "Il paziente e' deceduto il 30 luglio.",
     "Il paziente e' stato dimesso il 30 luglio."),
    ("B non-anton", "fallita",
     "Sentenza: la societa' Ferraris e' stata dichiarata fallita a giugno.",
     "La societa' Ferraris e' stata dichiarata fallita a giugno.",
     "La societa' Ferraris ha chiuso il bilancio in utile a giugno."),
    ("B non-anton", "vuoto",
     "Inventario: il magazzino nord risulta completamente vuoto.",
     "Il magazzino nord risulta completamente vuoto.",
     "Nel magazzino nord sono stoccati i lotti di aprile."),
    ("B non-anton", "incendio",
     "Rapporto: il capannone di Rovigo e' stato distrutto da un incendio a marzo.",
     "Il capannone di Rovigo e' stato distrutto da un incendio a marzo.",
     "Il capannone di Rovigo ha ospitato la fiera campionaria ad aprile."),
    ("B non-anton", "arrestato",
     "Cronaca: il fornitore Corsini e' stato arrestato il 9 giugno.",
     "Il fornitore Corsini e' stato arrestato il 9 giugno.",
     "Il fornitore Corsini ha presieduto l'assemblea del 10 giugno."),
    ("B non-anton", "ghiacciato",
     "Bollettino: il valico e' rimasto sepolto dalla neve per tutta la settimana.",
     "Il valico e' rimasto sepolto dalla neve per tutta la settimana.",
     "I camion hanno attraversato il valico ogni giorno della settimana."),
    ("B non-anton", "prosciugato",
     "Rilievo: il bacino di monte si e' prosciugato ad agosto.",
     "Il bacino di monte si e' prosciugato ad agosto.",
     "Ad agosto il bacino di monte ha alimentato la centrale."),
    ("B non-anton", "sequestrato",
     "Verbale: il macchinario e' stato sequestrato dall'autorita' a maggio.",
     "Il macchinario e' stato sequestrato dall'autorita' a maggio.",
     "Il macchinario ha lavorato su tre turni a maggio."),
    ("B non-anton", "neonato",
     "Anagrafe: il figlio dei Baldini e' nato il 3 marzo.",
     "Il figlio dei Baldini e' nato il 3 marzo.",
     "Il figlio dei Baldini ha conseguito la laurea il 4 marzo."),
    ("B non-anton", "demolito",
     "Atto: il ponte sul canale e' stato demolito nel 2019.",
     "Il ponte sul canale e' stato demolito nel 2019.",
     "Nel 2024 il ponte sul canale ha retto il traffico pesante."),
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
    print("%-13s %-13s %-12s %7s  %s"
          % ("gruppo", "caso", "esito", "g", "layer"))
    amm = {}
    tot = {}
    rif = {}
    for gruppo, nome, src, vero, falso in CASI:
        tot[gruppo] = tot.get(gruppo, 0) + 1
        e_v, _, _ = esegui(vero, src)
        if e_v != "admitted":
            rif[gruppo] = rif.get(gruppo, 0) + 1
        e_f, g_f, l_f = esegui(falso, src)
        if e_f != "quarantined":
            amm[gruppo] = amm.get(gruppo, 0) + 1
        print("%-13s %-13s %-12s %7s  %-22s %s"
              % (gruppo, nome, e_f,
                 ("%.1f" % g_f) if g_f is not None else "-", l_f,
                 "<<< AMMESSA" if e_f != "quarantined" else ""))
    print()
    print("=" * 72)
    for gruppo in ("A antonimi", "B non-anton"):
        print("  %-13s falsita' ammesse %2d/%-3d   VERI rifiutati %d"
              % (gruppo, amm.get(gruppo, 0), tot.get(gruppo, 0),
                 rif.get(gruppo, 0)))
    print()
    print("  A basso e B alto -> il conflitto iscritto nel LESSICO viene preso,")
    print("  quello che richiede conoscenza del MONDO no. Nessuna lista di")
    print("  antonimi puo' contenere «un morto non viene dimesso».")


if __name__ == "__main__":
    main_banco()
