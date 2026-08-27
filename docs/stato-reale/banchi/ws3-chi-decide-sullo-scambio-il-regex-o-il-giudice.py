# -*- coding: utf-8 -*-
"""CHI DECIDE SULLO SCAMBIO DI ATTRIBUZIONE: la regex o il giudice?

@ws4 alle 22:00 ha misurato lo scambio di attribuzione sui 12 casi qui sotto
(sei coppie, entrambi i versi) e ha trovato 5 concordi su 6, 3 ammessi su 7 sul
dominio vero. Poi ha provato QUATTRO ipotesi su cosa distingua gli ammessi dai
fermati - specie, verso, rapporto fra i valori, struttura sintattica - e sono
cadute tutte. Ha chiuso in negativo, correttamente: «non ho la variabile e non
la invento».

Le sue quattro ipotesi riguardano tutte la FORMA DEL CLAIM. La mia riguarda
un'altra cosa: QUALE COMPONENTE decide. Il suo banco stampa `status` e
`grounding_score`; non stampa `layers`. Questo lo stampa.

LA PREDIZIONE, scritta prima di eseguire:

  `layers` e' VUOTO su tutti e 12 - anche sui quattro fermati a 0.7-4.9.
  Se e' cosi', L4.1 non parla MAI sullo scambio di attribuzione, e l'intera
  separazione ammesso/fermato la produce il SOLO giudice neurale.
  ⇒ la forma corretta della falla non e' «il gate e' cieco all'attribuzione»
    ma «sull'attribuzione il gate non ha ALCUNO strato deterministico: guarda
    solo il giudice, e il giudice sbaglia N volte su 12».
  ⇒ e la cura non e' «aggiustare L4.1» - L4.1 non sta partecipando - ma
    COSTRUIRE uno strato che oggi non esiste.

CONDIZIONE DI FALSIFICAZIONE: se anche UNO dei casi fermati porta L4.1 (o
qualunque altro strato) fra i suoi `layers`, la tesi cade: vorrebbe dire che
uno strato deterministico partecipa e discrimina.

CONTROLLO POSITIVO CHE DEVE POTER FALLIRE - ed e' il controllo che manca a
entrambi i banchi precedenti, mio e suo: un `layers` vuoto ovunque puo' anche
voler dire che il mio LETTORE e' rotto. Quindi prima di leggere i 12 casi
chiedo a L4.1 di parlare su QUESTA stessa fonte, con una cifra che la fonte non
contiene affatto. Se li' `layers` e' vuoto, lo strumento e' cieco e il banco si
ferma senza dare un verdetto.

CONTROLLO NEGATIVO: due claim VERI devono essere ammessi (come nel banco di
@ws4), altrimenti la fonte non e' stata letta.

    python docs/stato-reale/banchi/ws3-chi-decide-sullo-scambio-il-regex-o-il-giudice.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# --- le fonti e le coppie sono COPIATE ALLA LETTERA dal banco di @ws4 -------
# docs/stato-reale/banchi/lo-scambio-e-simmetrico-o-no.py
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
FONTI = {"contratto": CONTRATTO, "referto": REFERTO}

COPPIE = [
    ("contratto", "penali 2%/5%",
     "La penale per il ritardo e' pari al 5% dell'importo contrattuale.",
     "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale."),
    ("contratto", "termini marzo/aprile",
     "Il termine di consegna e' fissato al 30 aprile 2027.",
     "Il termine per la contestazione dei vizi e' fissato al 12 marzo 2027."),
    ("contratto", "importi 148000/22000",
     "La cauzione definitiva e' pari a 148000 euro.",
     "L'importo contrattuale e' di 22000 euro."),
    ("referto", "metformina/ramipril",
     "Il ramipril e' prescritto a 850 mg al mattino.",
     "Il paziente assume metformina 5 mg due volte al giorno."),
    ("referto", "metformina/acido",
     "L'acido acetilsalicilico e' prescritto a 850 mg alla sera.",
     "Il paziente assume metformina 100 mg due volte al giorno."),
    ("referto", "ramipril/acido",
     "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.",
     "Il ramipril e' prescritto a 100 mg al mattino."),
]

# controllo POSITIVO: la cifra NON compare da nessuna parte nelle due fonti
CTRL_POSITIVI = [
    ("contratto", "La penale per il ritardo e' pari al 7% dell'importo contrattuale."),
    ("contratto", "L'importo contrattuale e' di 391000 euro."),
    ("referto", "Il ramipril e' prescritto a 73 mg al mattino."),
]
CTRL_VERI = [
    ("contratto", "La penale per il ritardo e' pari al 2% dell'importo contrattuale."),
    ("referto", "Il ramipril e' prescritto a 5 mg al mattino."),
]


def _lay(ric) -> list:
    """Gli strati che hanno parlato.

    ATTENZIONE - misurato il 27/08 alle 22:11, e la prima stesura di questo
    banco ci e' cascata: la ricevuta di `add()` NON ha una chiave `layers`.
    Le sue chiavi sono adjudication, advice, grounding_score, id, moat,
    quarantined_by, status, stored, warnings. `ric.get("layers")` restituisce
    quindi [] SEMPRE, per qualunque scrittura, qualunque cosa sia scattata:
    un lettore che guarda li' misura zero e crede di aver misurato.
    Gli strati stanno dentro `warnings`, uno per avviso, sotto la chiave
    `layer`. La riga di log `flow.write ... layers=[...]` e' la terza
    superficie, ed e' quella che riporta chi ha AGITO (client.py:725).
    """
    return [str(w.get("layer")) for w in (ric.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


def _fmt(ls: list) -> str:
    return ",".join(str(x) for x in ls) if ls else "-VUOTO-"


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)}")
    print(f"    python {sys.version.split()[0]} · store TEMPORANEO vuoto "
          f"(Memory(path=...)) · un solo processo · porta SDK · validate='full'")

    mem = Memory(str(Path(tempfile.mkdtemp()) / "chidecide.db"))

    # ---- controllo NEGATIVO: i veri devono entrare ------------------------
    print("\n  [1] CONTROLLO: i claim VERI entrano, e il giudice sta girando")
    for nome, prop in CTRL_VERI:
        r = mem.add(prop, topic=f"chi/vero/{nome}", source=FONTI[nome], validate="full")
        g = r.get("grounding_score")
        st = str(r.get("status"))
        print(f"      {st:<12} ground={g}  layers={_fmt(_lay(r))}   {prop[:52]}")
        if st == "quarantined":
            print("      CONTROLLO CADUTO: un claim VERO e' quarantinato.")
            return 1
        if g is None:
            print("      CONTROLLO CADUTO: grounding_score e' None ⇒ il giudice NON")
            print("      sta girando. Un banco che non giudica non misura niente.")
            return 1

    # ---- controllo POSITIVO: L4.1 deve saper parlare su QUESTA fonte ------
    print("\n  [2] CONTROLLO POSITIVO: L4.1 sa parlare su queste fonti?")
    print("      (cifra ASSENTE dalla fonte: se qui layers e' vuoto, il mio")
    print("       LETTORE e' rotto e questo banco non puo' dare un verdetto)")
    parla = 0
    for nome, prop in CTRL_POSITIVI:
        r = mem.add(prop, topic=f"chi/ctrl/{nome}", source=FONTI[nome], validate="full")
        ls = _lay(r)
        parla += 1 if ls else 0
        print(f"      {str(r.get('status')):<12} ground={r.get('grounding_score')}  "
              f"layers={_fmt(ls)}   {prop[:50]}")
    print(f"      ⇒ strati che parlano: {parla} su {len(CTRL_POSITIVI)}")
    if parla == 0:
        print("      CONTROLLO POSITIVO CADUTO: nessuno strato parla nemmeno su una")
        print("      cifra del tutto assente. Lo strumento e' cieco: NESSUN VERDETTO.")
        return 1

    # ---- i 12 casi di scambio --------------------------------------------
    print("\n  [3] I DODICI SCAMBI (le sei coppie di @ws4, entrambi i versi)")
    print(f"      {'coppia':<22} {'verso':<6} {'esito':<7} {'ground':>7}  layers")
    print("      " + "-" * 68)
    ammessi, fermati = [], []
    for i, (nome, coppia, a, b) in enumerate(COPPIE):
        for j, prop in enumerate((a, b)):
            r = mem.add(prop, topic=f"chi/{i}/{j}", source=FONTI[nome], validate="full")
            st = str(r.get("status"))
            g = r.get("grounding_score")
            gf = float(g) if g is not None else -1.0
            ls = _lay(r)
            esito = "ferma" if st == "quarantined" else "ENTRA"
            (fermati if esito == "ferma" else ammessi).append((coppia, esito, gf, ls))
            print(f"      {coppia:<22} {'A' if j == 0 else 'B':<6} {esito:<7} "
                  f"{gf:7.1f}  {_fmt(ls)}")

    # ---- il verdetto, su ENTRAMBE le popolazioni -------------------------
    print(f"\n  [4] LE DUE POPOLAZIONI, separate")
    with_layers_amm = [x for x in ammessi if x[3]]
    with_layers_fer = [x for x in fermati if x[3]]
    print(f"      AMMESSI  {len(ammessi):>2} su 12 · con almeno uno strato: "
          f"{len(with_layers_amm)}")
    print(f"      FERMATI  {len(fermati):>2} su 12 · con almeno uno strato: "
          f"{len(with_layers_fer)}")

    print("\n  [5] VERDETTO")
    if with_layers_fer:
        print("      TESI FALSIFICATA. Almeno un caso FERMATO porta uno strato:")
        for c, _e, g, ls in with_layers_fer:
            print(f"         {c:<22} ground={g:.1f}  layers={_fmt(ls)}")
        print("      ⇒ uno strato deterministico partecipa e discrimina. La forma")
        print("        «solo il giudice decide» e' FALSA e la ritiro.")
    elif not with_layers_amm and not with_layers_fer:
        print("      TESI RETTA. `layers` e' VUOTO su tutti e 12 - ammessi e fermati.")
        print(f"      Eppure su una cifra ASSENTE gli strati parlano "
              f"({parla}/{len(CTRL_POSITIVI)}): lo strumento vede.")
        print("      ⇒ sullo SCAMBIO DI ATTRIBUZIONE nessuno strato deterministico")
        print("        interviene mai. La separazione fra i")
        print(f"        {len(ammessi)} ammessi e i {len(fermati)} fermati e' prodotta")
        print("        INTERAMENTE dal giudice neurale.")
        print("      ⇒ le quattro ipotesi di @ws4 cercavano una regolarita' nella")
        print("        forma del claim: se a decidere e' il solo modello, una")
        print("        regolarita' di quel tipo puo' non esistere affatto.")
        print("      ⇒ e la cura NON e' «aggiustare L4.1»: L4.1 non partecipa.")
        print("        Servirebbe uno strato soggetto-valore che oggi non esiste.")
    else:
        print("      RISULTATO MISTO: strati sugli AMMESSI ma non sui FERMATI.")
        for c, _e, g, ls in with_layers_amm:
            print(f"         AMMESSO {c:<20} ground={g:.1f}  layers={_fmt(ls)}")
        print("      ⇒ da spiegare: uno strato parla e il fatto entra lo stesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
