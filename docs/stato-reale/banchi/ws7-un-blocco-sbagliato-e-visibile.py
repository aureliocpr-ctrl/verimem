# -*- coding: utf-8 -*-
"""«A WRONG BLOCK IS VISIBLE AND REVERSIBLE» — la promessa del README, alla porta

PERCHE' ESISTE, e perche' non e' un doppione. `chi_ha_gia_misurato.py quarantined_by`
da' **17 celle, sette di @ws2**: tutte guardano il **CAMPO nel database**. Cercando
`quarantine_log` invece: **nessuna cella**. La differenza e' il punto — e' la classe
gia' registrata *«il livello a cui misuri decide il verdetto»*: campo interno <
funzione pubblica < porta che il prodotto usa. **Le altre hanno misurato il campo;
il README promette la FUNZIONE all'utente.**

LE QUATTRO PROMESSE, copiate dal README (righe 152-166), tutte falsificabili:

  P1  ogni riga di `quarantine_log(explain=True)` dice **QUALE schermo** l'ha fermata
  P2  ... e **cosa lo farebbe passare** («what would let it through»)
  P3  **ricalcolato sul momento**, «so it works on claims held long before you asked»
  P4  il claim fermato dal controllo di entailment e' l'unico che non si puo'
      spiegare a posteriori (la fonte non e' conservata) e **lo DICE, invece di non
      restituire niente**

P3 e' la piu' importante e la meno ovvia: le 17 celle delle altre dicono che il campo
`quarantined_by` e' quasi sempre vuoto. **Se P3 regge, quel vuoto NON e' un difetto di
vetrina** — la spiegazione non viene letta, viene ricalcolata. **Se P3 non regge, il
README promette una cosa che il prodotto non fa.** Le due letture si escludono, ed e'
esattamente cio' che un banco deve separare.

IL CONTROLLO CHE DEVE POTER FALLIRE: un fatto ammesso NON deve comparire nel log.
Senza, un log che restituisse tutto sembrerebbe perfetto su ogni promessa.

    python docs/stato-reale/banchi/ws7-un-blocco-sbagliato-e-visibile.py

Store TEMPORANEO. Fuori da pytest (li' l'embedder e' uno stub su SHA-256).
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

#: fonte che sostiene alla lettera i quattro claim di dominio qui sotto.
FONTE = (
    "Verbale della seduta del 14 marzo. La pratica numero 2214 e' stata verificata "
    "dall'ufficio tecnico. Il preventivo e' stato approvato dal consiglio con nove voti "
    "favorevoli. Il documento e' stato firmato dal presidente in data 14 marzo. Il guasto "
    "segnalato a gennaio e' stato risolto dalla ditta incaricata. La sede si trova a Verona. "
    "Il compenso pattuito e' di 3200 euro."
)

#: claim VERI, ognuno sostenuto letteralmente dalla fonte, e ognuno con una parola
#: che la famiglia L1 tratta come auto-affermazione (verificata / approvato / firmato /
#: risolto): sono i verbali d'ufficio di `LANT-32`, dove 8 su 10 vengono fermati.
VERI = [
    "La pratica numero 2214 e' stata verificata dall'ufficio tecnico.",
    "Il preventivo e' stato approvato dal consiglio con nove voti favorevoli.",
    "Il documento e' stato firmato dal presidente in data 14 marzo.",
    "Il guasto segnalato a gennaio e' stato risolto dalla ditta incaricata.",
]

#: claim che la fonte NON sostiene: serve a P4 (il caso che non si puo' spiegare dopo).
NON_SOSTENUTO = "Il compenso pattuito e' di 9900 euro."

#: controllo che deve poter fallire: e' nella fonte e non ha parole di auto-affermazione.
AMMESSO = "La sede si trova a Verona."


def _campi(riga: dict) -> str:
    return " ".join(sorted(riga.keys()))


def main() -> int:
    for tok in ("9900",):
        if tok in FONTE:
            print(f"  CONTROLLO CADUTO: «{tok}» e' nella fonte, non e' piu' un non-sostenuto")
            return 1
    print(f"  controllo retto: «9900» assente dalla fonte, {len(VERI)} veri sostenuti alla lettera")

    from verimem.client import Memory  # noqa: PLC0415

    radice = Path(tempfile.mkdtemp())
    percorso = radice / "visibile.db"
    mem = Memory(str(percorso))

    fermati, ammessi = [], []
    for i, claim in enumerate(VERI + [NON_SOSTENUTO, AMMESSO]):
        ric = mem.add(claim, topic=f"verbale/{i}", source=FONTE, validate="full")
        stato = str(ric.get("status"))
        g = float(ric.get("grounding_score") or -1)
        (fermati if stato == "quarantined" else ammessi).append((claim, g))
        segno = "🔴 FERMATO" if stato == "quarantined" else "🟢 ammesso"
        print(f"  {segno}  {g:6.2f}  {claim[:64]}")

    if not fermati:
        print("\n  NIENTE DA MISURARE: nessun claim e' stato fermato, il banco non dice nulla")
        return 1

    # ---- il log SENZA explain, per poter attribuire a `explain` cio' che aggiunge ----
    nudo = mem.quarantine_log(limit=50)
    spiegato = mem.quarantine_log(limit=50, explain=True)
    print(f"\n  quarantine_log(): {len(nudo)} righe  ·  explain=True: {len(spiegato)} righe")
    if not spiegato:
        print("  🔴 P1-P4 TUTTE CADUTE: il log e' VUOTO benche' ci siano fatti fermati")
        return 1

    campi_nudi = set(nudo[0].keys()) if nudo else set()
    campi_spieg = set(spiegato[0].keys())
    aggiunti = sorted(campi_spieg - campi_nudi)
    print(f"  campi aggiunti da explain=True: {aggiunti or '— NESSUNO'}")

    # ---- CONTROLLO: il claim ammesso non deve comparire ----
    testi_log = " ".join(str(r.get("proposition") or r.get("content") or "") for r in spiegato)
    if AMMESSO[:24] in testi_log:
        print(f"  🔴 CONTROLLO CADUTO: «{AMMESSO}» e' AMMESSO ma compare nel log dei bloccati")
        return 1
    print(f"  controllo retto: il claim ammesso NON compare fra le {len(spiegato)} righe")

    # ---- P1 / P2 / P4, riga per riga ----
    p1 = p2 = p4 = 0
    print()
    for r in spiegato:
        testo = str(r.get("proposition") or r.get("content") or "")[:52]
        blob = " ".join(f"{k}={v}" for k, v in r.items() if v not in (None, "", [], {}))
        # P1: nomina uno schermo? cerco un nome di layer nella riga.
        ha_schermo = any(s in blob for s in ("L1.", "L4.", "L3-", "moat", "entail", "grounding"))
        # P2: dice cosa lo farebbe passare?
        ha_rimedio = any(s in blob.lower() for s in
                         ("would", "let it through", "rimedi", "fix", "remed", "pass if",
                          "verified_by", "restore", "add a source", "per farlo passare"))
        # P4: sul non-sostenuto, dichiara di non poter spiegare?
        e_moat = NON_SOSTENUTO[:24] in testo or "9900" in blob
        dichiara = any(s in blob.lower() for s in
                       ("not retained", "cannot be explained", "non conservata", "unavailable",
                        "no longer available", "source is not"))
        p1 += ha_schermo
        p2 += ha_rimedio
        p4 += (dichiara if e_moat else 0)
        print(f"   {'✅' if ha_schermo else '❌'} schermo  "
              f"{'✅' if ha_rimedio else '❌'} rimedio   {testo}")

    n = len(spiegato)
    moat_righe = sum(1 for r in spiegato
                     if NON_SOSTENUTO[:24] in str(r.get("proposition") or r.get("content") or ""))

    # ---- P3: il campo nel db e' popolato, o la spiegazione e' ricalcolata? ----
    con = sqlite3.connect(str(percorso))
    try:
        col = [d[1] for d in con.execute("PRAGMA table_info(facts)")]
        if "quarantined_by" in col:
            vuoti = con.execute(
                "SELECT COUNT(*) FROM facts WHERE status='quarantined' "
                "AND (quarantined_by IS NULL OR quarantined_by='')").fetchone()[0]
            tot = con.execute("SELECT COUNT(*) FROM facts WHERE status='quarantined'").fetchone()[0]
        else:
            vuoti = tot = -1
    finally:
        con.close()

    print("\n  " + "=" * 76)
    print(f"  P1 nomina lo schermo      {p1}/{n}")
    print(f"  P2 dice come rimediare    {p2}/{n}")
    print(f"  P4 caso non-spiegabile    {p4}/{moat_righe} righe del claim non sostenuto")
    if tot >= 0:
        print(f"  P3 nel DB: quarantined_by VUOTO su {vuoti}/{tot} fermati "
              f"⇒ {'la spiegazione NON puo venire dal campo: e ricalcolata' if vuoti else 'il campo e popolato: P3 non e distinguibile qui'}")
    print(f"     campi che explain=True aggiunge: {aggiunti or 'NESSUNO'}")
    print("  " + "=" * 76)
    print(f"\n  store temporaneo: {radice}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
