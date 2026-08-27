# -*- coding: utf-8 -*-
r"""L'unico punto forte del gate si aggira scrivendo il numero A PAROLE: 0/6 contro 6/6.

    CIFRA    ammessi 0/6   L4.1 ha parlato su 6/6
    LETTERE  ammessi 6/6   L4.1 ha parlato su 0/6

    EN   CIFRA=bloc   LETTERE=AMMESSO (senza L4.1)
    IT   CIFRA=bloc   LETTERE=AMMESSO (senza L4.1)
    ZH   CIFRA=bloc   LETTERE=AMMESSO (senza L4.1)      340箱 -> 三百四十箱
    JA   CIFRA=bloc   LETTERE=AMMESSO (senza L4.1)      340個 -> 三百四十個

Separazione totale, quattro scritture su quattro, ideogrammi compresi. E `L4.1`
non parla MAI sulla forma in lettere: non e' che parla e si sbaglia — non vede
proprio che c'e' un numero.

DA DOVE VIENE, e la catena conta perche' nessuno dei tre pezzi da solo lo diceva:
  · @ws3 ha misurato che il dettaglio NUMERICO e' fermato 18/18 da `L4.1` mentre
    il non numerico sfugge 16/18 ⇒ «l'asse non e' la lingua, e' la cifra».
  · io ho verificato che il TRAINO non scalfisce quel 18/18
    (`ws5-il-traino-contro-la-cifra.py`): l'unico strato che regge, regge davvero.
  · restava una sola domanda: e se il numero non e' scritto in cifra?

⚠️ NON E' UNA SCOPERTA NUOVA, ed e' O1 ad avermelo detto PRIMA di misurare: in
memoria c'erano gia' `lessons/verimem/ab-l41-numero-in-lettere-0` e `-1` — «6» in
cifra esce quarantined, «SEI» in lettere esce model_claim con grounding 99.98.
Quello e' un A/B su UN numero in UNA lingua. Questo banco dice che **e'
sistematico**: sei casi reali, quattro scritture, separazione 0/6 vs 6/6.

⇒ CIO' CHE CAMBIA. Con il solo A/B si poteva dire «caso limite, una parola
particolare». Con 6/6 su quattro scritture no: **la superficie protetta non e' «i
numeri», sono «i numeri scritti in cifra»**, e la riscrittura che la aggira e'
quella che un LLM produce da solo quando parla in prosa. In italiano
«trecentoquaranta colli» e' PIU' naturale di «340 colli» in una frase discorsiva.
⇒ Non serve un attaccante: **basta scrivere normalmente.**

⇒ E CHIUDE IL QUADRO DEI DUE STRATI, in peggio::

    `L4.1` sulle CIFRE     regge 18/18, immune al traino e alla scrittura...
                           ...ma solo se il numero e' in cifra: 6/6 lo aggira
    punteggio SEMANTICO    comprabile in QUATTRO modi (ripetere la fonte,
                           ricombinare i suoi token, il traino, il contorno neutro)

Il gate NON ha un punto debole e un punto forte. Ha un punto forte **con una porta
accanto**, e dietro la porta non c'e' un secondo strato: c'e' il punteggio, che si
compra.

✅ LIMITE PAGATO LO STESSO GIORNO, e ha dato il criterio ESATTO. Il primo giro
diceva «sei casi, quattro scritture, interi tondi; non provati decimali a parole,
forme miste, AR/HI/KO». Estensione (`ws5-dove-finisce-la-vista-di-L41.py`)::

    AR interi    CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1
    HI interi    CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1
    KO interi    CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1
    IT decimale  CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1      «tre virgola cinque»
    EN decimale  CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1      «three point five»
    IT mista     CIFRA=bloc      ALTRA=bloc                    «340 mila»
    EN mista     CIFRA=bloc      ALTRA=bloc                    «340 thousand»

    CIFRA  ammessi 0/7   L4.1 ha parlato su 7/7
    ALTRA  ammessi 5/7   L4.1 ha parlato su 2/7

⇒ SETTE SCRITTURE IN TUTTO (EN IT ZH JA AR HI KO) e anche i DECIMALI a parole.
⇒ MA LA FORMA MISTA E' BLOCCATA, ed e' la riga che vale piu' di tutte: «340 mila»
ha lo stesso valore, la stessa lingua e la stessa struttura di
«trecentoquarantamila», e viene fermata CON `L4.1`. L'unica differenza e' che
contiene il glifo `340`.
🔑 ⇒ LA FRONTIERA NON E' «i numeri scritti in cifra» in senso vago: `L4.1` vede il
numero **se e solo se compare almeno un carattere 0-9**. La forma mista e' la prova
per contrasto — isola la variabile senza cambiare nient'altro.
⚖️ E ribalta la lettura del limite: non e' «il gate e' debole sulle lingue esotiche».
E' **una condizione puramente tipografica**, identica in sette scritture, che non
ha niente a che vedere con la lingua ne' col significato.

⚠️ LIMITE RESIDUO: dodici casi in tutto, un valore per forma. Non provate le
frazioni («un terzo»), i numeri romani, ne' le forme parlate («un paio di
centinaia»). ⛔ NESSUNA CURA PROPOSTA: riconoscere i numeri a parole in N lingue
non e' una regex, e una cura che non so misurare non si consegna.

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

⚠️ CORREZIONE DEL 27/08 SERA — QUESTA RIGA ERA FALSA. Sopra c'era scritto
«nessuna cura: riconoscere i numeri a parole in N lingue non e' una regex». **Il
prodotto lo fa gia' dal 16/08**, e l'ho scoperto solo perche' `verimem stats`
elenca fra i layer un `L4.1-a-parole` che non conoscevo (scattato 1 volta).
  · commit «gate: la fonte diceva il numero a parole e il fatto vero spariva»
  · `assenti_che_la_fonte_scrive_a_parole()` chiama `valori_scritti_a_parole(text)`,
    generica, in `quantity_match.py:2446`
  · ma e' chiamata SOLO sulla `source`, mai sulla `proposition`
⇒ Quel layer cura il caso ROVESCIATO (fonte a parole, claim in cifra, fatto VERO
trattenuto). Il caso di questo banco — claim a parole — non ha nessun controllo.
⇒ La simmetria mancante ha un nome e una riga. E il vincolo del docstring
(«non usarla in `extract_quantities`, creerebbe quantita' fantasma») NON la vieta:
li' si parla del parser, qui resta «un confronto fra due testi».
⛔ MA NON CHIUDEREBBE QUESTO BANCO: `_NUMERALI_A_PAROLE` conosce **EN e IT**. Delle
sette scritture misurate qui se ne coprirebbero **due**; ZH JA AR HI KO restano
scoperte. E il layer esistente DECLASSA, mentre qui il valore falso ENTRA: la
severita' va decisa, e non la decide un banco.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-cifra-si-aggira-scrivendola-a-parole.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

#: (lingua, fonte, claim-CIFRA, claim-LETTERE)
CASI = [
 ("EN", "Logistics note: the shipment was delivered to the Bari depot.",
        "340 parcels were delivered to the Bari depot.",
        "Three hundred and forty parcels were delivered to the Bari depot."),
 ("EN", "Report: the Verona branch hired new staff.",
        "The Verona branch hired 27 people.",
        "The Verona branch hired twenty-seven people."),
 ("IT", "Nota logistica: la merce e' stata consegnata al deposito di Bari.",
        "340 colli sono stati consegnati al deposito di Bari.",
        "Trecentoquaranta colli sono stati consegnati al deposito di Bari."),
 ("IT", "Verbale: il consiglio ha approvato il bilancio.",
        "Il consiglio ha approvato il bilancio con 12 voti favorevoli.",
        "Il consiglio ha approvato il bilancio con dodici voti favorevoli."),
 ("ZH", "物流记录：货物已送达巴里仓库。",
        "340箱货物已送达巴里仓库。",
        "三百四十箱货物已送达巴里仓库。"),
 ("JA", "物流記録：荷物はバーリ倉庫に配達されました。",
        "340個の荷物がバーリ倉庫に配達されました。",
        "三百四十個の荷物がバーリ倉庫に配達されました。"),
]

def prova(claim, src):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=src, grounding_llm=None, ground_write=True)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    return (getattr(r, "action", "?") == "persist",
            any(str(w).startswith("L4.1") for w in ws))

amm = {"CIFRA": 0, "LETTERE": 0}
l41 = {"CIFRA": 0, "LETTERE": 0}
print("")
for lg, src, c_cifra, c_lettere in CASI:
    out = []
    for eti, claim in (("CIFRA", c_cifra), ("LETTERE", c_lettere)):
        ok, ha41 = prova(claim, src)
        amm[eti] += int(ok); l41[eti] += int(ha41)
        out.append("%s=%s%s" % (eti, "AMMESSO" if ok else "bloc", "" if ha41 else " (senza L4.1)"))
    print("   %-3s  %s" % (lg, "   ".join(out)))
print("")
n = len(CASI)
for eti in ("CIFRA", "LETTERE"):
    print("   %-8s ammessi %d/%d   L4.1 ha parlato su %d/%d" % (eti, amm[eti], n, l41[eti], n))
