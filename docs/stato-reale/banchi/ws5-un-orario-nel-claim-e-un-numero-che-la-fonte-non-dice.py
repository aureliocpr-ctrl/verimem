r"""Due modi di scrivere la STESSA data, due verdetti opposti: la politica e' sulla FORMA.

Non l'ho cercato: e' emerso **usando il prodotto**. Salvando il fatto di un altro
banco — la cui frase dice «*il 28/08 alle 20:58*» — il gate ha alzato un avviso
`L4.2` su **58**, con questa spiegazione::

    L4.2 — il claim riusa un numero della fonte riferendolo a un'altra grandezza:
    58 qui e' «(nessuna parola accanto)», nella fonte «(solo parole grammaticali
    accanto)»

⚠️ Non ha trovato una discordanza: ha trovato **due assenze** e le ha trattate come
una. Ma l'avviso e' il sintomo; la causa e' a monte.

LA CAUSA, misurata su `extract_quantities`::

    data ISO        «2026-08-10»          []                      potata ✔
    data IT         «10/08/2026»          []                      potata ✔
    data SENZA anno «28/08»               [8.0, 28.0]             🔴 NON potata
    orario hh:mm    «20:58»               [20.0, 58.0]            🔴 NON potata
    orario + data   «28/08 alle 20:58»    [8.0, 20.0, 28.0, 58.0] 🔴 QUATTRO
    durata (CTRL)   «190 secondi»         [190.0]                 giusto ✔

⇒ `_spans_delle_date` copre le date **complete** e non quelle **senza anno**, e non
copre affatto gli **orari**. 🪞 Ed e' la forma che il commento di quella stessa
funzione dichiarava di non voler ripetere: «*un controllo per-numero ne prenderebbe
uno e lascerebbe gli altri — che e' esattamente il modo in cui la copertura degli
anni era rimasta a meta', e ripeterlo qui sarebbe rifare lo stesso errore con la sua
diagnosi in mano*». **La copertura e' rimasta a meta' in un'altra dimensione.**

🔴 ESITO ALLA PORTA — **la stessa data, scritta in due modi, riceve due verdetti
opposti**::

    caso                           esito    ground   layer
    A  «... alle 20:58»            CADE       99.8   L4.1     l'ora non e' nella fonte
    B  senza orario      (CTRL)    passa      99.9   -        identico ad A meno l'ora
    C  orario, fonte avara         CADE       98.8   L4.1
    D  numero inventato (CTRL-)    CADE       99.9   L4.1     il banco sa dire di no
    E  «... il 2026-08-10»         passa      99.5   -        🔑 NON sostenuta, PASSA
    F  «... il 28/08»              CADE       99.7   L4.1     🔑 NON sostenuta, CADE

✅ **I due controlli reggono**: `B` passa (senza l'ora, tutto il resto e' sostenuto) e
`D` cade (`L4.1`, un grounding inventato) ⇒ il banco distingue, non e' un regime in
cui tutto passa o tutto cade.

🪞 **LA MIA PREDIZIONE ERA SBAGLIATA, e la scrivo perche' e' il punto**. Avevo
previsto «*rumore, non veto: i numeri spuri trovano per caso un gemello nella fonte*».
**`A` cade.** E la controipotesi che mi ero imposta — «*se l'ora non e' nella fonte,
`L4.1` ha ragione a fermarla*» — e' quella che ha prodotto il reperto vero: l'ho
messa alla prova con `E` ed `F`, e sono loro a decidere.

🔑 **`E` ed `F` sono la STESSA COSA**: una marca temporale che la fonte non contiene.
`E` passa, `F` cade. L'unica differenza e' **come e' scritta**. ⇒ **Il difetto non e'
che il gate fermi un'ora non sostenuta: e' che la politica dipende dal FORMATO invece
che dal significato.** Scrivi `2026-08-10` e passi; scrivi `28/08` — la forma che
usiamo tutti i giorni — e vieni quarantinato.

⇒ E il grounding e' **99.5-99.8 in tutti i casi**: il giudice e' d'accordo ovunque.
A separare `E` da `F` c'e' **solo la potatura sintattica**.

📌 **Si salda col reperto sul rosso di @ws8** (`1fffc4d9`), ed e' la stessa lista::

    «riga 999»  →  POTATO      ⇒ L4.1 non vede un numero INVENTATO   (manca un falso)
    «28/08»     →  NON potato  ⇒ L4.1 ferma una data VERA            (ferma un vero)

⇒ **Una sola lista di forme, due errori opposti.** E' la classe «*un criterio
sintattico su un fenomeno semantico sbaglia in entrambe le direzioni*»: qui si vede
in tutte e due contemporaneamente.

⇒ **Portata pratica**: e' la forma con cui scriviamo i fatti ogni giorno («*il commit
e' del 28/08 alle 20:58*»). La cura sta **a monte** — la copertura di
`_spans_delle_date` — non nell'avviso `L4.2`, che ne e' solo il sintomo.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) · `ground_write=True` ·
porta `run_validation_gate` · daemon attivo, nessun `None` nel grounding.
⚖️ PUNTI DEBOLI: sei claim, due fonti. **Non ho misurato sul corpus** quanti fatti
contengano un orario o una data breve, quindi **non dico quanto sia frequente** —
dico che la forma e' la nostra. E `C` (fonte avara) non isola nulla da solo: e' `E`
contro `F` a portare il verdetto.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-un-orario-nel-claim-e-un-numero-che-la-fonte-non-dice.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402
from verimem.quantity_match import extract_quantities, _spans_delle_date  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

#: una riga di ricevuta della CLI, verbatim — ricca di numeri, come sono le fonti vere
FONTE = ("admitted id=f9e44ce101ff topic='verimem/numero-inventato-alla-porta' "
         "grounding_score=99.98452758789062 judged=True status=model_claim stored=True")
#: la stessa cosa detta in prosa, POVERA di numeri
FONTE_AVARA = "Il fatto e' stato ammesso e il giudice gli ha dato 99.98452758789062."

BASE = "Il fatto e' stato ammesso con grounding 99.98"

CASI = [
    ("A con orario", BASE + " alle 20:58.", FONTE, "CADE"),
    ("B senza orario (CTRL)", BASE + ".", FONTE, "passa"),
    ("C orario + fonte avara", BASE + " alle 20:58.", FONTE_AVARA, "CADE"),
    ("D numero inventato (CTRL-)", "Il fatto e' stato ammesso con grounding 44.12.",
     FONTE, "CADE"),
    # ⚖️ E ed F sono LA CONTROIPOTESI, ed e' da loro che viene il verdetto: se l'ora
    # non e' nella fonte, `L4.1` ha ragione a fermarla — e allora ogni altra marca
    # temporale non sostenuta deve cadere allo stesso modo. Se la data COMPLETA
    # passa e quella SENZA ANNO no, il difetto non e' il veto: e' che due scritture
    # della stessa cosa ricevono due politiche opposte.
    ("E data completa non sost.", BASE + " il 2026-08-10.", FONTE, "passa"),
    ("F data senza anno non sost.", BASE + " il 28/08.", FONTE, "CADE"),
]

ORARI = [
    ("data ISO", "Il fatto e' del 2026-08-10."),
    ("data IT", "Il fatto e' del 10/08/2026."),
    ("data SENZA anno", "Il commit e' del 28/08."),
    ("orario hh:mm", "Il test e' diventato rosso alle 20:58."),
    ("orario + data", "Il commit e' del 28/08 alle 20:58."),
    ("durata (CTRL)", "Il banco costa 190 secondi."),
]


def main():
    print("① LA CAUSA — cosa estrae il lato claim\n")
    print("  %-18s %-40s %-24s %s" % ("caso", "testo", "quantita'", "span-data"))
    print("  " + "-" * 96)
    for nome, testo in ORARI:
        q = sorted(v for _, v in extract_quantities(testo))
        print("  %-18s %-40s %-24s %s" % (nome, testo, q or "[]",
                                          _spans_delle_date(testo) or "[]"))

    print("\n② L'EFFETTO ALLA PORTA — la stessa marca temporale, scritta in due modi\n")
    print("  %-28s %-8s %8s  %s" % ("caso", "esito", "ground", "layer deterministici"))
    print("  " + "-" * 78)
    esiti = {}
    for nome, claim, fonte, atteso in CASI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=fonte, grounding_llm=None,
                                ground_write=True)
        g = getattr(r, "grounding_score", None)
        ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
              if isinstance(w, dict)]
        det = [x for x in ws if x not in NON_DETERMINISTICI]
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        esito = "passa" if az == "persist" else "CADE"
        esiti[nome[0]] = (esito, det)
        print("  %-28s %-8s %8s  %s %s"
              % (nome, esito, ("%.1f" % g) if g is not None else "None",
                 ", ".join(det) or "-", "✔" if esito == atteso else "🔴 ATTESO " + atteso))

    print("\n=== SINTESI ===")
    b_esito, _ = esiti.get("B", ("?", []))
    d_esito, _ = esiti.get("D", ("?", []))
    e_esito, _ = esiti.get("E", ("?", []))
    f_esito, f_layer = esiti.get("F", ("?", []))
    if b_esito != "passa" or d_esito != "CADE":
        print("  ⚠️ I CONTROLLI NON REGGONO (B=%s, D=%s): il verdetto non e' leggibile."
              % (b_esito, d_esito))
    elif e_esito == "passa" and f_esito == "CADE":
        print("  🔴🔴 LA STESSA DATA, DUE VERDETTI: «2026-08-10» non sostenuta PASSA,")
        print("       «28/08» non sostenuta CADE (%s)." % (", ".join(f_layer) or "-"))
        print("       ⇒ la politica e' sulla FORMA della scrittura, non sul significato.")
    elif e_esito == f_esito:
        print("  🟢 E ed F concordano (%s): la politica NON dipende dal formato," % e_esito)
        print("     e la mia lettura cade.")
    else:
        print("  ⚠️ esito inatteso: E=%s F=%s" % (e_esito, f_esito))


main()
