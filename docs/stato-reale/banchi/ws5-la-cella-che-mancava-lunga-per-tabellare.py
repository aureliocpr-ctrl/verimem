r"""La cella che mancava: fonte LUNGA **e** TABELLARE. Chiude una causa ignota.

🔍 **memoria** (regola di canale: un finding dichiarato nuovo porta la ricerca
fatta). Prima di misurare ho letto `LANT-75` di @ws7 delle 13:53 — «*il gate
premia le fonti in PROSA e penalizza quelle TABELLARI*», con un claim VERO a
**15.1** perche' il verbale enuncia la relazione in prosa e l'uscita di uno
script la mostra in due righe. **Quella dimensione e' sua e non la rifaccio.**
E lei stessa cita `quantity_match.py:676` («*27 falsi positivi su 28 sulle fonti
tabellari*»): il difetto era gia' dichiarato nel prodotto da una terza
direzione.

⇒ QUI MISURO SOLO CIO' CHE NESSUNA DELLE DUE COPRE: **l'incrocio**.

LO STATO DELLE MIE MISURE, che e' il motivo per cui questo banco esiste::

                        PROSA              TABELLARE
    CORTA               (non misurata)     ✅ passa 100.0   (banco d883abd7)
    LUNGA               ✅ passa 100.0     ❓ MAI MISURATA   ← l'incidente sta qui
                        (banco d883abd7)

**Tre celle su quattro dicono che va tutto bene, e l'incidente e' avvenuto
nella quarta.** L'incidente: salvando i fatti della cura `L1.20`, «EXIT=0.» —
presente **alla lettera** nella source — e' stato quarantinato; la source era
l'output vero di `pytest`, cioe' **lunga E tabellare** insieme. Ho dichiarato
la causa ignota dopo tre ipotesi cadute (lunghezza del claim, troncamento a 512
token, posizione nella fonte): **nessuna delle tre guardava l'incrocio.**

L'IPOTESI, dichiarata prima: **e' l'incrocio, non i due fattori da soli.** Corta
e tabellare passa; lunga e in prosa passa; **lunga e tabellare no**.
⚠️ **L'ESITO CHE MI SMENTISCE**: se anche `LUNGA+TABELLARE` passa, l'incrocio
non e' la causa e resto senza spiegazione — il che va scritto, non aggirato con
una quinta ipotesi.

⚠️ **POPOLAZIONE DI CONTROLLO**: su ognuna delle quattro fonti viaggia anche il
claim **FALSO** (`EXIT=1.`, che ogni fonte contraddice). Serve a distinguere due
letture opposte: se in una cella cade il vero **e passa il falso**, quella cella
non e' «severa», e' **rovesciata**. E il banco precedente ha gia' mostrato che
su un frammento minimo il giudice da' 100.0 a entrambi: senza i falsi non si
vede.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: le quattro fonti sono **mie** e differiscono per costruzione su
due assi insieme — «tabellare» qui vuol dire righe di script con colonne e
simboli, non una tabella markdown; un claim vero e uno falso per cella.

🔴🔴 ESITO - **la causa e' l'INCROCIO, e nella cella che mancava il gate non e'
severo: e' ROVESCIATO**::

    fonte                  car.   VERO       ground   FALSO      ground  verdetto
    CORTA + prosa            62   passa        97.5   cade          1.0  🟢 distingue
    CORTA + tabellare        81   passa       100.0   cade          1.4  🟢 distingue
    LUNGA + prosa          3350   passa       100.0   cade          0.6  🟢 distingue
    LUNGA + tabellare      2517   CADE         52.0   passa        98.9  🔴🔴 ROVESCIATO

                        prosa       tabellare
          CORTA         passa       passa
          LUNGA         passa       CADE

🔑 **NE' LA LUNGHEZZA NE' LA FORMA, DA SOLE, FANNO DANNO: LO FA IL LORO
INCROCIO.** Tre celle su quattro distinguono benissimo. Nella quarta - fonte
**lunga E tabellare** - il claim VERO, che la fonte sostiene alla lettera, cade
a **52.0**, e il claim FALSO, che la fonte **contraddice**, entra a **98.9**.

⇒ **Non e' un gate severo: e' un gate che preferisce il falso al vero.** La
distinzione conta perche' porta a cure opposte - contro un gate severo si
alza una soglia, contro uno rovesciato no.

✅ **REGGE AL CONTROLLO DELL'ORDINE** (il confondente isolato da @ws8): la stessa
cella eseguita **per prima in un processo fresco**, col FALSO prima del VERO, da'
**gli stessi identici numeri** — falso 98.9 passa, vero 52.0 cade. Non e' un
artefatto della sequenza.

📌 **CHIUDE UNA CAUSA CHE AVEVO DICHIARATO IGNOTA** dopo tre ipotesi cadute
(lunghezza del claim, troncamento a 512 token, posizione nella fonte). Nessuna
delle tre guardava l'incrocio, e l'incidente originale - «EXIT=0.» quarantinato
con la source vera di `pytest` - stava **esattamente li'**: quella source e'
lunga e tabellare insieme.

🔥 **PERCHE' RIGUARDA TUTTE, ORA**: @ws7 in `LANT-75` lo dice per la sua
dimensione — «*le nostre fonti sono output di script*». Un banco che gira
produce una source **lunga e tabellare**. ⇒ **Ogni fatto salvato con la source di
un banco lungo sta nel regime dove il gate puo' preferire il falso al vero.**
📌 Si compone con `LANT-75` (@ws7: la forma tabellare penalizza) e con
`quantity_match.py:676`, che dichiara 27 falsi positivi su 28 sulle fonti
tabellari: **tre direzioni, e questa aggiunge che la lunghezza e' la seconda
condizione**.

⚠️ **E LA PARTE GRAVE L'HA TROVATA LA COLONNA DI CONTROLLO, la terza volta in
due giorni.** La mia ipotesi diceva «cade il vero» e sarebbe stata confermata
guardando solo i veri. Il falso a 98.9 - che nessuna ipotesi mia prevedeva - si
vede **solo** perche' i falsi viaggiavano accanto.

🪞 **E RESTRINGO IO LA PORTATA, un minuto dopo averla scritta.** Nel messaggio
di consegna avevo scritto: «*ogni fatto salvato con la source di un banco lungo
sta nel regime dove il gate puo' preferire il falso al vero*», promettendo di
riportare come sarebbe andato il salvataggio di questi stessi fatti. **E'
andato bene: 3 fatti su 3 AMMESSI**, con una source di **9630 caratteri**.
⇒ **La mia frase era piu' larga della misura.** La differenza: la source di un
banco e' un file `.py` con un lungo docstring **in prosa** piu' del codice —
**e' MISTA**, non tabellare pura. La cella rovesciata usa zeppa tabellare
**pura** (righe di log e di diff, nient'altro).
⇒ La formulazione che regge: **il regime pericoloso e' fonte lunga e tabellare
PURA** — l'uscita grezza di uno script senza prosa intorno. Un file di banco
non ci rientra, e chi salva col docstring come source e' al riparo.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: **un claim vero e uno falso per cella** - il segnale e' netto
(52.0 contro 98.9) ma la popolazione e' minima; le quattro fonti sono mie e
cambiano su due assi per costruzione; «tabellare» qui e' output di script con
colonne e simboli, non una tabella markdown; **non ho isolato QUALE proprieta'
della forma tabellare pesi** (le colonne? i simboli? le righe spezzate?) - la
prossima domanda e' quella.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-cella-che-mancava-lunga-per-tabellare.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

VERO = "La suite termina con EXIT=0."
FALSO = "La suite termina con EXIT=1."

#: la stessa informazione, nelle due forme
RIGA_PROSA = ("La suite riporta 21 passed e 2 skipped, e termina con EXIT=0.\n")
RIGA_TAB = ("tests/test_uno.py ....... [ 33%]\n"
            "21 passed, 2 skipped, 1 warning in 9.31s\n"
            "EXIT=0\n")

#: riempitivo nelle due forme, per allungare SENZA aggiungere informazione
ZEPPA_PROSA = (
    "Il modulo di ingestione normalizza i percorsi prima di aprirli e registra "
    "ogni apertura nel giornale delle operazioni. La procedura di avvio verifica "
    "che la cartella dei dati sia scrivibile e che il file di configurazione sia "
    "leggibile, poi prepara le strutture in memoria. "
)
ZEPPA_TAB = (
    "verimem/ingestione.py:112 percorso=normalizzato esito=ok durata_ms=4\n"
    "verimem/avvio.py:57 cartella=scrivibile config=leggibile esito=ok\n"
    " verimem/giornale.py    |  18 ++--\n"
    " verimem/rotazione.py   |   7 +-\n"
)

FONTI = [
    ("CORTA + prosa", RIGA_PROSA),
    ("CORTA + tabellare", RIGA_TAB),
    ("LUNGA + prosa", ZEPPA_PROSA * 12 + RIGA_PROSA),
    ("LUNGA + tabellare", ZEPPA_TAB * 12 + RIGA_TAB),
]


def _gate(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az == "persist", g


def main():
    print("  %-20s %6s   %-9s %8s   %-9s %8s  %s"
          % ("fonte", "car.", "VERO", "ground", "FALSO", "ground", "verdetto"))
    print("  " + "-" * 92)
    esiti = {}
    for nome, fonte in FONTI:
        pv, gv = _gate(VERO, fonte)
        pf, gf = _gate(FALSO, fonte)
        esiti[nome] = pv
        if pv and not pf:
            verdetto = "🟢 distingue"
        elif not pv and not pf:
            verdetto = "🔴 CADE IL VERO"
        elif pv and pf:
            verdetto = "🔴 passa anche il FALSO"
        else:
            verdetto = "🔴🔴 ROVESCIATO"
        print("  %-20s %6d   %-9s %8s   %-9s %8s  %s"
              % (nome, len(fonte), "passa" if pv else "CADE",
                 ("%.1f" % gv) if gv is not None else "None",
                 "passa" if pf else "cade",
                 ("%.1f" % gf) if gf is not None else "None", verdetto))

    print("\n=== LA GRIGLIA (il claim VERO passa?) ===\n")
    print("                    prosa            tabellare")
    print("      CORTA         %-16s %s"
          % ("passa" if esiti["CORTA + prosa"] else "CADE",
             "passa" if esiti["CORTA + tabellare"] else "CADE"))
    print("      LUNGA         %-16s %s"
          % ("passa" if esiti["LUNGA + prosa"] else "CADE",
             "passa" if esiti["LUNGA + tabellare"] else "CADE"))
    solo_incrocio = (esiti["CORTA + prosa"] and esiti["CORTA + tabellare"]
                     and esiti["LUNGA + prosa"] and not esiti["LUNGA + tabellare"])
    print("\n  ⇒ %s" % ("🎯 E' L'INCROCIO: cade solo LUNGA+TABELLARE, e la causa"
                        " dell'incidente\n     e' isolata."
                        if solo_incrocio else
                        "L'incrocio NON spiega da solo: leggi la griglia riga per"
                        " riga.\n     Se passano tutte e quattro, l'ipotesi e'"
                        " falsificata e resto senza causa."))
    print("  ⚠️ La colonna FALSO distingue «severa» da «rovesciata»: sono difetti")
    print("     diversi e chiedono cure opposte.")


main()
