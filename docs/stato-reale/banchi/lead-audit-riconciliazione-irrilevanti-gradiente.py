# -*- coding: utf-8 -*-
"""RICONCILIAZIONE ws3 (423f71d7) vs banco D lead-audit (ef234ae0) — 29/08 sera.

I due banchi misurano la stessa classe (fonte che NON dice il claim) con esiti
opposti: gli irrilevanti di ws3 prendono 81,4-94,4 dal giudice (uno ENTRA), il
D5 mio prendeva 0,29. Una variabile nascosta li separa. Le fonti di ws3 la
suggeriscono ma non la isolano: i suoi irrilevanti alti condividono il
SOGGETTO con la fonte («il server alfa...»), il mio D5 no — pero' il suo
«Genova ha un aeroporto» condivide il soggetto E prende 1,9.

GRADIENTE a variabile singola sul caso server (la fonte verbatim di ws3):
  G1  il suo irrilevante verbatim (atteso ~81 come da suo esito)
  G2  stesso predicato, SOGGETTO diverso («il server beta») -> se crolla, la
      variabile e' il soggetto condiviso
  G3  stesso soggetto, predicato di un ALTRO CAMPO semantico («ha vinto un
      premio di cucina») -> se resta alto, il soggetto basta; se crolla, conta
      anche il campo del predicato
  G4  il mio D5 verbatim (controllo di continuita' col banco D: atteso ~0,3)

Attesa dichiarata PRIMA: G2 e G3 sotto 30 se la variabile dominante e' il
soggetto condiviso; G3 alto e G2 basso se il CE lega al solo soggetto.

    python -u docs/stato-reale/banchi/lead-audit-riconciliazione-irrilevanti-gradiente.py
"""

from __future__ import annotations

FONTE_WS3 = ("Nel trimestre il server alfa ha avuto una disponibilita' "
             "superiore al 95 per cento, misurata dal sistema di "
             "monitoraggio interno.")

CASI = [
    ("G1 verbatim ws3",
     "Il server alfa e' ospitato in un data center tedesco.", FONTE_WS3),
    ("G2 soggetto diverso",
     "Il server beta e' ospitato in un data center tedesco.", FONTE_WS3),
    ("G3 campo diverso",
     "Il server alfa ha vinto un premio di cucina.", FONTE_WS3),
    ("G4 D5 verbatim (controllo)",
     "La migrazione risulta in stato terminale dal 12 aprile e nessun "
     "passo resta aperto.",
     "Il magazzino ha ricevuto la visita dell'ispettore il 3 maggio."),
]


def main() -> int:
    from verimem.anti_confab_gate import run_validation_gate
    print("  porta: run_validation_gate(..., ground_write=True), agent=None")
    for nome, claim, fonte in CASI:
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=fonte, ground_write=True)
        layers = [str((w or {}).get("layer") or "") for w in g.warnings]
        print(f"  {nome:<28} action={g.action:<9} "
              f"grounding={g.grounding_score and round(g.grounding_score,1)} "
              f"layers={layers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
