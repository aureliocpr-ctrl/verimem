r"""La cella `C+D` era SOLA nel suo stato: la allargo a cinque fonti.

⚠️ **Banco che paga un debito dichiarato da me quaranta minuti fa**, e che può
demolire una lettura che ho già consegnato.

Nel banco delle combinazioni, `C+D` (simboli + colonne, righe lunghe) è stata
l'unica cella in uno stato che non avevo previsto:

    A · B+C · B+D    vero ~100    falso 0.3-2.7    🟢 distingue
    C+D              vero  1.7    falso 79.0       🔴 cade il VERO
    E                vero 52.0    falso 98.9       🔴🔴 rovesciato

⇒ Su quell'unica cella ho costruito **due affermazioni** che sono già sul
canale: «*per il danno bastano simboli+colonne*» e «*le colonne coi simboli
distruggono il segnale, l'andare a capo trasforma il rumore in un sì*».
**Una cella sola non regge due affermazioni**, e l'avevo scritto io fra i punti
deboli: «*`C+D` è la sola cella del suo stato e meriterebbe di essere allargata
prima di costruirci sopra*».

LA PROVA: **cinque fonti diverse**, ognuna nella forma `C+D` e nella forma `A`
(prosa) come controllo appaiato. Contenuto e claim cambiano insieme alla fonte;
l'unica cosa che resta fissa è **la forma**.

    se `C+D` fa cadere il vero su 4-5 fonti   → il gradino è reale
    se lo fa su 1-2                            → era la MIA cella, e ritiro

⚠️ **CONTROLLO APPAIATO, ed è la metà che conta**: la stessa identica
informazione, sulla stessa fonte, in **prosa**. Se cadesse anche lì, non sarebbe
la forma: sarebbe il contenuto che ho scelto.

🩺 **Regime verificato prima di misurare**: daemon di encoding **attivo**
(ultimi 12 fatti dello store col vettore). E **nessun `None`** deve comparire
nella colonna del grounding: se compare, quella riga misura il daemon.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: le cinque coppie sono **mie**; un vero e un falso per cella;
«prosa» e «colonne coi simboli» restano giudizi miei sulla forma.

✅ ESITO - **il gradino e' REALE: non era la mia cella. 4 fonti su 5, e zero
falsi allarmi nel controllo appaiato**::

    fonte       forma    VERO       ground   FALSO      ground  verdetto
    suite       PROSA    passa       100.0   cade          0.6  🟢 distingue
                C+D      CADE          1.7   cade         79.0  🔴 cade il VERO
    collaudo    PROSA    passa       100.0   cade          0.3  🟢 distingue
                C+D      CADE         73.8   cade         61.5  🔴 cade il VERO
    fornitura   PROSA    passa       100.0   cade          0.1  🟢 distingue
                C+D      CADE         25.9   cade         33.7  🔴 cade il VERO
    pagamento   PROSA    passa       100.0   cade          0.3  🟢 distingue
                C+D      CADE         28.8   cade          8.0  🔴 cade il VERO
    delibera    PROSA    passa       100.0   cade          0.8  🟢 distingue
                C+D      passa        80.5   cade         79.2  🟢 distingue

    il VERO cade in C+D          4 su 5
    il VERO cade in PROSA        0 su 5   ← controllo appaiato

🔑 **La stessa identica informazione, sulla stessa fonte, in prosa passa SEMPRE
(100.0 su 5 su 5) e a colonne coi simboli si perde 4 volte su 5.** ⇒ Il debito
che avevo dichiarato e' pagato: **la lettura consegnata regge su una
popolazione, non su un punto.**

⚠️ **E il controllo appaiato e' cio' che rende leggibile il numero**: se il vero
fosse caduto anche in prosa, la causa sarebbe stata il contenuto che ho scelto,
non la forma. **Zero su cinque** — la forma e' isolata.

📐 **IL DATO NUOVO, che la cella singola non poteva dare: il collasso della
SEPARAZIONE.** In prosa il vero sta a **100.0** e il falso fra **0.1 e 0.8** —
due ordini di grandezza. In `C+D` i due punteggi si **avvicinano fino a
toccarsi**::

    collaudo    vero 73.8  ·  falso 61.5     distanza 12 punti
    fornitura   vero 25.9  ·  falso 33.7     **il falso sta SOPRA il vero**
    delibera    vero 80.5  ·  falso 79.2     distanza 1.3 punti

⇒ **Su `fornitura` l'ordine e' gia' invertito** (falso 33.7 contro vero 25.9):
non e' ancora un rovesciamento perche' **entrambi restano sotto la soglia**, ma
il giudizio ha gia' perso il segno. E su `delibera` il vero passa per **1.3
punti** di margine — passa, ma non perche' il gate abbia capito qualcosa.
⇒ **La forma non alza la severita': cancella l'informazione.** Un gate severo
sbaglia in una direzione; questo perde la capacita' di distinguere, e da li' il
verso dipende dal caso.

🩺 Regime verificato prima di misurare: daemon **attivo**, e **nessun `None`**
nella colonna del grounding ⇒ tutte e venti le chiamate sono state giudicate.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: cinque coppie **mie**; un vero e un falso per cella; «prosa» e
«colonne coi simboli» restano giudizi miei sulla forma; **`delibera` non cade** e
non ho indagato perche' — e' il caso che direbbe dove sta il confine.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-cella-CD-allargata-a-cinque-fonti.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

#: (nome, riga-che-sostiene in PROSA, riga in C+D, claim VERO, claim FALSO)
CASI = [
    ("suite",
     "La suite riporta 21 passed e 2 skipped, e termina con EXIT=0.",
     "tests/suite.py | passed=21 ++ skipped=2 -- exit=0 | al 100% [ ok ]",
     "La suite termina con EXIT=0.", "La suite termina con EXIT=1."),
    ("collaudo",
     "Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo.",
     "impianto/linea3 | collaudo=concluso ++ data=12-marzo -- esito=positivo | al 100% [ ok ]",
     "Il collaudo della linea 3 si e' concluso il 12 marzo.",
     "Il collaudo della linea 3 si e' concluso il 25 marzo."),
    ("fornitura",
     "La fornitura di 200 unita' e' entrata in magazzino il 5 aprile con bolla 4471.",
     "magazzino/ingressi | unita=200 ++ data=5-aprile -- bolla=4471 | al 100% [ ok ]",
     "La fornitura di 200 unita' e' entrata in magazzino il 5 aprile.",
     "La fornitura di 700 unita' e' entrata in magazzino il 5 aprile."),
    ("pagamento",
     "Il pagamento della fattura 118 di 4300 euro e' stato eseguito il 20 giugno.",
     "contabilita/pagamenti | fattura=118 ++ importo=4300 -- data=20-giugno | al 100% [ ok ]",
     "Il pagamento della fattura 118 e' stato eseguito il 20 giugno.",
     "Il pagamento della fattura 118 e' stato eseguito il 2 luglio."),
    ("delibera",
     "Il consiglio ha deliberato all'unanimita' sul punto tre il 9 maggio.",
     "consiglio/sedute | punto=3 ++ esito=unanimita -- data=9-maggio | al 100% [ ok ]",
     "Il consiglio ha deliberato sul punto tre il 9 maggio.",
     "Il consiglio ha deliberato sul punto otto il 9 maggio."),
]

#: zeppa nelle due forme, per portare la fonte alla lunghezza del regime misurato
Z_PROSA = ("Il modulo di ingestione normalizza i percorsi prima di aprirli e registra "
           "ogni apertura nel giornale delle operazioni. La procedura di avvio verifica "
           "che la cartella dei dati sia scrivibile e che il file di configurazione sia "
           "leggibile, poi prepara le strutture in memoria. ")
Z_CD = ("verimem/ingestione.py | percorso=normalizzato ++ esito=ok -- durata_ms=4 | "
        "al 100% [ ok ] verimem/avvio.py | cartella=scrivibile ++ config=leggibile "
        "-- esito=ok | al 100% [ ok ]\n")


def _gate(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az == "persist", g


def main():
    print("  %-11s %-6s   %-9s %8s   %-9s %8s  %s"
          % ("fonte", "forma", "VERO", "ground", "FALSO", "ground", "verdetto"))
    print("  " + "-" * 84)
    cd_vero_cade = prosa_vero_cade = 0
    visto_none = False
    for nome, riga_prosa, riga_cd, vero, falso in CASI:
        for forma, fonte in (("PROSA", Z_PROSA * 12 + riga_prosa + "\n"),
                             ("C+D", Z_CD * 12 + riga_cd + "\n")):
            pv, gv = _gate(vero, fonte)
            pf, gf = _gate(falso, fonte)
            if gv is None or gf is None:
                visto_none = True
            if not pv:
                if forma == "C+D":
                    cd_vero_cade += 1
                else:
                    prosa_vero_cade += 1
            if pv and not pf:
                verdetto = "🟢 distingue"
            elif not pv and pf:
                verdetto = "🔴🔴 ROVESCIATO"
            elif not pv and not pf:
                verdetto = "🔴 cade il VERO"
            else:
                verdetto = "🔴 passa il falso"
            print("  %-11s %-6s   %-9s %8s   %-9s %8s  %s"
                  % (nome if forma == "PROSA" else "", forma,
                     "passa" if pv else "CADE",
                     ("%.1f" % gv) if gv is not None else "None",
                     "passa" if pf else "cade",
                     ("%.1f" % gf) if gf is not None else "None", verdetto))
        print("  " + "-" * 84)

    print("=== SINTESI ===")
    print("  fonti                                   %d" % len(CASI))
    print("  🔴 il VERO cade in forma C+D            %d su %d" % (cd_vero_cade, len(CASI)))
    print("  controllo: il VERO cade in PROSA        %d su %d" % (prosa_vero_cade, len(CASI)))
    if prosa_vero_cade:
        print("\n  ⚠️ Il vero cade anche in prosa: NON e' la forma, e' il contenuto")
        print("     che ho scelto. La lettura consegnata va RITIRATA.")
    elif cd_vero_cade >= 4:
        print("\n  ✅ IL GRADINO E' REALE: la forma C+D fa cadere il vero su una")
        print("     popolazione, non su una cella. La lettura consegnata regge.")
    elif cd_vero_cade <= 2:
        print("\n  🔴 ERA LA MIA CELLA: su cinque fonti il gradino quasi non compare.")
        print("     Le due affermazioni che ho consegnato vanno RITIRATE.")
    else:
        print("\n  🟡 Meta' e meta': il gradino esiste ma non e' la regola —")
        print("     la lettura va RIDIMENSIONATA, non confermata.")
    if visto_none:
        print("\n  ⚠️ C'E' UN None NEL GROUNDING: quella riga misura il daemon.")


main()
