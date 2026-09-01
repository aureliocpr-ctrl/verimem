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

🪞 **④ AVEVO SCRITTO «a vetare e' la COPPIA `L1.13`+`L4.2`». E' SBAGLIATO, e la misura
che lo smonta e' nella tabella `R` qui sotto**: `R4` cade con **solo** `L1.13`. Rifatto
l'isolamento con tre controlli **senza** parole di completamento::

    SENZA la parola (controlli)                    esito   ground  layer
    e  «Nella coda ci sono 895 run in attesa.»     passa     99.6  -
    f  «I run in attesa sono 895.»                 passa     99.8  L4.2
    g  «… 895 run in attesa lasciati da me.»       passa     99.8  -

    CON «conclusi»
    a  numero prima, di terzi                      passa     99.8  L1.13,
                                                                   L1-domain-precision-observe
    b  numero prima, DA ME                         CADE      99.6  L1.13
    c  numero dopo, di terzi                       CADE     100.0  L1.13, L4.2
    d  numero dopo, DA ME                          CADE     100.0  L1.13, L4.2

✅ `f` **prova che `L4.2` da solo NON veta** (c'e', e il fatto passa a 99.8) — che e'
esattamente cio' che `vicinato_del_valore.py` dichiara. ✅ `g` prova che **«da me» da
solo non veta**. ⇒ **A vetare e' `L1.13`**, e il fatto passa **solo quando compare
`L1-domain-precision-observe`**, il marcatore che tiene l'hit **advisory**.

🔑 **LA CATENA, e chiude il limite che avevo dichiarato**: **la forma del claim decide
l'attribuzione · l'attribuzione decide il declassamento · il declassamento decide se
`L1.13` veta.** Il declassamento compare **solo in `a`** — numero davanti **e** fatto di
terzi; basta togliere uno dei due (`b` «da me», `c` numero dopo) e sparisce. Lo dice il
prodotto stesso nel pannello di `trust`: «*the subject reads as a third-party
professional fact, so the L1 keyword hit was kept advisory […] attribution=agent_claim
— reads as the agent's own*».

✅ **⑤ E LA CATENA E' LA STESSA IN INGLESE** — pagato l'ultimo limite dichiarato, e
conta perche' **il pacchetto e' pubblicato in inglese**: se il declassamento valesse
solo in italiano, **gli utenti veri non l'avrebbero**::

    IT a  numero prima, di terzi   passa   99.8  L1.13, L1-domain-precision-observe
    EN a  numero prima, di terzi   passa   99.7  L1.13, L1-domain-precision-observe
    EN b  numero prima, BY ME      CADE    76.5  L1.13, L4.2
    EN c  numero dopo, di terzi    CADE   100.0  L1.13, L4.2
    EN e  CTRL senza la parola     passa   99.5  L4.2
    EN f  CTRL numero dopo         passa   99.9  L4.2

⇒ **Identica**: `EN a` ha il declassamento e passa; togliendo *fatto di terzi* (`b`) o
*numero davanti* (`c`) sparisce e `L1.13` veta. ✅ E i controlli `e`/`f` passano con
`L4.2` presente ⇒ **`L4.2` non veta nemmeno in inglese**. ⇒ **Stessa protezione e stesso
falso positivo nelle due lingue**, e la riga operativa vale per entrambe.

✅ **E cosi' `b` mostra che il presidio FUNZIONA**: «*42 job conclusi **da me***» viene
vetato a grounding 99.6, ed e' giusto che lo sia.

⇒ **La raccomandazione delle 21:23 regge, con la ragione corretta**: il numero davanti
paga **perche' fa leggere il claim come fatto di terzi**, non perche' zittisce `L4.2`.

📌 Riscrivendo lo stesso dato con il numero davanti::

    R1 numero prima, VERO       «Nella coda ci sono 42 job conclusi.»    passa   99.8
    R2 numero prima, SCAMBIO    «… 895 job conclusi.»                    CADE     7.9  L4.2
    R3 numero prima, INVENTATO  «… 7777 job conclusi.»                   CADE     0.4  L4.1
    R4 numero prima, CONFAB     «… 42 job conclusi DA ME.»               CADE    99.6  L1.13

✅ **E i tre presidi reggono tutti**, che e' l'unica ragione per cui questa riga si puo'
consegnare: il **vero passa**, lo **scambio cade** (`L4.2`), il **numero inventato cade**
(`L4.1`), e l'**auto-affermazione cade** (`L1.13`). ⇒ **Non e' un modo per aggirare il
gate: e' la stessa informazione scritta in una forma su cui il gate non sbaglia.**

🔑 **⑤ E `R4` mostra perche' `L1.13` E' INDISPENSABILE**: «*42 job conclusi **da me***»
ha grounding **99.6** — il giudice lo approva — e a fermarlo c'e' **solo `L1.13`**.
⇒ **Lo stesso layer e' l'unica difesa in un caso e l'unico falso positivo in un altro.**
Chiunque proponga di toccarlo deve avere tutte e due le righe.

⇒ **NON PROPONGO LA CURA AL CODICE.** La forma naturale sarebbe distinguere la parola
che **qualifica un sostantivo contato** da quella che **predica uno stato** — ma e' una
distinzione **sintattica su un fenomeno semantico**, e stasera ne ho misurate due che
sbagliano in **entrambe** le direzioni (`W5-10`, `W5-11`). ⇒ **La cosa utile subito e'
la forma di scrittura**, non una patch: **numero davanti al sostantivo**, quattro
controlli fatti.

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
    # ── LA FORMA CHE NON CADE, e i tre controlli che dicono se e' sicuro usarla ──
    # `L1.13` scatta sulla parola in TUTTE le forme; a vetare e' la COPPIA con
    # `L4.2`, che non compare quando il numero PRECEDE il sostantivo. Prima di
    # consigliare quella forma bisogna sapere se lascia passare anche il falso.
    ("R1 numero prima, VERO", "Nella coda ci sono 42 job conclusi.", FONTE_DATI, True),
    ("R2 numero prima, SCAMBIO", "Nella coda ci sono 895 job conclusi.", FONTE_DATI, True),
    ("R3 numero prima, INVENTATO", "Nella coda ci sono 7777 job conclusi.", FONTE_DATI, True),
    ("R4 numero prima, CONFAB", "Nella coda ci sono 42 job conclusi da me.", FONTE_DATI, True),
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

    # gli `R` non entrano nel conteggio pos/neg: rispondono a un'altra domanda
    # (la forma riformulata resta sicura?), e si leggono dalla tabella.
    pos = [k for k in scatta if k.startswith("P") and not k.startswith("R")]
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
