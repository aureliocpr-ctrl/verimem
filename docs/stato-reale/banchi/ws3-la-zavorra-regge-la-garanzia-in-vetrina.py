# -*- coding: utf-8 -*-
"""@ws4 ha misurato che una frase ESTRANEA puo' ribaltare un verdetto. Regge la mia riga?

Alle 21:30 @ws4 ha misurato (`aad97bcd`): claim fisso «Il lotto B12 e' conforme
alle specifiche», fonte che lo smentisce, e aggiungendo «La mensa aziendale
resta chiusa il primo maggio» il verdetto passa da `quarantined 1.8` a
`ammesso 98.9`. La sua tesi forte e' caduta — succede in 1 caso su 4, non 4 su
4 — ma ha nominato la conseguenza giusta: «**questo tocca le nostre misure
sulla contraddizione: erano fatte con fonti di UNA frase**».

⚠️ HA RAGIONE, E TOCCA UNA RIGA CHE HO SCRITTO IO IN VETRINA. Tutte le mie
batterie di stasera usano fonti di una frase, e su quelle la negazione da'
0/10 in IT e in EN. Quel numero e' nel README (commit c62da996): «a claim the
source **contradicts** does not come back as truth». **Se la zavorra lo
ribalta, la garanzia che ho pubblicato vale solo su fonti che nessuno scrive.**

DISEGNO — una variabile sola, il resto identico: gli STESSI dieci casi della
batteria negazione IT (`ws3-la-negazione-a-batteria-*`), in tre regimi::

    A  fonte NUDA, una frase          (gia' misurato: 0/10 ammesse)
    B  fonte + 1 frase ESTRANEA       (mensa, parcheggio, corso d'inglese)
    C  fonte + 3 frasi ESTRANEE       (la zavorra cresce)

Il nucleo che contraddice il claim resta IDENTICO e sempre presente in tutti e
tre. Cambia solo quanto testo irrilevante gli sta intorno.
🔑 Se B o C ammettono, il numero in vetrina va qualificato: non «una falsita'
che la fonte contraddice viene trattenuta», ma «…quando la fonte e' breve».
⚖️ Ogni regime porta anche i VERI: se la zavorra alzasse il grounding di tutto,
i veri resterebbero ammessi e i falsi pure — e allora non sarebbe una scoperta
sul gate, sarebbe una scoperta sul mio banco.
⛔ La zavorra e' ESTRANEA per costruzione: mensa, parcheggio, corso d'inglese.
Non ha niente a che vedere col contenuto dei casi. Se fosse pertinente
misurerei un'altra cosa.

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

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_zavorra_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

ZAVORRA_1 = " La mensa aziendale resta chiusa il primo maggio."
ZAVORRA_3 = (" La mensa aziendale resta chiusa il primo maggio."
             " Il corso d'inglese per i dipendenti comincia a ottobre."
             " Il parcheggio interno sara' riasfaltato durante l'estate.")

#: (nome, fonte_nuda, vero, falso)  — i dieci casi della batteria negazione IT
CASI = [
    ("rimborso",
     "Verbale: la richiesta di rimborso del reparto vendite non e' stata approvata.",
     "La richiesta di rimborso del reparto vendite non e' stata approvata.",
     "La richiesta di rimborso del reparto vendite e' stata approvata."),
    ("affitto",
     "Nota: il contratto di affitto del magazzino nord non e' stato rinnovato.",
     "Il contratto di affitto del magazzino nord non e' stato rinnovato.",
     "Il contratto di affitto del magazzino nord e' stato rinnovato."),
    ("terapia",
     "Referto: il paziente non ha risposto alla terapia antibiotica.",
     "Il paziente non ha risposto alla terapia antibiotica.",
     "Il paziente ha risposto alla terapia antibiotica."),
    ("fornitore",
     "Comunicazione: il fornitore Baldini non ha consegnato il lotto entro il termine.",
     "Il fornitore Baldini non ha consegnato il lotto entro il termine.",
     "Il fornitore Baldini ha consegnato il lotto entro il termine."),
    ("migrazione",
     "Rapporto: la migrazione a Postgres non e' stata completata nel trimestre.",
     "La migrazione a Postgres non e' stata completata nel trimestre.",
     "La migrazione a Postgres e' stata completata nel trimestre."),
    ("bilancio",
     "Verbale: il consiglio ha approvato il bilancio annuale.",
     "Il consiglio ha approvato il bilancio annuale.",
     "Il consiglio non ha approvato il bilancio annuale."),
    ("lotto",
     "Registro: il lotto B12 e' uscito dal deposito il 9 giugno.",
     "Il lotto B12 e' uscito dal deposito il 9 giugno.",
     "Il lotto B12 non e' uscito dal deposito il 9 giugno."),
    ("magazzino",
     "Atto: il magazzino di Rovigo e' stato venduto al signor Anselmi.",
     "Il magazzino di Rovigo e' stato venduto al signor Anselmi.",
     "Il magazzino di Rovigo non e' stato venduto al signor Anselmi."),
    ("servizio",
     "Nota tecnica: il servizio di pagamento e' tornato operativo lunedi mattina.",
     "Il servizio di pagamento e' tornato operativo lunedi mattina.",
     "Il servizio di pagamento non e' tornato operativo lunedi mattina."),
    ("accesso",
     "Protocollo: la richiesta di accesso agli atti e' stata accolta.",
     "La richiesta di accesso agli atti e' stata accolta.",
     "La richiesta di accesso agli atti non e' stata accolta."),
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
    print("%-11s %-10s %-12s %8s   %-12s %8s"
          % ("caso", "regime", "falso", "g", "vero", "g"))
    amm = {"A nuda": 0, "B +1": 0, "C +3": 0}
    rif = {"A nuda": 0, "B +1": 0, "C +3": 0}
    for (nome, nuda, vero, falso) in CASI:
        for reg, src in (("A nuda", nuda),
                         ("B +1", nuda + ZAVORRA_1),
                         ("C +3", nuda + ZAVORRA_3)):
            e_f, g_f, _ = esegui(falso, src)
            e_v, g_v, _ = esegui(vero, src)
            if e_f != "quarantined":
                amm[reg] += 1
            if e_v != "admitted":
                rif[reg] += 1
            print("%-11s %-10s %-12s %8s   %-12s %8s  %s"
                  % (nome, reg, e_f,
                     ("%.1f" % g_f) if g_f is not None else "-", e_v,
                     ("%.1f" % g_v) if g_v is not None else "-",
                     "<<< FALSITA' AMMESSA" if e_f != "quarantined" else ""))
        print()
    n = len(CASI)
    print("=" * 78)
    for reg in ("A nuda", "B +1", "C +3"):
        print("  %-8s  falsita' ammesse %2d/%d   VERI rifiutati %2d/%d"
              % (reg, amm[reg], n, rif[reg], n))
    print()
    print("  A=0 e B/C>0  -> la garanzia in vetrina vale solo su fonti brevi:")
    print("                  la riga del README va qualificata, ed e' mia.")
    print("  tutte a 0    -> la mia riga regge, e il caso di @ws4 e' un'altra cosa.")


if __name__ == "__main__":
    main_banco()
