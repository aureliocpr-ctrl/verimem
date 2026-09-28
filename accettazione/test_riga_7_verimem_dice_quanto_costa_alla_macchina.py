"""RIGA 7 — verimem costa al massimo X MB fissi e Y MB per sessione, e il doctor lo dice.

LA PROMESSA. Aurelio, 28/09: «non si capisce come mai sta RAM sia sempre satura […] non
può essere che ognuna di voi pesi 2 GB, così non è scalabile nessun sistema». Riga 7 del
tabellone (lead, 28/09 19:18): verimem costa al massimo X MB fissi sulla macchina e Y MB
per sessione, e `verimem doctor` stampa i due numeri misurati.

COSA VEDE L'UTENTE. Apre una sessione MCP come dice il README e scrive due fatti con la
fonte: il giudizio passa dal daemon condiviso. `verimem doctor --json` gli dice, sulla
riga `memory`, quanta memoria impegnata tiene il daemon (il costo fisso) e quanta il
server della sua sessione (il costo per sessione), entro i due tetti che il prodotto
dichiara. Memoria IMPEGNATA e non unica: sotto pressione il sistema comprime i processi
fermi e la unica scende, mentre la macchina resta piena.

LA PROVA. La sessione resta aperta mentre il doctor misura: è lei il processo per
sessione. Controllo positivo: il doctor deve aver visto il daemon e almeno un server
MCP, altrimenti i due numeri sarebbero assenti e il verde non misurerebbe niente.

CHI LA CHIUDE: la riga `memory` del doctor, con psutil fra le dipendenze del pacchetto
(senza, il doctor dice «not measured»); per la sessione #162 (il giudice NLI nel daemon)
e #163 (il daemon dichiara la finestra da subito). Oggi: ROSSA, il doctor del wheel non
ha la riga.
"""
from __future__ import annotations

from conftest import json_di

FATTI = [
    ("Analytics runs on Postgres.",
     "We migrated the analytics store to Postgres last quarter."),
    ("The nightly backup runs at two in the morning.",
     "Ops note: the nightly backup job starts at two in the morning."),
]


def test_riga_7_il_doctor_stampa_quanto_costa_verimem(utente):
    with utente.mcp() as sessione:
        for fatto, fonte in FATTI:
            sessione.chiama("verimem_remember",
                            {"proposition": fatto, "source": fonte, "topic": "accettazione"})
        uscita = utente.cli("doctor", "--json")

    controlli = json_di(uscita)
    memoria = [c for c in controlli if c.get("name") == "memory"]
    assert memoria, "il doctor non dice quanto costa verimem alla macchina"
    riga = memoria[0]
    assert riga.get("fixed_mb") and riga.get("per_session_mb"), (
        f"CONTROLLO POSITIVO SPENTO: il doctor non ha misurato il daemon o la sessione "
        f"aperta, quindi i due numeri non dicono niente: {riga}")
    assert riga.get("status") == "ok", (
        f"verimem costa piu' di quanto promette: {riga.get('detail')}")
