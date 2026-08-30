r"""Servono tutte e tre le proprietà della forma, o ne bastano DUE?

Terzo e ultimo passo del filone aperto da `W5-5`. Lo stato prima di questo banco:

    fonte lunga e tabellare PIENA (spezzata + simboli + colonne)  🔴 ROVESCIATO
    ognuna delle tre PRESA DA SOLA                                🟢 distingue

⇒ **La causa è la combinazione.** Ma «combinazione» può voler dire *due su tre*
oppure *tutte e tre*, e la differenza **non è accademica: è quanto è esteso il
regime pericoloso**, cioè quante delle nostre fonti ci cadono dentro.

    se basta una COPPIA   → il regime è largo: molti output di script ne hanno due
    se servono TUTTE E TRE → è stretto, e riguarda solo l'uscita grezza completa

LE TRE COPPIE, stesse zeppe e stesso claim del banco precedente::

    B+C   spezzate + simboli        (righe corte con | ++ -- %, ma con le frasi)
    B+D   spezzate + colonne        (righe corte a chiave=valore, senza simboli)
    C+D   simboli + colonne         (chiave=valore con | ++ --, su righe lunghe)

⚠️ **POPOLAZIONE DI CONTROLLO — le due estremità già misurate**: `A` (prosa)
deve **distinguere** e `E` (tutte e tre) deve **rovesciarsi**. Se una delle due
non riproduce, il banco non è leggibile e i verdetti sulle coppie non valgono.
⚠️ Su ogni forma viaggiano un claim **VERO** e uno **FALSO**: senza i falsi,
«il vero cade» non separa un gate severo da uno rovesciato.

🩺 **REGIME VERIFICATO PRIMA DI MISURARE** (lezione del 30/08): il daemon di
encoding è **attivo** — righello `SELECT (embedding IS NOT NULL AND
length(embedding)>0) FROM facts ORDER BY rowid DESC LIMIT 12`, tutti `1`. E la
tabella qui sotto **non deve contenere `None`** nella colonna del grounding: se
ne compare uno, quella riga misura il daemon e non il gate.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: le zeppe sono **mie**; le lunghezze non sono uguali al
carattere; un vero e un falso per forma — il segnale del rovesciamento è netto
(52 contro 98) ma la popolazione è minima.

🔴 ESITO - **la domanda era binaria e la risposta ha TRE stati: esiste un
gradino intermedio che nessuna delle due ipotesi prevedeva**::

    forma                          car.   VERO       ground   FALSO      ground  verdetto
    A nessuna (CONTROLLO)          3350   passa       100.0   cade          0.6  🟢 distingue
    B+C spezzate+simboli           3626   passa       100.0   cade          0.3  🟢 distingue
    B+D spezzate+colonne           2145   passa        99.9   cade          2.7  🟢 distingue
    C+D simboli+colonne            2217   CADE          1.7   cade         79.0  🔴 cade il VERO
    E tutte e tre (CONTROLLO)      2517   CADE         52.0   passa        98.9  🔴🔴 ROVESCIATO

✅ Controlli riprodotti (A distingue, E si rovescia) ⇒ le tre coppie sono leggibili.

🪞 **E LA SINTESI CHE IL BANCO STAMPA DA SOLO E' TROPPO GENEROSA — la correggo
io.** Lo script conclude «*nessuna coppia rovescia ⇒ servono tutte e tre ⇒ il
regime e' stretto, l'avviso resta come l'ho dato*», perche' cerca **solo** il
rovesciamento. **Ma guardate `C+D`**: il claim VERO **cade a 1.7** e il falso
sale a **79.0** — contro lo 0.3-2.7 di tutte le altre forme. ⇒ **Li' il danno
c'e' gia'**: l'utente perde un fatto sostenuto. Manca solo che il falso superi
la soglia.

🔑 **LE SOGLIE SONO DUE, E VANNO DETTE SEPARATE**::

    per il DANNO (un fatto VERO viene perso)        bastano SIMBOLI + COLONNE
    per il ROVESCIAMENTO (il falso entra al posto
    del vero)                                       servono tutte e TRE

⇒ **Il regime pericoloso e' piu' largo di quanto avessi scritto**, e l'avviso va
esteso: **non serve l'uscita grezza completa perche' un fatto vero venga perso —
bastano colonne con dentro dei simboli.**

📐 **E si vede il RUOLO di ciascuna proprieta', che era la domanda dietro la
domanda**: `C+D` (simboli+colonne) **rompe il giudizio** — vero 1.7, falso 79.0,
entrambi lontanissimi dal vero valore. Aggiungere `B` (spezzare le righe) porta
da `C+D` a `E`, cioe' **fa passare il falso oltre la soglia** (79.0 → 98.9)
risollevando il vero (1.7 → 52.0). ⇒ **Le colonne coi simboli distruggono il
segnale; l'andare a capo e' cio' che trasforma il rumore in un SI'.**
⚖️ Questa lettura poggia su **una cella per combinazione**: e' la spiegazione
piu' semplice che regge sui cinque punti, **non una legge**.

🩺 **Regime verificato prima di misurare**: daemon di encoding **attivo**
(ultimi 12 fatti dello store tutti col vettore) e **nessun `None`** nella
colonna del grounding qui sopra ⇒ tutte e dieci le chiamate sono state
giudicate, e il confondente del primo write non tocca questa tabella.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: zeppe **mie**, lunghezze non uguali al carattere (2145-3626);
**un vero e un falso per forma**; `C+D` e' la sola cella del suo stato e
meriterebbe di essere allargata prima di costruirci sopra.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-bastano-due-proprieta-o-servono-tutte-e-tre.py <dir-temp>
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

RIGA_PROSA = "La suite riporta 21 passed e 2 skipped, e termina con EXIT=0.\n"
RIGA_TAB = ("tests/test_uno.py ....... [ 33%]\n"
            "21 passed, 2 skipped, 1 warning in 9.31s\n"
            "EXIT=0\n")

#: le stesse identiche frasi del banco precedente, per confrontabilità
_FRASI = ("Il modulo di ingestione normalizza i percorsi prima di aprirli e registra "
          "ogni apertura nel giornale delle operazioni. La procedura di avvio verifica "
          "che la cartella dei dati sia scrivibile e che il file di configurazione sia "
          "leggibile, poi prepara le strutture in memoria. ")


def _spezza(t, n=40):
    parole, riga, out = t.split(), "", []
    for p in parole:
        if len(riga) + len(p) + 1 > n:
            out.append(riga)
            riga = p
        else:
            riga = (riga + " " + p).strip()
    out.append(riga)
    return "\n".join(out) + "\n"


#: A — nessuna proprietà (controllo)
Z_A = _FRASI

#: B+C — spezzate E con simboli, ma le frasi restano
Z_BC = _spezza("Il modulo di ingestione | normalizza i percorsi prima di aprirli e "
               "registra ogni apertura nel giornale ++ delle operazioni. La procedura "
               "di avvio -- verifica che la cartella dei dati sia scrivibile al 100% e "
               "che il file di configurazione sia leggibile [ ok ], poi prepara le "
               "strutture in memoria. ")

#: B+D — spezzate E a colonne, ma senza simboli
Z_BD = ("verimem ingestione percorso normalizzato\n"
        "esito ok durata 4\n"
        "verimem avvio cartella scrivibile\n"
        "config leggibile esito ok\n"
        "verimem giornale rotazione attiva\n"
        "soglia 64 durata 2\n")

#: C+D — a colonne E con simboli, ma su righe lunghe (non spezzate)
Z_CD = ("verimem/ingestione.py | percorso=normalizzato ++ esito=ok -- durata_ms=4 | al 100% [ ok ] verimem/avvio.py | cartella=scrivibile ++ config=leggibile -- esito=ok | al 100% [ ok ]\n")

#: E — tutte e tre (controllo)
Z_E = ("verimem/ingestione.py:112 percorso=normalizzato esito=ok durata_ms=4\n"
       "verimem/avvio.py:57 cartella=scrivibile config=leggibile esito=ok\n"
       " verimem/giornale.py    |  18 ++--\n"
       " verimem/rotazione.py   |   7 +-\n")

FORME = [
    ("A nessuna (CONTROLLO)", Z_A * 12 + RIGA_PROSA),
    ("B+C spezzate+simboli", Z_BC * 12 + RIGA_PROSA),
    ("B+D spezzate+colonne", Z_BD * 12 + RIGA_TAB),
    ("C+D simboli+colonne", Z_CD * 12 + RIGA_TAB),
    ("E tutte e tre (CONTROLLO)", Z_E * 12 + RIGA_TAB),
]


def _gate(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az == "persist", g


def main():
    print("  %-28s %6s   %-9s %8s   %-9s %8s  %s"
          % ("forma", "car.", "VERO", "ground", "FALSO", "ground", "verdetto"))
    print("  " + "-" * 98)
    esiti, visto_none = {}, False
    for nome, fonte in FORME:
        pv, gv = _gate(VERO, fonte)
        pf, gf = _gate(FALSO, fonte)
        if gv is None or gf is None:
            visto_none = True
        if pv and not pf:
            verdetto = "🟢 distingue"
        elif not pv and pf:
            verdetto = "🔴🔴 ROVESCIATO"
        elif not pv and not pf:
            verdetto = "🔴 cade anche il vero"
        else:
            verdetto = "🔴 passa anche il falso"
        esiti[nome.split()[0]] = verdetto
        print("  %-28s %6d   %-9s %8s   %-9s %8s  %s"
              % (nome, len(fonte), "passa" if pv else "CADE",
                 ("%.1f" % gv) if gv is not None else "None",
                 "passa" if pf else "cade",
                 ("%.1f" % gf) if gf is not None else "None", verdetto))

    print("\n=== SINTESI ===")
    ok = ("distingue" in esiti.get("A", "")) and ("ROVESCIATO" in esiti.get("E", ""))
    print("  controlli (A distingue, E rovesciato): %s"
          % ("✅ riprodotti" if ok else "🔴 NON riprodotti — il banco non e' leggibile"))
    coppie = [k for k in ("B+C", "B+D", "C+D") if "ROVESCIATO" in esiti.get(k, "")]
    print("  coppie che ROVESCIANO: %s" % (", ".join(coppie) if coppie else "nessuna"))
    print("\n  ⇒ %s" % ("🔑 BASTANO DUE proprieta' (%s): il regime pericoloso e' PIU' LARGO\n"
                        "     di quanto avessi detto — molti output di script ne hanno due."
                        % ", ".join(coppie) if coppie else
                        "🔑 SERVONO TUTTE E TRE: il regime e' STRETTO e riguarda solo\n"
                        "     l'uscita grezza completa. L'avviso resta come l'ho dato."))
    if visto_none:
        print("\n  ⚠️ C'E' UN None NELLA COLONNA DEL GROUNDING: quella riga misura il")
        print("     daemon, non il gate. Rifai il banco a daemon attivo.")


main()
