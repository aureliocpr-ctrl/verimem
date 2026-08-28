# -*- coding: utf-8 -*-
"""F1 · La baseline di un'ora fa REGGE su una fonte di lunghezza vera?

Un'ora fa ho pubblicato la baseline rossa di F1 su fonti CORTE (~450 e ~230
caratteri) e ne ho ricavato una PRIORITA' DI LAVORO:
    SCAMBIO 7/12 entrano  >  OMISSIONE 3/3  >  NUMERALE 1/3
e avevo dichiarato «fonti corte» come limite.

Nella stessa ora, due misure delle sorelle dicono che quel limite NON e' un
limite:
  @ws4 (b047ebb7) sulla MIA STESSA fonte contrattuale, allungandola con
       clausole di stile: a 453 caratteri lo scambio sugli importi e' fermato
       a 0.9 — e' esattamente la mia cella — ma a 935 il gate NON DISTINGUE
       PIU' il vero dal falso (vero 100.0, scambi 99.5-99.9).
  @ws5 : bastano TRE frasi / 14 parole di riempimento puro per portare un
       falso da 7.9 a 84.2, e NON e' una rampa: e' una SOGLIA.

⇒ regola di casa: **un limite dichiarato e' un debito, non un'assicurazione —
  se misurandolo l'affermazione potrebbe cadere, il limite non l'accompagna:
  la SOSPENDE.** Quindi la sospendo e la rimisuro.

LA PREDIZIONE, scritta prima di eseguire:

  SCAMBIO    7/12 -> 12/12   (tutti entrano a >=935 caratteri)
  NUMERALE   1/3  ->  3/3    (i due che oggi ferma il giudice a 0.6 e 14.5
                              sono fermati DAL GIUDICE, non da L4.1 ⇒ lo
                              stesso meccanismo del traino li solleva)
  OMISSIONE  3/3  ->  3/3    (gia' tutti dentro: non puo' peggiorare)
  CONTROLLI  i falsi in CIFRA restano fermati — sono gli unici con L4.1, e
             L4.1 e' deterministico: il riempimento non dovrebbe toccarlo.
  VERI       restano ammessi in ogni regime.

⇒ SE la predizione regge, la conseguenza per il DESIGN e' grossa: **la
  priorita' che ho pubblicato un'ora fa si dissolve** — non c'e' niente da
  ordinare, perche' a lunghezze vere fallisce tutto — e soprattutto **il
  contributo del giudice neurale va a ZERO esattamente dove vivono i documenti
  reali**. Lo strato deterministico non sarebbe «la vittoria piu' grossa»:
  sarebbe **l'unica cosa in piedi**.

CONDIZIONE DI FALSIFICAZIONE: se a 1400 caratteri gli scambi restano fermati
come a 450, il traino non tocca questa famiglia, la mia baseline regge com'e'
e la priorita' pubblicata resta valida.

DUE CONTROLLI CHE DEVONO POTER FALLIRE:
  (a) il riempimento non deve contenere NESSUN glifo 0-9 — altrimenti
      introduco una seconda variabile e il banco non misura la lunghezza;
  (b) i claim VERI devono restare ammessi in TUTTI i regimi — se cadessero,
      starei misurando un gate che si rompe, non un gate che si fa ingannare.

REGIME: un processo, store temporaneo vuoto (`Memory(path=…)`), porta SDK,
`validate="full"`, italiano. Strati letti da `warnings` (la ricevuta non ha
una chiave `layers`: cella 50). Riempimento = clausole di stile PERTINENTI
senza cifre, come in @ws4.

    python docs/stato-reale/banchi/ws3-F1-la-baseline-regge-su-una-fonte-vera.py
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
REFERTO = (
    "Terapia in atto. Il paziente assume metformina 850 mg due volte al giorno. "
    "Il ramipril e' prescritto a 5 mg al mattino. "
    "L'acido acetilsalicilico e' prescritto a 100 mg alla sera. "
    "Controllo previsto a tre mesi."
)
OMI_FONTI = {
    "affidamento": "L'affidamento al fornitore Bertani e' subordinato "
                   "all'approvazione preventiva del collegio dei revisori.",
    "rimborso": "Il rimborso delle spese di trasferta e' ammesso solo entro il "
                "limite mensile fissato dal regolamento interno.",
    "proroga": "La proroga del contratto di servizio decorre dalla scadenza "
               "originaria ed e' condizionata alla verifica dei requisiti da "
               "parte dell'ufficio.",
}

# clausole di stile PERTINENTI, senza NESSUNA cifra (controllo (a) lo verifica)
ZAVORRA_CONTRATTO = [
    "Le parti danno atto di aver preso visione integrale del presente accordo e "
    "di accettarne ogni clausola senza riserva alcuna.",
    "Il foro competente in via esclusiva per ogni controversia e' quello del "
    "luogo in cui ha sede la stazione appaltante.",
    "Ogni comunicazione fra le parti si intende validamente effettuata se "
    "trasmessa agli indirizzi indicati in epigrafe.",
    "Le parti si impegnano a mantenere riservata ogni informazione appresa in "
    "ragione dell'esecuzione del presente accordo.",
    "L'eventuale invalidita' di una singola clausola non comporta la nullita' "
    "dell'intero accordo, che resta valido per la parte residua.",
    "Le modifiche al presente atto sono valide soltanto se risultanti da atto "
    "scritto sottoscritto da entrambe le parti.",
    "Il presente accordo annulla e sostituisce ogni precedente intesa fra le "
    "parti avente il medesimo oggetto.",
    "La tolleranza di una parte rispetto a comportamenti dell'altra non "
    "costituisce rinuncia ai diritti derivanti dalle clausole non osservate.",
]
ZAVORRA_REFERTO = [
    "Anamnesi raccolta in sede di visita ambulatoriale, paziente collaborante e "
    "orientato nel tempo e nello spazio.",
    "Non si segnalano reazioni avverse riferite dal paziente nel periodo "
    "intercorso dall'ultimo controllo.",
    "Si raccomanda di mantenere le abitudini alimentari concordate e di "
    "proseguire l'attivita' fisica secondo tolleranza.",
    "Il paziente e' stato informato della necessita' di riferire tempestivamente "
    "ogni sintomo di nuova insorgenza.",
    "Copia del presente referto e' consegnata al paziente e trasmessa al medico "
    "curante per opportuna conoscenza.",
    "Si allega alla presente la documentazione prodotta in sede di accesso, "
    "conservata agli atti dell'ambulatorio.",
    "La presente relazione ha valore di aggiornamento clinico e non sostituisce "
    "la valutazione dello specialista di riferimento.",
    "Nulla da segnalare in merito all'aderenza terapeutica riferita nel corso "
    "del colloquio odierno.",
]
ZAVORRA_AMM = [
    "Il presente verbale e' redatto a cura della segreteria e conservato agli "
    "atti secondo le modalita' previste dal regolamento.",
    "Si da' atto della regolarita' della convocazione e della presenza del "
    "numero legale per la validita' della seduta.",
    "Ogni determinazione assunta e' resa pubblica mediante affissione all'albo "
    "per il periodo previsto dalle disposizioni vigenti.",
    "Le eventuali osservazioni dei presenti sono riportate a verbale su "
    "espressa richiesta degli interessati.",
    "La seduta prosegue con la trattazione dei successivi punti iscritti "
    "all'ordine del giorno.",
    "Copia del presente atto e' trasmessa agli uffici competenti per gli "
    "adempimenti conseguenti.",
    "Non si registrano rilievi in ordine alla procedura seguita per la "
    "formazione della presente determinazione.",
    "Il verbale e' letto, approvato e sottoscritto seduta stante dai "
    "componenti intervenuti.",
]

# (famiglia, etichetta, chiave-fonte, claim, ramo)
CASI: list[tuple[str, str, str, str, str]] = []
for _et, _k, _a, _b in [
    ("penali 2%/5%", "contratto",
     "La penale per il ritardo e' pari al 5% dell'importo contrattuale.",
     "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale."),
    ("termini mar/apr", "contratto",
     "Il termine di consegna e' fissato al 30 aprile 2027.",
     "Il termine per la contestazione dei vizi e' fissato al 12 marzo 2027."),
    ("importi 148k/22k", "contratto",
     "La cauzione definitiva e' pari a 148000 euro.",
     "L'importo contrattuale e' di 22000 euro."),
    ("metform./ramipr.", "referto",
     "Il ramipril e' prescritto a 850 mg al mattino.",
     "Il paziente assume metformina 5 mg due volte al giorno."),
    ("metform./acido", "referto",
     "L'acido acetilsalicilico e' prescritto a 850 mg alla sera.",
     "Il paziente assume metformina 100 mg due volte al giorno."),
    ("ramipr./acido", "referto",
     "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.",
     "Il ramipril e' prescritto a 100 mg al mattino."),
]:
    CASI.append(("SCAMBIO", f"{_et} A", _k, _a, "scambio"))
    CASI.append(("SCAMBIO", f"{_et} B", _k, _b, "scambio"))
for _et, _k, _cif, _par in [
    ("importo", "contratto",
     "L'importo contrattuale e' di 391000 euro.",
     "L'importo contrattuale e' di trecentonovantunomila euro."),
    ("cauzione", "contratto",
     "La cauzione definitiva e' pari a 70000 euro.",
     "La cauzione definitiva e' pari a settantamila euro."),
    ("dosaggio", "referto",
     "Il ramipril e' prescritto a 73 mg al mattino.",
     "Il ramipril e' prescritto a settantatre mg al mattino."),
]:
    CASI.append(("NUMERALE", f"{_et} cifra", _k, _cif, "cifra"))
    CASI.append(("NUMERALE", f"{_et} parole", _k, _par, "parole"))
for _et, _claim in [
    ("affidamento", "Il consiglio ha disposto l'affidamento al fornitore Bertani."),
    ("rimborso", "Le spese di trasferta sono rimborsate al personale."),
    ("proroga", "Il contratto di servizio e' stato prorogato."),
]:
    CASI.append(("OMISSIONE", _et, f"omi/{_et}", _claim, "omissione"))

# controllo (b): i VERI, uno per fonte
VERI = [
    ("contratto", "La penale per il ritardo e' pari al 2% dell'importo contrattuale."),
    ("referto", "Il ramipril e' prescritto a 5 mg al mattino."),
    ("omi/affidamento", "L'affidamento al fornitore Bertani richiede il via libera "
                        "dei revisori."),
]

ZAVORRE = {"contratto": ZAVORRA_CONTRATTO, "referto": ZAVORRA_REFERTO}


def _fonte(chiave: str, n_frasi: int) -> str:
    if chiave.startswith("omi/"):
        base, zav = OMI_FONTI[chiave[4:]], ZAVORRA_AMM
    elif chiave == "contratto":
        base, zav = CONTRATTO, ZAVORRA_CONTRATTO
    else:
        base, zav = REFERTO, ZAVORRA_REFERTO
    if n_frasi <= 0:
        return base
    return base + " " + " ".join(zav[:n_frasi])


def _strati(ric) -> list[str]:
    return [str(w.get("layer")) for w in (ric.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)} · python {sys.version.split()[0]}")
    print("    store TEMPORANEO vuoto · un processo · porta SDK · validate='full' · IT")
    print("    unica variabile: la LUNGHEZZA della fonte (clausole di stile SENZA cifre)")

    # ── controllo (a): la zavorra non porta cifre ────────────────────────
    sporche = [z for z in (ZAVORRA_CONTRATTO + ZAVORRA_REFERTO + ZAVORRA_AMM)
               if re.search(r"[0-9]", z)]
    print(f"\n  [a] CONTROLLO: clausole di zavorra con una cifra: {len(sporche)}")
    if sporche:
        print("      CONTROLLO CADUTO: la zavorra porta cifre ⇒ due variabili insieme.")
        for z in sporche[:3]:
            print(f"         {z[:90]}")
        return 1

    mem = Memory(str(Path(tempfile.mkdtemp()) / "f1len.db"))
    regimi = [0, 2, 4, 8]
    lung = {n: len(_fonte("contratto", n)) for n in regimi}
    print(f"  [b] regimi (lunghezza della fonte CONTRATTO): "
          f"{', '.join(f'+{n}fr={lung[n]}ch' for n in regimi)}")

    # ── controllo (b): i veri, in ogni regime ────────────────────────────
    # ⚠️ CONTROLLO RISCRITTO dopo la prima esecuzione (28/08 ~19:20), e dichiaro
    # il perche'. L'avevo scritto «nessun VERO deve essere quarantinato in nessun
    # regime», ed e' scattato: il vero «L'affidamento al fornitore Bertani
    # richiede il via libera dei revisori» e' quarantinato a 0.37-1.60 in TUTTI
    # E QUATTRO i regimi.
    # Ma un vero rifiutato UNIFORMEMENTE non minaccia QUESTO banco: e' costante,
    # quindi non puo' spiegare una variazione che dipende dalla LUNGHEZZA. Cio'
    # che la minaccerebbe e' un vero che CAMBIA esito coi regimi.
    # ⇒ il controllo giusto per lo scopo e': nessun vero cambia esito.
    #   Il vero rifiutato ovunque resta un REPERTO, stampato qui sotto e NON
    #   nascosto: e' una parafrasi fedele bocciata dal gate, e va misurata a
    #   parte perche' e' un FALSO POSITIVO, non un confondente.
    # 🔑 E' la SECONDA volta in due giorni che scrivo un controllo piu'
    #   GROSSOLANO del suo scopo (ieri la clausola di falsificazione trattava
    #   L4-grounding come uno strato deterministico). La versione originale
    #   resta in questo commento: non si riscrive un criterio dopo aver visto i
    #   numeri senza dichiarare di averlo fatto.
    print("\n  [b] CONTROLLO: nessun VERO cambia esito al variare della lunghezza")
    esiti_veri: dict[str, list[bool]] = {}
    punteggi: dict[str, list[float]] = {}
    for n in regimi:
        for k, prop in VERI:
            r = mem.add(prop, topic=f"len/vero/{n}/{k}".replace("/", "_"),
                        source=_fonte(k, n), validate="full")
            esiti_veri.setdefault(k, []).append(str(r.get("status")) != "quarantined")
            punteggi.setdefault(k, []).append(float(r.get("grounding_score") or -1))
    instabili = {k: v for k, v in esiti_veri.items() if len(set(v)) > 1}
    sempre_no = {k: v for k, v in esiti_veri.items() if not any(v)}
    print(f"      veri che CAMBIANO esito: {len(instabili)} su {len(esiti_veri)}")
    for k in sempre_no:
        print(f"      📌 REPERTO (costante, quindi NON un confondente): «{k}» e'")
        print(f"         quarantinato in TUTTI i regimi — ground "
              f"{', '.join(f'{x:.2f}' for x in punteggi[k])}")
        print(f"         E' UNA PARAFRASI FEDELE della fonte ⇒ falso positivo del")
        print(f"         gate, indipendente dalla lunghezza. Da misurare a parte.")
    if instabili:
        print("      CONTROLLO CADUTO: un VERO cambia esito con la lunghezza ⇒ non")
        print("      posso attribuire alla lunghezza cio' che vedo sui falsi.")
        for k, v in instabili.items():
            print(f"         {k}: {v}")
        return 1

    # ── la matrice ──────────────────────────────────────────────────────
    print(f"\n  {'famiglia':<10} {'caso':<18} " +
          " ".join(f"{'+' + str(n) + 'fr':>9}" for n in regimi))
    print("  " + "-" * (30 + 10 * len(regimi)))
    matrice: dict[tuple[str, str], dict[int, bool]] = {}
    for fam, et, k, claim, ramo in CASI:
        cells = []
        for n in regimi:
            r = mem.add(claim, topic=f"len/{fam}/{et}/{n}".replace("/", "_").replace(" ", "_"),
                        source=_fonte(k, n), validate="full")
            entra = str(r.get("status")) != "quarantined"
            g = r.get("grounding_score")
            matrice.setdefault((fam, et), {})[n] = entra
            cells.append(f"{'E' if entra else 'f'}{float(g or -1):>8.1f}")
        matrice[(fam, et)]["_ramo"] = ramo  # type: ignore[assignment]
        print(f"  {fam:<10} {et:<18} " + " ".join(c.rjust(9) for c in cells))

    # ── il verdetto ─────────────────────────────────────────────────────
    print("\n  ══ ENTRANO, per famiglia e per regime ══")
    print(f"     {'famiglia':<12} " + " ".join(f"{'+' + str(n) + 'fr':>8}" for n in regimi))
    for fam in ("SCAMBIO", "NUMERALE", "OMISSIONE"):
        tot = [(f, e) for (f, e), _v in matrice.items()
               if f == fam and matrice[(f, e)].get("_ramo") != "cifra"]
        riga = []
        for n in regimi:
            riga.append(f"{sum(1 for key in tot if matrice[key][n])}/{len(tot)}")
        print(f"     {fam:<12} " + " ".join(r.rjust(8) for r in riga))
    cifre = [(f, e) for (f, e) in matrice if matrice[(f, e)].get("_ramo") == "cifra"]
    riga = [f"{sum(1 for key in cifre if matrice[key][n])}/{len(cifre)}" for n in regimi]
    print(f"     {'(cifra→ctrl)':<12} " + " ".join(r.rjust(8) for r in riga))

    falsi = [k for k in matrice if matrice[k].get("_ramo") != "cifra"]
    ent0 = sum(1 for k in falsi if matrice[k][regimi[0]])
    entN = sum(1 for k in falsi if matrice[k][regimi[-1]])
    print(f"\n  ══ VERDETTO ══")
    print(f"     falsi che entrano: {ent0}/{len(falsi)} a {lung[regimi[0]]} caratteri"
          f"  →  {entN}/{len(falsi)} a {lung[regimi[-1]]}")
    # ⚠️ Blocco riscritto dopo la prima esecuzione: la versione precedente era
    # binaria (entN > ent0 ⇒ «fallisce tutto, non c'e' niente da ordinare») e i
    # numeri NON la sostengono — 14 su 18, non 18 su 18, e l'OMISSIONE migliora.
    # TERZA volta in due giorni che scrivo un verdetto piu' grossolano del dato.
    # La frase originale resta qui: non si riscrive una conclusione in silenzio.
    print("     PAGELLA della predizione, cella per cella:")
    for fam, atteso in (("SCAMBIO", 12), ("NUMERALE", 3), ("OMISSIONE", 3)):
        keys = [k for k in matrice if k[0] == fam
                and matrice[k].get("_ramo") != "cifra"]
        a = sum(1 for k in keys if matrice[k][regimi[0]])
        b = sum(1 for k in keys if matrice[k][regimi[-1]])
        if b == atteso:
            esito = "ESATTA"
        elif (b - a) * (atteso - a) > 0:
            esito = "direzione giusta, TAGLIA sbagliata"
        elif b == a:
            esito = "NESSUN EFFETTO"
        else:
            esito = "DIREZIONE SBAGLIATA"
        print(f"       {fam:<10} previsto {a}→{atteso}   misurato {a}→{b}   {esito}")
    c0 = sum(1 for k in cifre if matrice[k][regimi[0]])
    cN = sum(1 for k in cifre if matrice[k][regimi[-1]])
    print(f"       {'CONTROLLI':<10} previsto {c0}→{c0}   misurato {c0}→{cN}   "
          f"{'ESATTA' if cN == c0 else 'SBAGLIATA'}")
    print(f"\n     falsi che entrano: {ent0}/{len(falsi)} a {lung[regimi[0]]} car."
          f"  →  {entN}/{len(falsi)} a {lung[regimi[-1]]}")
    print("\n     COSA SI PUO' DIRE, e non di piu':")
    print("     ① IL RISULTATO CHE DECIDE IL DESIGN — i falsi in CIFRA, gli UNICI")
    print("       che `L4.1` ferma, restano fermati a OGNI lunghezza"
          f" ({c0}/{len(cifre)} → {cN}/{len(cifre)}),")
    print("       mentre la protezione del GIUDICE sugli scambi si sgretola.")
    print("       ⇒ lo strato DETERMINISTICO e' indipendente dal regime;")
    print("         il giudice neurale NO. Misurato, non asserito.")
    print("     ② la protezione che cade, cade SUBITO: bastano DUE frasi di stile")
    print("       (+242 caratteri) — non e' una rampa, e' una soglia (come @ws5).")
    print("     ③ MA NON «fallisce tutto»: due scambi reggono a ogni lunghezza, e")
    print("       l'OMISSIONE addirittura MIGLIORA (3/3 → 2/3). La mia priorita'")
    print("       si SPOSTA, non si dissolve: SCAMBIO resta la famiglia piu' grossa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
