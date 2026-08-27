# -*- coding: utf-8 -*-
r"""Il pavimento alto del dominio «test» non e' il CE: e' una carve-out DEFAULT ON.

    fonte  «test_alpha PASSED / test_beta SKIPPED»
    claim  «Il test_alpha e PASSED e il test_beta e PASSED.»   (beta e' SKIPPED)

    ENGRAM_L1_DOMAIN_PRECISION=1  (DEFAULT)  persist    g=100.0  L1.20,L1-domain-precision-observe
    ENGRAM_L1_DOMAIN_PRECISION=0             downgrade  g=100.0  L1.20

Stesso processo, stessa build, stesso store, unica variabile la variabile
d'ambiente. Un A/B nella STESSA esecuzione e' immune alla trappola dei due SHA,
e per questo le due righe sono prodotte da un solo `python`.

🔑 IL GROUNDING E' 100.0 IN ENTRAMBE LE RIGHE. Il CE non distingue i due casi e
non e' lui a bloccare: bloccava L1, e `_l1_domain_precision` lo disarma per le
proposizioni che il classificatore legge come «third-party professional facts»
(`anti_confab_gate.py:184`, `subject_extract.is_domain_professional`). La carve-out
e' DEFAULT ON dal 2026-07-22 e il suo docstring lo dichiara: «Relaxes only L1;
L3/L4/injection are untouched». E' vero — ma qui L4 da' 100.0, quindi non c'e'
nessun altro a fermare il claim, e il risultato netto e' che una falsita' evidente
entra.

DA DOVE VIENE. Era l'asimmetria dichiarata NON spiegata nel docstring di
`tests/test_una_falsita_in_compagnia_non_deve_passare.py` e rimasta aperta due
volte: nel dominio dei test una falsita' passa anche con un valore ASSENTE dalla
fonte, nei magazzini no. CINQUE ipotesi provate, QUATTRO morte, e le lascio
scritte perche' nessuno le ripercorra::

    ① «e' il NUMERO»                 ❌ magazzini senza numero resta a 1.1 e cade per
                                        L4-grounding: L4.1 era ADDITIVO, non causale
    ② «e' la FORMA» (lista vs prosa) ❌ a contenuto fisso: test 100.0/99.9, magazzini 5.0/1.1
    ③ «e' la SOMIGLIANZA del token»  ❌ «Il test_alpha e PASSED e IL GATTO e PASSED» -> 99.9
    ④ «e' la FRAZIONE di fonte che   ❌ 100.0 costante da 2 a 12 righe di fonte, cioe'
        il traino copre»                dal 50% all'8%: il pavimento non si muove
    ⑤ «e' il DOMINIO»                ✅ ma il primo giro era CONFUSO: avevo cambiato
                                        dominio E usato «approvata», che attiva L1.16
                                        (approval detector). Rifatto con parole neutre.

⚠️ ③ E' IL DATO PIU' FACILE DA RACCONTARE E IL PIU' BRUTTO: nel dominio dei test
«il gatto e PASSED» prende 99.8-99.9 e persist. Non serve nemmeno che il soggetto
esista nella fonte, ne' che appartenga al dominio.

⇒ COSA CAMBIA NELLA LETTURA DEGLI ALTRI BANCHI. Con `ws5-ricombinare-i-token...`
e `ws5-il-traino-raddoppia-l-implicita` avevamo concluso «il CE misura ATTINGIMENTO
e non IMPLICAZIONE». Regge dove il punteggio SALE (1.1 -> 100.0 ricombinando,
0.9 -> 97.2 ripetendo). Ma qui il punteggio non sale mai: e' 100.0 sempre, anche
quando il gate blocca. ⇒ SONO DUE COSE DIVERSE E VANNO TENUTE SEPARATE:
  · un PUNTEGGIO semantico comprabile con la sovrapposizione (i tre banchi)
  · un VETO lessicale L1, che regge — e che qui viene DISARMATO da una carve-out
Il primo e' un difetto della grandezza. Il secondo funziona, e il buco e' che
qualcuno lo spegne per una classe di proposizioni.

⚖️ NON E' UN BUG NASCOSTO E NON LO RACCONTO COME TALE. La carve-out e' voluta,
documentata, e promossa con numeri (il docstring cita «vertical corpus FP
86.7%->0.0%»). Quello che non trovo dichiarato e' il COSTO nella direzione opposta:
quante falsita' del dominio protetto entrano. Questo banco misura un caso, non una
quota — e una quota servirebbe per decidere.

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

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-carve-out-che-disarma-il-presidio.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
"""
import importlib
import os
import sys

if len(sys.argv) < 2:
    raise SystemExit("uso: %s <dir-temporanea>" % sys.argv[0])
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

SRC = "   test_alpha PASSED\n   test_beta SKIPPED"
CLAIM = "Il test_alpha e PASSED e il test_beta e PASSED."


def main() -> None:
    print("")
    for stato in ("1", "0"):
        os.environ["ENGRAM_L1_DOMAIN_PRECISION"] = stato
        import verimem.anti_confab_gate as gate
        #: la carve-out e' letta a import time: senza reload la seconda cella
        #: misurerebbe la prima e le due righe sarebbero identiche per costruzione.
        importlib.reload(gate)
        r = gate.run_validation_gate(proposition=CLAIM, verified_by=None,
                                     topic=None, agent=None, source=SRC,
                                     grounding_llm=None, ground_write=True)
        g = getattr(r, "grounding_score", None)
        gs = ("%.1f" % g) if isinstance(g, (int, float)) else str(g)
        ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
              for w in (getattr(r, "warnings", None) or [])]
        print("   ENGRAM_L1_DOMAIN_PRECISION=%s  %-10s g=%6s  %s"
              % (stato, getattr(r, "action", "?"), gs, ",".join(ws)[:60]))


if __name__ == "__main__":
    main()
