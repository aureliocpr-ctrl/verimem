"""`as_of` promette «cio' che era CORRENTE in quel momento». Tre celle, e la
terza e' quella che distingue una promessa da una tautologia.

LA PROMESSA, dallo schema MCP: *«epoch seconds: dossier of what was
known/current at that moment»*. E dal sorgente, `temporal_context.py:218`:

    i fatti asseriti prima di `when` (`asserted_at`, con `created_at` come
    ripiego) e NON ancora superseduti a quel punto (`superseded_at` dopo
    `when` conta come ancora corrente).

⇒ Tre affermazioni distinte, e servono tutte e tre per dire che regge:
  ① senza `as_of` torna la versione CORRENTE (la nuova)
  ② con `as_of` a un istante PRIMA della supersessione torna la VECCHIA
  ③ con `as_of` PRIMA della prima scrittura non torna NIENTE

🔑 Senza la ③ le altre due non provano un viaggio nel tempo: proverebbero solo
che qualcosa cambia. La ③ e' la cella che distingue «il filtro guarda le date»
da «il filtro restituisce l'altra riga».

🚨 E LA COPERTURA C'ERA GIA', a un ALTRO LIVELLO — lo scrivo prima del
risultato perche' cambia cosa vale questo banco.
`tests/test_deep_recall_asof.py::test_recall_as_of_reconstructs_the_past`
presidia tutte e tre le celle, ③ compresa (*«BEFORE anything was asserted:
empty»*), chiamando **`recall_as_of` direttamente**. Il mio primo sweep non
l'aveva trovata: cercavo `as_of` e «vuoto» sulla STESSA RIGA, e li' l'assert e'
`feb == []`, due righe piu' sotto. Ottava volta in una notte che il difetto sta
nel misuratore — stavolta nel misuratore della COPERTURA.
⚖️ COSA AGGIUNGE ALLORA QUESTO BANCO: il livello. Il test esistente misura la
FUNZIONE; qui si passa dalla porta dell'SDK (`Memory.search(as_of=...)`), che
e' la superficie da cui un utente ci arriva, e la supersessione non e' forzata
dal test ma AVVIENE da se'. *Il livello a cui misuri decide il verdetto*: sono
due misure diverse della stessa promessa, e questa non sostituisce quella.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: la supersessione deve essere AVVENUTA —
il vecchio deve risultare superseduto. Se non lo fosse, non ci sarebbero due
ere da distinguere e ogni cella qui sotto parlerebbe di un fenomeno che non
esiste.
⚠️ IL CRITERIO DI RICONOSCIMENTO SONO GLI ID, non il testo. Un'ora fa un token
derivato dalla proposizione era «di» — una preposizione presente in ogni riga —
e il banco stava per pubblicare un finding falso. Gli id vengono dalla ricevuta
della scrittura e si confrontano con gli id della risposta: univoci per
costruzione.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, SDK in-process, giudice locale assente.
Le pause fra le scritture sono REALI e servono: senza, le tre ere cadrebbero
nello stesso istante e `as_of` non avrebbe niente da separare. Lo store di
Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-il-viaggio-nel-tempo-e-le-sue-tre-celle.py
"""

from __future__ import annotations

import json
import subprocess
import sys

DOMANDA = "quanto e' la penale del contratto Rossi"

FIGLIO = r'''
import json, os, sys, tempfile, time
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem.client import Memory

domanda = sys.argv[1]
m = Memory(os.path.join(tempfile.mkdtemp(), "s.db"))

t_prima = time.time()
time.sleep(0.3)

vecchio = m.add("La penale del contratto Rossi e' 120 euro al giorno.",
                source="Contratto Rossi, articolo 7: penale di 120 euro al giorno.",
                topic="tempo/penale")
id_vecchio = vecchio.get("id") if isinstance(vecchio, dict) else None

time.sleep(0.3)
t_mezzo = time.time()
time.sleep(0.3)

nuovo = m.add("La penale del contratto Rossi e' 200 euro al giorno.",
              source="Contratto Rossi, atto integrativo: penale di 200 euro al giorno.",
              topic="tempo/penale")
id_nuovo = nuovo.get("id") if isinstance(nuovo, dict) else None

# Supersessione ESPLICITA, se l'automatismo non l'ha gia' fatta.
superseduto_da = None
try:
    f = m.semantic.get(id_vecchio)
    superseduto_da = getattr(f, "superseded_by", None)
except Exception as e:
    superseduto_da = f"ERRORE {type(e).__name__}"
if not superseduto_da and hasattr(m.semantic, "supersede"):
    try:
        m.semantic.supersede(id_vecchio, id_nuovo)
        f = m.semantic.get(id_vecchio)
        superseduto_da = getattr(f, "superseded_by", None)
    except Exception as e:
        superseduto_da = f"ERRORE supersede {type(e).__name__}"

def ids(**kw):
    hits = m.search(domanda, k=10, **kw)
    fuori = []
    for h in hits:
        f = h[0] if isinstance(h, (tuple, list)) else h
        fuori.append(f.get("id") if isinstance(f, dict)
                     else getattr(f, "id", None))
    return [x for x in fuori if x]

print(json.dumps({
    "id_vecchio": id_vecchio, "id_nuovo": id_nuovo,
    "superseduto_da": str(superseduto_da),
    "senza_as_of": ids(),
    "as_of_mezzo": ids(as_of=t_mezzo),
    "as_of_prima": ids(as_of=t_prima),
}, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO, DOMANDA],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-500:]}")
        return 1
    d = json.loads(p.stdout.strip().splitlines()[-1])
    vec, nuo = d["id_vecchio"], d["id_nuovo"]

    def eti(lista):
        m = {vec: "VECCHIO", nuo: "NUOVO"}
        return [m.get(x, x[:8]) for x in lista] or ["(vuoto)"]

    print(f"  id vecchio={vec}  id nuovo={nuo}")
    print(f"  il vecchio risulta superseduto da: {d['superseduto_da']}")
    print(f"\n  senza as_of        -> {eti(d['senza_as_of'])}")
    print(f"  as_of PRIMA della supersessione -> {eti(d['as_of_mezzo'])}")
    print(f"  as_of prima di TUTTO            -> {eti(d['as_of_prima'])}")

    superseduta = d["superseduto_da"] not in ("None", "", "null")
    print(f"\n  [1] CONTROLLO — la supersessione e' AVVENUTA: "
          f"{'SI' if superseduta else 'NO'}")
    if not superseduta:
        print("      CONTROLLO CADUTO: le due versioni convivono, non ci sono")
        print("      due ere da distinguere e nessuna cella qui sotto misura un")
        print("      viaggio nel tempo. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    ok1 = nuo in d["senza_as_of"] and vec not in d["senza_as_of"]
    ok2 = vec in d["as_of_mezzo"] and nuo not in d["as_of_mezzo"]
    ok3 = not d["as_of_prima"]

    print(f"     ① senza as_of torna SOLO il corrente        : "
          f"{'🟢 SI' if ok1 else '🔴 NO'}")
    print(f"     ② as_of prima della supersessione: il VECCHIO: "
          f"{'🟢 SI' if ok2 else '🔴 NO'}")
    print(f"     ③ as_of prima di tutto: NIENTE              : "
          f"{'🟢 SI' if ok3 else '🔴 NO'}")

    if ok1 and ok2 and ok3:
        print("\n     🟢 LA PROMESSA REGGE su tutte e tre. ⚠️ Ed e' la ③ a")
        print("     renderla non banale: senza, le altre due proverebbero solo")
        print("     che qualcosa cambia, non che il filtro guardi le DATE.")
    else:
        print("\n     🔴 La promessa «what was current at that moment» non regge")
        print("     su tutte le celle. ⚠️ Prima di attribuirlo al prodotto:")
        print("     rileggi il sorgente — se contraddice questa misura, il")
        print("     primo indiziato e' la misura (costato una volta stanotte).")

    print("\n  ⚠️ LIMITI: due versioni di UN fatto, una domanda, pause di 0,3 s.")
    print("     NON misura `asserted_at` esplicito (qui e' `None` e si usa il")
    print("     ripiego `created_at`), ne' catene di supersessione piu' lunghe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
