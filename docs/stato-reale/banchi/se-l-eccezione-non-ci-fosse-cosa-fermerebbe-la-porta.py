"""SE L'ECCEZIONE NON CI FOSSE, CHE COSA FERMEREBBE LA PORTA? — sugli stessi 24 letti.

`W7-69` ha misurato al **detector** e ha dichiarato il limite: *«misuro al
detector, non alla porta ⇒ limite superiore»*. `W7-70` ha **letto** quei fatti e
li ha classificati: **11 resoconti, 13 misure, 0 self-claim nudi**.

⚠️ **Ma \"misurare alla porta\" qui e' una domanda mal posta**, e vale la pena
dirlo prima di rispondere: per un fatto `narrative` la porta **salta `L1` per
costruzione** (`narrative_l1_skip`), quindi l'esito sarebbe **0 per definizione**
e non misurerebbe niente.

🎯 **LA DOMANDA GIUSTA E' CONTROFATTUALE**: *se l'eccezione non ci fosse — se
cioe' quegli stessi fatti fossero scritti come scritture ordinarie — che cosa
farebbe la porta?* Perche' quello e' **il prezzo che l'eccezione ci risparmia**,
o **il danno che ci nasconde**: la stessa misura risponde a tutt'e due.

E si combina con `W7-70`: **so gia' che cosa sono quei 24**. Se la porta ne
ferma molti, sono **falsi allarmi su lavoro vero** — perche' zero di essi e' un
self-claim nudo.

ATTESA DICHIARATA PRIMA: la porta ne ferma **una parte cospicua**, perche' il
moat non ha nulla da salvare (questi fatti in gran parte **non hanno una fonte**
o ce l'hanno breve) e `L1` e' un rilevatore lessicale che quel vocabolario lo
sorveglia. ⚠️ **Se invece la porta li lasciasse passare quasi tutti**, allora
`L1` **non decide** su questo materiale e l'eccezione sarebbe **superflua**: e'
un esito che cambierebbe la conclusione di `W7-70` e lo dico con la stessa forza.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **il confronto e' A/B nella stessa esecuzione** sullo stesso fatto:
     `narrative_l1_skip=True` (com'e' oggi) contro `False` (il controfattuale).
     Se il primo non desse SEMPRE `persist`, non starei misurando l'eccezione.
 (2) `ground_write=True`, altrimenti il moat non gira e leggerei un'assenza di
     misura come un verdetto (lezione `W7-62`).
 (3) gli id sono **gli stessi 24** di `W7-70`, letti dal suo output: cosi' la
     classificazione A/B/C e l'esito alla porta stanno sulla stessa riga.

    python -u docs/stato-reale/banchi/se-l-eccezione-non-ci-fosse-cosa-fermerebbe-la-porta.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys

OUT_W770 = (
    r"C:/Users/aurel/AppData/Local/Temp/claude/C--Users-aurel-Desktop-ProgettiAI"
    r"/78ba9444-dd97-498f-bd48-07ca991638a4/scratchpad/out_w770.txt")


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    try:
        testo = open(OUT_W770, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print(f"NON RIUSCITO: non leggo l'output di W7-70 - {e}")
        return 1
    ids = re.findall(r"^  \[\s*\d+\] ([0-9a-f]{12}) ", testo, re.M)
    print(f"  id ripresi dall'output di `W7-70`: {len(ids)}")
    if len(ids) < 10:
        print("NON RIUSCITO: meno di dieci id, il campione non regge.")
        return 1

    c = sqlite3.connect(str(CONFIG.semantic_db))
    q = ",".join("?" * len(ids))
    righe = c.execute(
        f"select id, proposition, grounding_span, writer_role, verified_by, topic "
        f"from facts where id in ({q})", ids).fetchall()
    print(f"  ritrovati nello store: {len(righe)}")

    # DISTRIBUZIONE PRIMA DI DIVIDERE: quanti hanno una fonte da giudicare?
    con_fonte = sum(1 for r in righe if (r[2] or "").strip())
    print(f"\n  -- distribuzione: con `grounding_span` {con_fonte},"
          f" senza {len(righe) - con_fonte}")

    def alla_porta(r, skip: bool):
        _fid, prop, span, wr, vb_raw, _t = r
        try:
            vb = json.loads(vb_raw or "[]")
        except Exception:  # noqa: BLE001
            vb = []
        g = run_validation_gate(
            proposition=prop or "", verified_by=vb, topic=None, agent=None,
            source=span or None, writer_role=wr, narrative_l1_skip=skip,
            **({"ground_write": True} if (span or "").strip() else {}))
        ws = getattr(g, "warnings", None) or []
        lay = sorted({str((w or {}).get("layer") or "?") for w in ws})
        return str(getattr(g, "action", None)), lay

    print("\n  -- CONTROLLO (1): com'e' OGGI, la porta li ammette tutti?")
    oggi_ok = 0
    for r in righe:
        az, _ = alla_porta(r, True)
        oggi_ok += 1 if az == "persist" else 0
    print(f"     ammessi con l'eccezione ATTIVA: {oggi_ok} su {len(righe)}")
    if oggi_ok != len(righe):
        print("     ⚠️ non tutti passano gia' oggi: qualcuno e' fermato da un")
        print("     layer FUORI dalla famiglia `L1`, e per quelli il")
        print("     controfattuale non misura l'eccezione. Li conto a parte.")

    print("\n  == IL CONTROFATTUALE: senza l'eccezione, che cosa succede?")
    print(f"     {'oggi':<10}{'senza':<11}layer che si accenderebbero")
    fermati, esempi = 0, []
    for r in righe:
        az_o, _ = alla_porta(r, True)
        az_s, lay_s = alla_porta(r, False)
        if az_o == "persist" and az_s != "persist":
            fermati += 1
            if len(esempi) < 5:
                esempi.append((az_s, lay_s, r[1]))
        print(f"     {az_o:<10}{az_s:<11}{','.join(lay_s) or '-'}")

    print(f"\n  == LA RIGA CHE CONTA")
    print(f"     senza l'eccezione la porta ne fermerebbe {fermati}"
          f" su {oggi_ok}")
    if oggi_ok and fermati / oggi_ok >= 0.5:
        print("     🔴 E `W7-70` ha gia' letto che cosa sono: **11 resoconti di")
        print("     lavoro, 13 misure verificabili, ZERO self-claim nudi**.")
        print("     ⇒ Senza l'eccezione, questi sarebbero **falsi allarmi su")
        print("     lavoro vero** \u2014 e l'eccezione non e' un buco: e' cio' che")
        print("     li evita. **La compensazione e' misurata, non supposta.**")
    elif oggi_ok and fermati:
        print(f"     🟡 Ne ferma {fermati} su {oggi_ok}: l'eccezione risparmia")
        print("     qualcosa ma non e' decisiva su questo campione.")
    else:
        print("     🪞 NE FERMA ZERO ⇒ su questo materiale `L1` non decide, e")
        print("     **l'eccezione e' superflua**: la mia lettura di `W7-70`")
        print("     («e' una compensazione») CADE, perche' non c'e' niente da")
        print("     compensare. Lo dico con la stessa forza.")

    for az, lay, prop in esempi:
        print(f"     {az:<11}{','.join(lay):<26}{(prop or '')[:44]}")

    print("\n  ⚠️ COSA NON DICE: 24 fatti, gli stessi di `W7-70` e quindi lo")
    print("  stesso campione (uno ogni 14) — non e' una stima sul corpus. E il")
    print("  controfattuale cambia UN parametro: non dice che cosa sarebbe")
    print("  successo se quei fatti fossero stati SCRITTI diversamente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
