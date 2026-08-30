r"""La fonte oltre 512 token e' TRONCATA: conta DOVE sta il pezzo che serve.

⚠️ Terzo banco di fila che nasce da un'ipotesi mia sbagliata, e questa volta
l'errore ha portato alla causa.

LA CATENA, per intero, perche' il modo in cui ci sono arrivata e' il reperto:
① Salvando i fatti della cura `L1.20`, il gate ha **quarantinato «EXIT=0.»** —
   una stringa che nella source c'era **alla lettera**.
② Ipotesi pubblicata prima di misurare: *«decide la LUNGHEZZA DEL CLAIM: i
   frammenti corti non sono proposizioni e il giudice non ha su cosa
   pronunciarsi»*. ⇒ **FALSIFICATA**: sul banco, con una fonte corta,
   **«EXIT=0.» passa a 100.0** e con lei tutti i frammenti, dal piu' corto al
   piu' lungo. Zero veri caduti.
③ Rimesso lo stesso claim con la source **VERA** dell'incidente: **downgrade a
   72.94**. ⇒ Non e' il claim. **E' la FONTE.**
④ E il prodotto lo dichiara, in una riga che passa inosservata::

       Token indices sequence length is longer than the specified maximum
       sequence length for this model (669 > 512)

⇒ **La fonte eccede la finestra del modello e viene troncata.** Il claim non
viene giudicato contro la fonte: viene giudicato contro **i primi 512 token**.

L'IPOTESI CHE QUESTO BANCO METTE ALLA PROVA, a variabile singola: **conta DOVE
sta**. Stessa fonte lunga, stesso claim, cambia solo la **posizione** della riga
che lo sostiene.

    fonte lunga, riga in TESTA    dentro la finestra   → deve PASSARE
    fonte lunga, riga in CODA     oltre la finestra    → deve CADERE
    fonte CORTA, stessa riga      nessun troncamento   → deve PASSARE

⚠️ **POPOLAZIONE DI CONTROLLO**: in ogni regime viaggia anche un claim **FALSO**
(`EXIT=1.`, che la fonte contraddice). Serve a separare due letture opposte:
se in coda cade il vero **e** cade il falso, il gate «non vede» quella zona; se
in coda **passa il falso**, il troncamento non rende il gate cieco - lo rende
**permissivo**, che e' peggio.
📌 E un dato gia' in mano che rende il controllo indispensabile: sul banco
precedente, con fonte corta, **il falso `EXIT=1.` e' passato a 100.0** insieme
al vero. Su frammenti minimi il giudice **non distingue**.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: il riempitivo e' prosa tecnica ripetuta, non un documento vero;
512 e' il limite dichiarato dal messaggio, **non l'ho letto nella
configurazione**; misuro l'esito e il punteggio, non quale porzione il modello
abbia effettivamente visto.

🔴 ESITO - **falsificata anche questa: la posizione NON conta, e il troncamento
non degrada il giudizio**::

    regime                       car.   VERO      ground   FALSO     ground  verdetto
    fonte CORTA (controllo)        60   passa       97.2   cade         1.0  🟢 distingue
    LUNGA, riga in TESTA         5380   passa       97.2   cade         1.0  🟢 distingue
    LUNGA, riga in CODA          5380   passa      100.0   cade         0.7  🟢 distingue

⇒ **Tutti e tre i regimi distinguono**, e la riga in **coda** - quella che
secondo la mia ipotesi doveva finire fuori dalla finestra - prende **100.0**,
il punteggio piu' alto dei tre. ⇒ **La fonte lunga non e' giudicata su una
porzione**: il claim viene sostenuto anche quando la riga che lo sostiene sta
in fondo a 5380 caratteri.

🪞 **E CADE L'INTERPRETAZIONE DEL WARNING, che avevo preso per la causa.** Il
messaggio `Token indices sequence length is longer than the specified maximum
sequence length for this model (669 > 512)` **c'e' davvero** ed e' stampato dal
prodotto — ma **non implica che il verdetto sia degradato**. Il modello che
tronca a 512 non e' quello che decide qui. ⇒ Avevo letto un avviso vero come
la spiegazione di un difetto, che e' esattamente il tipo di scorciatoia che
questo lavoro deve evitare: **un warning che compare vicino a un sintomo non ne
e' la causa finche' non lo si misura.**

═══ 🔴 TRE IPOTESI MIE, TRE FALSIFICAZIONI, E MI FERMO ═══
    ① «decide la lunghezza del CLAIM: i corti cadono»   → falsificata (passano
       tutti, e il piu' corto fa passare anche il falso)
    ② «la fonte oltre 512 token e' troncata»            → il troncamento c'e',
       il degrado no
    ③ «conta DOVE sta la riga nella fonte»              → falsificata (la coda
       prende il punteggio piu' alto)
⇒ **La causa dell'incidente originale — «EXIT=0.» quarantinato sulla porta CLI
con la source vera — resta IGNOTA, e la dichiaro invece di sceglierne una
quarta.** Cio' che resta da provare, per chi la prende: la porta e' diversa
(CLI `verimem save` contro `run_validation_gate`) e la source vera e'
**tabellare** (path, percentuali, `+++++`), non prosa. Sono due variabili non
ancora separate, e finche' non lo sono nessuna delle due e' la causa.

✅ **CIO' CHE QUESTO BANCO STABILISCE, e non e' poco**: su fonti da 60 a 5380
caratteri, con l'informazione in testa o in fondo, **il gate distingue il vero
dal falso in 3 regimi su 3**. E' un risultato **a favore del prodotto**, ed e'
il controllo che rende leggibile l'unico difetto misurato in questo giro (il
frammento da 7 caratteri, banco precedente).

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: riempitivo di prosa tecnica ripetuta, non un documento vero -
una fonte lunga e VARIA potrebbe comportarsi altrimenti; 512 e' il limite
dichiarato dal messaggio, **non letto nella configurazione**; non misuro quale
porzione il modello abbia effettivamente visto, solo l'esito.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-fonte-lunga-e-troncata-e-conta-dove-sta-il-pezzo.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

#: la riga che sostiene il claim
RIGA = "La suite riporta 21 passed, 2 skipped e termina con EXIT=0.\n"

#: riempitivo: prosa tecnica plausibile, senza numeri che possano confondersi
#: con quelli della riga sopra.
_ZEPPA = (
    "Il modulo di ingestione normalizza i percorsi prima di aprirli e registra "
    "ogni apertura nel giornale delle operazioni. La procedura di avvio verifica "
    "che la cartella dei dati sia scrivibile e che il file di configurazione sia "
    "leggibile, poi prepara le strutture in memoria. Le voci del giornale sono "
    "ruotate quando superano la dimensione prevista dalla politica di conservazione. "
)
LUNGA_TESTA = RIGA + _ZEPPA * 14
LUNGA_CODA = _ZEPPA * 14 + RIGA
CORTA = RIGA

VERO = "La suite termina con EXIT=0."
FALSO = "La suite termina con EXIT=1."

REGIMI = [
    ("fonte CORTA (controllo)", CORTA),
    ("LUNGA, riga in TESTA", LUNGA_TESTA),
    ("LUNGA, riga in CODA", LUNGA_CODA),
]


def _gate(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az == "persist", g


def main():
    print("  %-26s %6s   %-9s %8s   %-9s %8s  %s"
          % ("regime", "car.", "VERO", "ground", "FALSO", "ground", "verdetto"))
    print("  " + "-" * 94)
    for nome, fonte in REGIMI:
        pv, gv = _gate(VERO, fonte)
        pf, gf = _gate(FALSO, fonte)
        if pv and not pf:
            verdetto = "🟢 distingue"
        elif not pv and not pf:
            verdetto = "🔴 cade anche il VERO"
        elif pv and pf:
            verdetto = "🔴 passa anche il FALSO"
        else:
            verdetto = "🔴🔴 ROVESCIATO"
        print("  %-26s %6d   %-9s %8s   %-9s %8s  %s"
              % (nome, len(fonte), "passa" if pv else "CADE",
                 ("%.1f" % gv) if gv is not None else "None",
                 "passa" if pf else "cade",
                 ("%.1f" % gf) if gf is not None else "None", verdetto))

    print("\n=== COME SI LEGGE ===")
    print("  L'unica variabile fra le due righe LUNGHE e' DOVE sta la riga che")
    print("  sostiene il claim: stesso testo, stessa lunghezza, ordine invertito.")
    print("  Se TESTA passa e CODA no, la fonte e' troncata e il gate giudica")
    print("  contro una fonte PARZIALE senza dirlo a chi scrive.")
    print("  ⚠️ La colonna FALSO separa «non vede» da «lascia passare»: sono due")
    print("     difetti diversi e chiedono cure opposte.")


main()
