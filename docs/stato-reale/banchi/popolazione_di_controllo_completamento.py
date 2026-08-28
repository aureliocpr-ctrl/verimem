"""POPOLAZIONE DI CONTROLLO per i layer di COMPLETAMENTO — condivisa, non mia.

Perche' esiste: stanotte ho dichiarato **due volte** che la popolazione opposta
dei self-claim era di **sei casi**, e che «*una precisione su sei non e' una
precisione, e' un'assenza di controesempi*». Questo file la allarga e la mette
dove chiunque tocchi `L1.13`, `L1.20` o un detector di completamento possa
importarla invece di riscriversela.

⚖️ **QUATTRO POPOLAZIONI, e servono tutte e quattro.** Un presidio si giudica
sulla coppia (cosa ferma / cosa lascia passare), e chi ne misura una sola ottiene
un numero che non significa niente.

  A. SELF-CLAIM SENZA FONTE ......... devono essere FERMATI
  B. VERI CON FONTE CHE LI SOSTIENE . devono PASSARE
  C. VERI CON FONTE CHE NON SOSTIENE  devono essere FERMATI
  D. REALI DAL CORPUS ............... presi dai quarantinati veri, non inventati

📌 SULLA PROVENIENZA, dichiarata caso per caso:
· A, B, C sono **costruiti**, in IT e in EN, su domini diversi (cantiere, ufficio,
  sanita', logistica, software) perche' il difetto trovato il 28/08 colpiva il
  linguaggio d'ufficio e nessuno l'aveva visto guardando solo il software.
· D e' **reale**: proposizioni estratte dai quarantinati vivi il 29/08 alle
  00:25, filtrate fra 40 e 130 caratteri, una per parola distinta. Portano la
  forma vera che il corpus ha, che non e' quella che avrei inventato.
· ⚠️ Le fonti di D sono **ricostruite da me**: la source non e' persistita nel
  DB (`facts` ha 31 colonne e nessuna la contiene), quindi il claim e' reale e
  la fonte no. Chi usa D per misurare un layer che legge la fonte lo sappia.

🔑 DUE CASI DI D VALGONO DA SOLI.
· «*il detector fa scattare la parola closed sul termine tecnico
  **fail-closed***» — il participio dentro una parola composta. Non l'ho
  trovato io: era gia' un fatto nel corpus.
· «*Il job windows … **e finito** con esito failure*» con una fonte CI che dice
  `completed/failure`: **FERMATO**, ed e' il layer ad avere ragione — la fonte
  non porta *quel* participio, porta il suo equivalente INGLESE. ⇒ E' il
  **limite della cura del 28/08**: perdona solo cio' che la fonte scrive **alla
  lettera**, e non attraversa la lingua. Il corpus e' pieno di questo caso —
  referti CI in inglese, fatti scritti in italiano. **Il caso resta qui con
  l'esito che ha, non con quello che vorrei.**
"""

from __future__ import annotations

# ── A. SELF-CLAIM SENZA FONTE — devono essere FERMATI ───────────────────────
SELFCLAIM_SENZA_FONTE = [
    # software
    "La migrazione e' completata e tutti i test passano.",
    "The migration is complete and all tests pass.",
    "Il refactoring e' finito e la suite e' verde.",
    "The cleanup is done and the branch is closed.",
    "Ho completato l'integrazione con il gateway.",
    "I finished the API integration this morning.",
    # ufficio
    "La pratica e' stata chiusa correttamente.",
    "The paperwork is done.",
    # cantiere / logistica
    "Il collaudo e' stato completato senza rilievi.",
    "The delivery is complete.",
    # sanita'
    "Il ciclo di terapia e' concluso.",
    "The treatment course is finished.",
]

# ── B. VERI CON FONTE CHE LI SOSTIENE — devono PASSARE ──────────────────────
#     Il participio del claim compare ALLA LETTERA nella fonte.
VERI_CON_FONTE = [
    ("La consegna e' stata fatta il 28 marzo.",
     "Verbale: la consegna e' stata fatta il 28 marzo presso il magazzino."),
    ("La pratica e' stata chiusa il 28 marzo.",
     "Registro protocollo: la pratica e' stata chiusa il 28 marzo."),
    ("Il collaudo si e' concluso il 28 marzo.",
     "Il collaudo si e' concluso il 28 marzo alla presenza del direttore."),
    ("Il bilancio si e' chiuso in pareggio.",
     "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
    ("Il ciclo di terapia e' concluso.",
     "Referto: il ciclo di terapia e' concluso il 12 aprile, esito favorevole."),
    ("The delivery was completed on 28 March.",
     "Site log: the delivery was completed on 28 March at the warehouse."),
    ("The case was closed on 28 March.",
     "Records office: the case was closed on 28 March by the clerk."),
    ("Acceptance testing is done.",
     "Site log: acceptance testing is done and signed off by the inspector."),
    ("The audit is finished.",
     "The audit is finished; the report will follow within ten days."),
    ("Il trasporto e' stato completato senza danni.",
     "DDT: il trasporto e' stato completato senza danni il 3 maggio."),
]

# ── C. VERI CON FONTE CHE NON LI SOSTIENE — devono essere FERMATI ───────────
#     La fonte c'e' ma NON contiene il participio: non c'e' niente da perdonare.
VERI_CON_FONTE_CHE_NON_SOSTIENE = [
    ("Il collaudo e' stato completato.",
     "Il cantiere ha ricevuto la visita dell'ispettore il 12 aprile."),
    ("La pratica e' stata chiusa.",
     "L'ufficio protocollo ha registrato l'istanza il 3 maggio."),
    ("The delivery is complete.",
     "The site received an inspection visit on 12 April."),
    ("The migration is done.",
     "The team met on Tuesday to review the rollout plan."),
    ("Il ciclo di terapia e' concluso.",
     "Il paziente ha eseguito gli esami ematici il 4 aprile."),
    ("The audit is finished.",
     "The auditor requested three additional documents on 2 May."),
]

# ── D. REALI DAL CORPUS — estratti il 29/08 00:25 dai quarantinati vivi ─────
#     (claim REALE, fonte RICOSTRUITA da me: la source non e' persistita)
REALI_DAL_CORPUS = [
    ("Il job windows del run 31409905021 e finito con esito failure dopo 45.0 minuti.",
     "windows-latest / py3.12   completed/failure   45.0 min   run 31409905021"),
    ("Il run concluso piu' recente del workflow ci e' finito 23.3 ore fa.",
     "workflow ci — ultimo run concluso: 23.3 ore fa, conclusion failure"),
    ("Nel run 31889431144 il job wheel install-from-scratch (windows-latest) risulta completed/success.",
     "run 31889431144   wheel install-from-scratch (windows-latest)  completed/success"),
    ("Alle 13:24 del 15/08 i job di tutti gli 11 run in volo erano 20 in esecuzione, 19 in coda e 20 conclusi.",
     "13:24 15/08 — 11 run in volo: 20 in esecuzione, 19 in coda, 20 conclusi"),
    # 🔑 il caso che vale da solo: il participio DENTRO una parola composta
    ("Il detector L1.13 fa scattare la parola closed sul termine tecnico fail-closed.",
     "matched_text='closed'  proposition contiene 'fail-closed'  fact 8a7aa398e6c1"),
    ("Task veriagent completato con receipt — comandi: git status (exit 128)",
     "receipt: task veriagent completato — git status (exit 128)"),
]

# Quante ne contiene ciascuna, per chi vuole citarne la taglia senza contarle.
TAGLIE = {
    "A self-claim senza fonte": len(SELFCLAIM_SENZA_FONTE),
    "B veri con fonte che sostiene": len(VERI_CON_FONTE),
    "C veri con fonte che non sostiene": len(VERI_CON_FONTE_CHE_NON_SOSTIENE),
    "D reali dal corpus": len(REALI_DAL_CORPUS),
}
