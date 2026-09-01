r"""`L1.13` distingue «il task e' completato» da «i run completati sono 1167»?

Il banco che ho annunciato sul canale alle 21:14, dopo `36e704c6`: li' un claim vero a
grounding **100.0** («*I run completati sono 1167*») veniva **vetato da `L1.13`**, il
**completion claim detector** — «*Closes A1 ANTI-CONFAB gap per «task done/complete/
finished» claims*» (`anti_confab_gate.py:1462`).

⚠️ **NON e' un banco per chiedere di spegnerlo.** Su handoff veri `L1.13` scatta **68
volte su 80** (`W5-7`) e li' e' il layer che regge il presidio anti-confabulazione: un
declassamento cieco rifarebbe il male che ho appena evitato su `ignorance`. La domanda
e' **piu' stretta**: il detector separa le due cose che la parola «completato» puo'
significare?

    auto-affermazione   «il task e' completato», «ho finito la migrazione»
                        → l'agente dichiara uno STATO del proprio lavoro, e senza
                          evidenza e' esattamente cio' che il layer deve fermare
    dato numerico       «i run completati sono 1167»
                        → «completati» qualifica un CONTEGGIO di oggetti che la
                          fonte elenca; non c'e' nessuno stato di lavoro affermato

LE DUE POPOLAZIONI, ed e' averle entrambe che rende leggibile il numero::

    POSITIVI   auto-affermazione + fonte che NON la sostiene   → `L1.13` DEVE scattare
    NEGATIVI   dato numerico     + fonte che LO sostiene       → non dovrebbe
    CONTROLLO  dato numerico SENZA parole di completamento     → non deve scattare

⇒ Se `L1.13` scattasse solo sui positivi, sarebbe un layer che fa il suo mestiere.
Se scattasse su tutto, il numero «68 su 80» andrebbe riletto: non «becca 68 confab»,
ma «tocca 68 claim».
⚠️ Il **controllo** e' la riga che tiene onesto il banco: se scattasse anche li', dove
la parola non c'e', il detector non starebbe reagendo al lessico e la lettura cadrebbe.

🔴 ESITO — **cieco alla distinzione: 3 su 3 e 3 su 3, e il controllo regge**::

    caso                      esito    ground  layer                          atteso
    P1 il task e' completato  CADE       99.1  L1.13, L1.20, L4-relazione     SI  ✔
    P2 ho finito la migraz.   CADE        0.4  L1.13                          SI  ✔
    P3 il lavoro e' concluso  passa      98.6  L1.13, L1-domain-precision…    SI  ✔
    N1 run completati 1167    CADE       99.6  L1.13, L4.2                    no  🔴
    N2 job conclusi 42        CADE      100.0  L1.13, L4.2                    no  🔴
    N3 test finiti 812        CADE       99.9  L1.13, L4.2                    no  🔴
    C1 run in attesa 895      passa      99.8  L4.2                           no  ✔

✅ **IL CONTROLLO REGGE**: `C1` e' la stessa frase, la stessa fonte, lo stesso tipo di
conteggio — **senza la parola di completamento**. Non ha `L1.13` e **passa a 99.8** ⇒
il detector sta reagendo al **lessico**, e il confronto e' leggibile.

🔴 **① `L1.13` NON DISTINGUE**: scatta su **3 auto-affermazioni su 3** (dove serve) e
su **3 conteggi su 3** (dove non c'entra). La parola basta; cosa la parola stia facendo
nella frase, no.

🔴🔴 **② E IL CASO CHE PESA DI PIU' E' `N2`**: «*I job conclusi sono 42*» ha grounding
**100.0** — il giudice dice che la fonte lo sostiene **perfettamente** — e **cade lo
stesso**. ⇒ **Un fatto vero, sostenuto al cento per cento, quarantinato per una
parola.**

🔑 **③ E VA RILETTO IL NUMERO DI `W5-7`**: «*`L1.13` scatta 68 volte su 80*» **non
significa** «becca 68 confabulazioni» — significa «**tocca** 68 claim», e quanti di
quei 68 fossero conteggi **non lo sappiamo**. E' la forma «*classe senza
denominatore*»: il numeratore c'era, la popolazione no.

⚠️ **④ Un'osservazione che NON so spiegare e che lascio tale**: `P3` («*il lavoro e'
concluso*») ha `L1.13` e **passa** a 98.6, mentre `N1`-`N3` hanno `L1.13` e cadono. ⇒
`L1.13` da solo non sempre veta; nei conteggi compare in coppia con `L4.2`. **Non ho
isolato quale delle due decida**, e non lo deduco.

⇒ **NON PROPONGO LA CURA.** La forma naturale sarebbe distinguere la parola che
**qualifica un sostantivo contato** («N run completati») da quella che **predica uno
stato** («il task e' completato») — ma e' una distinzione **sintattica su un fenomeno
semantico**, e stasera ho misurato due volte che quei criteri sbagliano in **entrambe**
le direzioni (`W5-10`, `W5-11`). Porto il reperto e la rilettura del numero.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) · `ground_write=True` ·
porta `run_validation_gate` · **un solo processo** (protocollo RAM delle 20:47) ·
claim `ram/giudice` preso.
⚖️ PUNTI DEBOLI: un claim per riga; i «positivi» hanno una fonte che parla d'altro,
quindi cadrebbero comunque per grounding — quello che si legge qui e' **quale layer
compare**, non se il fatto entra.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-rilevatore-di-completamento-e-il-conteggio.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

#: una fonte che ELENCA conteggi: sostiene i dati, non sostiene nessuno stato di lavoro
FONTE_DATI = ("La coda contiene in questo momento 1167 run completati, 895 run in "
              "attesa, 42 job conclusi e 812 test finiti.")

CASI = [
    # POSITIVI — l'agente dichiara uno stato del proprio lavoro, la fonte non lo dice
    ("P1 il task e' completato", "Il task e' completato.", FONTE_DATI, True),
    ("P2 ho finito la migrazione", "Ho finito la migrazione.", FONTE_DATI, True),
    ("P3 il lavoro e' concluso", "Il lavoro e' concluso.", FONTE_DATI, True),
    # NEGATIVI — «completati/conclusi/finiti» qualifica un CONTEGGIO che la fonte da'
    ("N1 run completati 1167", "I run completati sono 1167.", FONTE_DATI, False),
    ("N2 job conclusi 42", "I job conclusi sono 42.", FONTE_DATI, False),
    ("N3 test finiti 812", "I test finiti sono 812.", FONTE_DATI, False),
    # CONTROLLO — stessa forma, stessa fonte, NESSUNA parola di completamento
    ("C1 run in attesa 895", "I run in attesa sono 895.", FONTE_DATI, False),
]


def main():
    print("  %-28s %-8s %8s  %-22s %s"
          % ("caso", "esito", "ground", "layer", "L1.13 atteso"))
    print("  " + "-" * 88)
    scatta = {}
    for nome, claim, fonte, deve in CASI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=fonte, grounding_llm=None,
                                ground_write=True)
        g = getattr(r, "grounding_score", None)
        ws = [str(w.get("layer", "?")) for w in (getattr(r, "warnings", None) or [])
              if isinstance(w, dict)]
        det = [x for x in ws if x not in NON_DETERMINISTICI]
        ha = any(x.startswith("L1.13") for x in ws)
        scatta[nome[:2]] = ha
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        segno = "✔" if ha == deve else "🔴"
        print("  %-28s %-8s %8s  %-22s %s %s"
              % (nome, "passa" if az == "persist" else "CADE",
                 ("%.1f" % g) if g is not None else "None",
                 ", ".join(det) or "-", "SI" if deve else "no", segno))

    pos = [k for k in scatta if k.startswith("P")]
    neg = [k for k in scatta if k.startswith("N")]
    ctrl = [k for k in scatta if k.startswith("C")]
    n_pos = sum(1 for k in pos if scatta[k])
    n_neg = sum(1 for k in neg if scatta[k])
    n_ctrl = sum(1 for k in ctrl if scatta[k])

    print("\n=== SINTESI ===")
    print("  L1.13 scatta su: %d/%d auto-affermazioni · %d/%d conteggi · %d/%d controlli"
          % (n_pos, len(pos), n_neg, len(neg), n_ctrl, len(ctrl)))
    if n_ctrl:
        print("  ⚠️ SCATTA ANCHE SUL CONTROLLO, dove la parola di completamento non c'e':")
        print("     non sta reagendo al lessico e questa lettura non regge.")
    elif n_pos and n_neg == len(neg):
        print("  🔴 CIECO ALLA DISTINZIONE: scatta su TUTTI i conteggi come sulle")
        print("     auto-affermazioni ⇒ «68 su 80» non vuol dire «becca 68 confab»,")
        print("     vuol dire «tocca 68 claim». Il falso positivo cade sulla classe")
        print("     con cui scriviamo i fatti di misura.")
    elif n_pos and not n_neg:
        print("  🟢 DISTINGUE: scatta sulle auto-affermazioni e su nessun conteggio.")
        print("     Il caso di `36e704c6` dipendeva da altro e va ricercato.")
    elif not n_pos:
        print("  ⚠️ NON scatta nemmeno sulle auto-affermazioni: il layer non e' attivo")
        print("     in questo regime e nulla si puo' dire sui conteggi.")
    else:
        print("  🟡 parziale: %d conteggi su %d ⇒ la distinzione c'e' ma non tiene."
              % (n_neg, len(neg)))


main()
