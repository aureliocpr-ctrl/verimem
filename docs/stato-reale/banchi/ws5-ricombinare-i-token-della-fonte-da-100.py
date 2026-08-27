# -*- coding: utf-8 -*-
r"""Scambiare la CITTA' con la PERSONA dentro la fonte da' 100.0.

    fonte  «Il magazzino di Ancona misura 2600 mq. Il responsabile e' Mancini.»
    claim  «Il responsabile e' ANCONA e il magazzino di MANCINI misura 2600 mq.»
    esito  persist, g=100.0

Non c'e' una verita' che accompagna, come nel caso a 92.3 di
`tests/test_una_falsita_in_compagnia_non_deve_passare.py`: qui NON c'e' NESSUNA
verita'. Sono due affermazioni, entrambe false, entrambe assurde — una citta' che
fa il responsabile e una persona che possiede un magazzino — e il giudice risponde
«la fonte lo sostiene» col punteggio pieno.
Lo stesso dominio, con UN token nuovo al posto della ricombinazione, e' bloccato::

    magazzini  RICOMBINATO (Ancona<->Mancini)   persist    g= 100.0
    magazzini  token NUOVO (Bologna)            downgrade  g=   1.1

DA DOVE VIENE. Era l'asimmetria dichiarata NON spiegata nel docstring di
`test_una_falsita_in_compagnia_non_deve_passare.py`: nel dominio dei test una
falsita' passa anche con un valore assente dalla fonte, nei magazzini no. Due
ipotesi provate e FALSIFICATE prima di questa, e le lascio scritte perche' nessuno
le ripercorra::

    ① «e' il NUMERO»  — magazzini SENZA numero resta a 1.1 e cade per
                        L4-grounding, non per L4.1: L4.1 era additivo, non causale
    ② «e' la FORMA»   — test LISTA 100.0 vs prosa 99.9; magazzini LISTA 5.0 vs
                        prosa 1.1: a contenuto fisso la forma non sposta niente

⇒ ③ LA RICOMBINAZIONE E' SUFFICIENTE MA NON NECESSARIA, e l'A/B lo dice nelle DUE
direzioni — che e' il motivo per cui sono quattro celle e non due::

    test       RICOMBINATO (beta<-alpha)        persist    g= 100.0
    test       token NUOVO (gamma)              persist    g=  99.8
    magazzini  RICOMBINATO (Ancona<->Mancini)   persist    g= 100.0
    magazzini  token NUOVO (Bologna)            downgrade  g=   1.1

Nei magazzini la ricombinazione SALE da 1.1 a 100.0: e' sufficiente. Nel dominio
dei test un token nuovo NON fa scendere (99.8): non e' necessaria. ⇒ Ricombinare i
token della fonte basta a comprare il punteggio pieno, ma nel dominio dei test si
prende il punteggio pieno anche senza.

⚠️ QUELLO CHE RESTA APERTO, e lo dichiaro invece di chiuderlo a parole: PERCHE' il
dominio dei test ammetta anche `test_gamma`, che nella fonte non c'e', questo banco
NON lo dice. L'asimmetria e' spiegata a meta': ho la causa del lato magazzini
(ricombinazione) e non quella del lato test.

⇒ TESI, e si salda con `ws5-il-traino-raddoppia-l-implicita.py`: il CE misura
quanto il claim ATTINGE dalla fonte, non quanto la fonte lo IMPLICA. Il caso a
92.3 comprava il punteggio con una verita' presa dalla fonte; qui si vede che non
serve nemmeno una verita' — bastano i TOKEN. La forma piu' pura del difetto:
zero parole nuove, zero affermazioni vere, punteggio pieno.

IN QUALE REGIME VALGONO QUESTI NUMERI — e perche' la domanda non e' pedanteria.
@ws3 ha misurato che togliere una guardia dalla RIGA DI COMANDO non e' toglierla
dall'AMBIENTE: credeva di misurare senza `PYTHONUTF8=1` e rimisurava lo stesso
regime, perche' la variabile e' esportata a livello di macchina. Questo banco gira
su una macchina che ha DIECI variabili che la CI non ha::

    ENGRAM_ADMISSION_GATE=1        ENGRAM_DATA_DIR=~\.engram
    ENGRAM_BRIEFING_MIN_MATCHED=4  ENGRAM_BRIEFING_THRESHOLD=0.40
    ENGRAM_DECAY_ENABLED=1         ENGRAM_TELEMETRY_PREFIXES=builtin
    HIPPO_DATA_DIR=~\.engram       HIPPO_ENCODE_DELEGATE_ONLY=1
    HIPPO_EXPOSE_TOOLS=...         PYTHONUTF8=1

✅ NESSUNA di queste e' letta da `anti_confab_gate.py`, che e' la porta chiamata
qui. Verificato guardando DA QUALE FILE ognuna e' letta, non a intuito::

    ENGRAM_ADMISSION_GATE      -> admission_gate.py, semantic.py
    HIPPO_ENCODE_DELEGATE_ONLY -> _compat.py, embedding.py
    ENGRAM_DECAY_ENABLED       -> daemon_runner.py
    ENGRAM_BRIEFING_*          -> briefing.py, mcp_server.py
    ENGRAM_TELEMETRY_PREFIXES  -> admission_cleanup.py, admission_gate.py

⚠️ Per un attimo questo e' sembrato un GUAIO invece di una rassicurazione: se
`ENGRAM_ADMISSION_GATE` vive in un modulo diverso, il sospetto e' che qui si stia
misurando UNO STRATO SOTTO la porta vera — l'errore che in questo repo e' costato
cinque ritiri in un giorno.
✅ NON lo e': `verimem/cli.py:1867` chiama `run_validation_gate`, e cosi'
`client.py:529` (SDK) e `mcp_server.py`. **La CLI usa esattamente questa porta.**
⇒ Il controllo utile non e' «togli la variabile e rimisura»: e' **«da quale file e'
letta, e quel file sta sulla strada del prodotto?»**. Due grep, e rispondono a
entrambe le domande — il regime E il livello.
⛔ Le due variabili di percorso (`*_DATA_DIR`) sono comunque sovrascritte in testa
a questo file con la dir temporanea passata da riga di comando: lo store
principale non viene mai toccato.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-ricombinare-i-token-della-fonte-da-100.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
"""
import os
import sys

if len(sys.argv) < 2:
    raise SystemExit("uso: %s <dir-temporanea>" % sys.argv[0])
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

SRC_TEST = "   test_alpha PASSED\n   test_beta SKIPPED"
SRC_MAG = "Il magazzino di Ancona misura 2600 mq. Il responsabile e' Mancini."

#: (dominio, etichetta, claim, fonte) — le quattro celle dell'A/B a due direzioni.
CASI = [
    ("test", "RICOMBINATO (beta<-alpha)",
     "Il test_alpha e PASSED e il test_beta e PASSED.", SRC_TEST),
    ("test", "token NUOVO (gamma)",
     "Il test_alpha e PASSED e il test_gamma e PASSED.", SRC_TEST),
    ("magazzini", "RICOMBINATO (Ancona<->Mancini)",
     "Il responsabile e' Ancona e il magazzino di Mancini misura 2600 mq.", SRC_MAG),
    ("magazzini", "token NUOVO (Bologna)",
     "Il responsabile e' Mancini e il magazzino e' a Bologna.", SRC_MAG),
]


def main() -> None:
    print("")
    for dom, tipo, claim, src in CASI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None,
                                ground_write=True)
        g = getattr(r, "grounding_score", None)
        gs = ("%.1f" % g) if isinstance(g, (int, float)) else str(g)
        print("%-10s %-32s %-10s g=%6s"
              % (dom, tipo, getattr(r, "action", "?"), gs))


if __name__ == "__main__":
    main()
