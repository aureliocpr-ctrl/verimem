# -*- coding: utf-8 -*-
r"""Il traino NON scalfisce la cifra: 0/18 con e senza. `L4.1` e' l'unico strato che regge.

PREDIZIONE DICHIARATA PRIMA DI ESEGUIRE (sul canale, 18:32): il traino non deve
scalfire il numerico. Se `L4.1` e' un confronto deterministico sulle cifre, una
frase in piu' non ha niente da spostare — il traino compra il punteggio
SEMANTICO, e li' il punteggio non decide.

DA DOVE VIENE. Domanda posta da @ws3 dopo il suo banco
`ws3-la-seconda-garanzia-fuori-da-it-en.py` (commit «banco: la seconda garanzia
non degrada con la scrittura, si spezza sulla CIFRA»): il dettaglio numerico e'
fermato 18 su 18 da `L4.1`, il non numerico sfugge 16 su 18. La sua domanda:
**il traino ribalta anche i casi con la cifra?** Se lo scalfisse, quel 18/18 non
sarebbe solido.
Il traino e' il mio: una verita' PRESA DALLA FONTE messa accanto alla falsita' —
la leva che porta l'implicita da 3/10 a 6/10 in italiano e da 0/10 a 2/10 in
inglese (`ws5-il-traino-raddoppia-l-implicita.py`). Qui il traino e' la fonte
stessa, cioe' il massimo possibile.

⚠️ LA CELLA DI CONTROLLO NON E' UN ORNAMENTO: la colonna «senza traino» deve
riprodurre lo 0/18 di @ws3. Se non torna, sto misurando a un livello diverso dal
suo e l'incrocio non dice niente — la regola che ieri ha reso valido l'incrocio
sull'implicita, e che in questo repo ha gia' prodotto cinque ritiri in un giorno.

MISURATO 27/08, sei scritture, solo i casi A (numerici)::

    EN ZH JA KO AR HI    senza: colli=bloc voti=bloc assunti=bloc
                        TRAINO: colli=bloc voti=bloc assunti=bloc

    numerici ammessi senza   0/18   (L4.1 ha parlato su 18)
    numerici ammessi TRAINO  0/18   (L4.1 ha parlato su 18)

⇒ PREDIZIONE CONFERMATA, e la cella di controllo tiene: «senza» riproduce lo 0/18
di @ws3, quindi il livello e' il suo e il confronto vale. Il traino non sposta UN
caso su diciotto, e `L4.1` parla su 18/18 in ENTRAMBE le colonne — non e' che
qualcun altro raccoglie i cocci: e' sempre lui, con e senza zavorra.

⇒ IL GATE HA DUE STRATI INDIPENDENTI, e adesso si vede il confine::

    `L4.1`, deterministico sulle CIFRE   immune al traino, immune alla scrittura
                                         (6 alfabeti), regge 18/18
    il punteggio SEMANTICO               comprabile in QUATTRO modi misurati:
                                         ripetere la fonte · ricombinare i suoi
                                         token · il traino · il contorno neutro

⚠️ E LA CONSEGUENZA NON E' RASSICURANTE, perche' i due strati non si coprono a
vicenda: dove c'e' una cifra il gate regge in sei scritture; dove non c'e', il
non numerico sfugge 16 su 18 (@ws3) e il punteggio che dovrebbe fare da rete si
compra in quattro modi diversi. **Non e' un gate con un punto debole: e' un gate
con UN punto forte.** La superficie protetta non e' una lingua ne' un dominio —
e' la presenza di un numero da confrontare.

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

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-traino-contro-la-cifra.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
"""
import importlib.util
import os
import sys

if len(sys.argv) < 2:
    raise SystemExit("uso: %s <dir-temporanea>" % sys.argv[0])
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

_BANCO_WS3 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "ws3-la-seconda-garanzia-fuori-da-it-en.py")
_spec = importlib.util.spec_from_file_location("_banco_ws3", _BANCO_WS3)
_wb = importlib.util.module_from_spec(_spec)
sys.modules["_banco_ws3"] = _wb
try:
    _spec.loader.exec_module(_wb)
except SystemExit:
    #: il banco di @ws3 esce da solo se invocato senza argomenti: a noi serve
    #: solo la sua tabella CASI, che a quel punto e' gia' definita.
    pass

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402


def _ammesso(claim, source):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=source, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    return (getattr(r, "action", "?") == "persist",
            g if isinstance(g, (int, float)) else -1.0, ws)


def main() -> None:
    tot = {"senza": [0, 0], "TRAINO": [0, 0]}
    l41 = {"senza": 0, "TRAINO": 0}
    print("")
    for lg, casi in _wb.CASI.items():
        riga = {}
        for classe, nome, fonte, claim in casi:
            if classe != "A":          #: solo i NUMERICI: e' la colonna che regge
                continue
            for eti, c in (("senza", claim), ("TRAINO", fonte + " " + claim)):
                ok, g, ws = _ammesso(c, fonte)
                tot[eti][0] += int(ok)
                tot[eti][1] += 1
                if any(str(w).startswith("L4.1") for w in ws):
                    l41[eti] += 1
                riga.setdefault(eti, []).append((nome, ok, g))
        if not riga:
            continue
        print("   %-4s  senza: %s      TRAINO: %s"
              % (lg,
                 " ".join("%s=%s" % (n, "AMM" if ok else "bloc") for n, ok, _ in riga["senza"]),
                 " ".join("%s=%s" % (n, "AMM" if ok else "bloc") for n, ok, _ in riga["TRAINO"])))
    print("")
    for eti in ("senza", "TRAINO"):
        print("   numerici ammessi %-7s %d/%d   (L4.1 ha parlato su %d)"
              % (eti, tot[eti][0], tot[eti][1], l41[eti]))


if __name__ == "__main__":
    main()
