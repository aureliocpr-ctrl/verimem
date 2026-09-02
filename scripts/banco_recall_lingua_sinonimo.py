"""M2 — BASELINE del recall: la LINGUA e il SINONIMO, isolati in un 2x2.

    python scripts/banco_recall_lingua_sinonimo.py

⚠️ QUESTA NON E' LA RIPRODUZIONE DI UN NUMERO ESISTENTE, E' UNA MISURA NUOVA.
Il muro M2 mi e' stato assegnato come «il recall trova 9/10 in italiano e 5/10 in inglese».
Quei due numeri sono MIEI ma di un ALTRO fenomeno: sono le frasi false col soggetto scambiato
AMMESSE DAL GATE ALLA PORTA DI SCRITTURA (celle 03:33 e 05:04 del 02/09), non query che
trovano fatti. Il mio reperto sul RECALL e' un terzo numero ancora: con domande a parole
proprie il fatto atteso e' al primo posto 0 volte su 10 e presente entro k=100 in 3 casi su 10
(celle 02:54 e 03:15), e li' la lingua non era una variabile: era tutto italiano.
E «serve una parola DEL fatto, il sinonimo esatto fallisce» e' un reperto di ws6, non mio.
⇒ una baseline del recall per lingua NON ESISTE. Questa la crea.

DISEGNO 2x2 — isola DUE variabili invece di confonderle:
                       query con la PAROLA DEL FATTO   |   query con un SINONIMO
    store ITALIANO              A                      |            B
    store INGLESE               C                      |            D
Dodici fatti, ognuno scritto nelle due lingue; due store separati (uno per lingua) cosi' il
corpus di ciascuno e' monolingue e il confronto non e' inquinato. Per ogni fatto due query
nella lingua del suo store: una che contiene il termine chiave COME STA NEL FATTO, una che lo
sostituisce con un sinonimo e lascia tutto il resto uguale.
METRICA: il fatto atteso e' al PRIMO POSTO? (e, come secondo numero, entro k=10)

CONTROLLO POSITIVO CHE FERMA: le colonne A e C (parola del fatto) devono dare >= 10/12 al
primo posto, o il banco sta misurando un retrieval rotto e non conclude.

PREDIZIONE SCRITTA PRIMA (02/09 12:35):
    A (IT parola) 11-12/12   ·   B (IT sinonimo) 2-5/12
    C (EN parola) 10-12/12   ·   D (EN sinonimo) 2-5/12
cioe': il sinonimo pesa molto, la lingua sul RECALL pesa poco — perche' il divario di lingua
che ho misurato io era sul GATE, non sul recall.
CONDIZIONE D'USCITA:
    |A - C| <= 2   -> il recall NON e' cieco alla lingua: il muro M2 va riscritto, perche'
                      la cecita' alla lingua che ho misurato e' del GATE
    |A - C| >= 4   -> il muro regge anche sul recall, ed e' un fatto nuovo
    A - B >= 5     -> il sinonimo E' una barriera sul recall (conferma ws6 da un perimetro
                      indipendente: fatti miei, store miei)
"""
import json
import os
import sys
import tempfile
from pathlib import Path

_ORIG = {}
for v in ("ENGRAM_GROUNDING_BACKEND", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_MIN_RELEVANCE",
          "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR", "ENGRAM_GATEWAY_MIN_RELEVANCE"):
    _ORIG[v] = os.environ.pop(v, None)
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()          # PRIMA dell'import, store usa e getta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402

K = 10

# (fatto IT, query IT con la parola del fatto, query IT col sinonimo,
#  fatto EN, query EN con la parola del fatto, query EN col sinonimo)
CASI = [
    ("Il server di posta rifiuta i messaggi oltre venticinque megabyte.",
     "Cosa fa il server di posta con i messaggi grandi?",
     "Cosa fa il gestore di email con le comunicazioni voluminose?",
     "The mail server rejects messages above twenty-five megabytes.",
     "What does the mail server do with large messages?",
     "What does the email handler do with bulky communications?"),
    ("La cache viene svuotata ogni sei ore dal processo notturno.",
     "Quando viene svuotata la cache?",
     "Quando viene ripulita la memoria temporanea?",
     "The cache is emptied every six hours by the nightly process.",
     "When is the cache emptied?",
     "When is the temporary storage cleared?"),
    ("Il pannello mostra la temperatura media delle ultime dodici ore.",
     "Cosa mostra il pannello sulla temperatura?",
     "Cosa visualizza il cruscotto sul calore?",
     "The panel shows the average temperature of the last twelve hours.",
     "What does the panel show about temperature?",
     "What does the dashboard display about heat?"),
    ("Il contratto prevede una penale del tre per cento sui ritardi.",
     "Quale penale prevede il contratto sui ritardi?",
     "Quale sanzione stabilisce l'accordo sulle attese?",
     "The contract provides a three per cent penalty on delays.",
     "What penalty does the contract provide on delays?",
     "What fine does the agreement set on late deliveries?"),
    ("Il magazzino conserva le scorte per un massimo di novanta giorni.",
     "Per quanto il magazzino conserva le scorte?",
     "Per quanto il deposito custodisce le riserve?",
     "The warehouse keeps the stock for at most ninety days.",
     "How long does the warehouse keep the stock?",
     "How long does the depot store the reserves?"),
    ("La caldaia consuma quattro litri di gasolio all'ora a pieno regime.",
     "Quanto gasolio consuma la caldaia?",
     "Quanto combustibile brucia il bruciatore?",
     "The boiler consumes four litres of diesel per hour at full load.",
     "How much diesel does the boiler consume?",
     "How much fuel does the burner burn?"),
    ("Il corso dura settanta ore e rilascia un attestato finale.",
     "Quante ore dura il corso?",
     "Quante ore occupa il seminario?",
     "The course lasts seventy hours and grants a final certificate.",
     "How many hours does the course last?",
     "How many hours does the seminar take?"),
    ("Il ponte sopporta un carico massimo di trentadue tonnellate.",
     "Quale carico sopporta il ponte?",
     "Quale peso regge il viadotto?",
     "The bridge supports a maximum load of thirty-two tonnes.",
     "What load does the bridge support?",
     "What weight does the viaduct bear?"),
    ("La batteria si ricarica completamente in ottanta minuti.",
     "In quanto si ricarica la batteria?",
     "In quanto si rigenera l'accumulatore?",
     "The battery recharges fully in eighty minutes.",
     "How long does the battery take to recharge?",
     "How long does the accumulator take to replenish?"),
    ("Il regolamento vieta l'accesso ai visitatori dopo le venti.",
     "Cosa vieta il regolamento ai visitatori?",
     "Cosa proibisce la normativa agli ospiti?",
     "The rules forbid access to visitors after eight in the evening.",
     "What do the rules forbid to visitors?",
     "What does the policy prohibit to guests?"),
    ("Il motore raggiunge la coppia massima a duemilaquattrocento giri.",
     "A quanti giri il motore raggiunge la coppia massima?",
     "A quanti giri il propulsore tocca la forza torcente massima?",
     "The engine reaches maximum torque at two thousand four hundred revolutions.",
     "At what revolutions does the engine reach maximum torque?",
     "At what revolutions does the powerplant hit peak turning force?"),
    ("La sala accoglie duecentodieci persone sedute.",
     "Quante persone accoglie la sala?",
     "Quante persone ospita l'aula?",
     "The hall seats two hundred and ten people.",
     "How many people does the hall seat?",
     "How many people does the auditorium hold?"),
]


#: Frasi della STESSA forma dei fatti, con valori diversi: servono a rendere il banco
#: sensibile. Senza, dodici fatti a domini disgiunti danno 12/12 su tutti e quattro i bracci
#: (misurato: effetto SOFFITTO) e la baseline non puo' mostrare ne' peggioramenti ne'
#: miglioramenti — cioe' non serve alla catena.
_OGG_IT = ["il filtro", "la pompa", "il quadro", "il nastro", "la valvola", "il sensore",
           "il cavo", "la guarnizione", "il rullo", "la ventola", "il giunto", "la piastra"]
_OGG_EN = ["the filter", "the pump", "the board", "the belt", "the valve", "the sensor",
           "the cable", "the gasket", "the roller", "the fan", "the joint", "the plate"]
_AZ_IT = ["sostituito ogni", "controllato ogni", "tarato ogni", "lubrificato ogni",
          "pulito ogni", "collaudato ogni"]
_AZ_EN = ["replaced every", "checked every", "calibrated every", "lubricated every",
          "cleaned every", "tested every"]


def distrattori(n, lingua):
    ogg, az = (_OGG_IT, _AZ_IT) if lingua == "it" else (_OGG_EN, _AZ_EN)
    fuori = []
    i = 0
    while len(fuori) < n:
        o, a = ogg[i % len(ogg)], az[(i // len(ogg)) % len(az)]
        val = 3 + (i % 97)
        coda = "ore." if lingua == "it" else "hours."
        fuori.append(f"{o.capitalize()} viene {a} {val} {coda}" if lingua == "it"
                     else f"{o.capitalize()} is {a} {val} {coda}")
        i += 1
    return fuori


def costruisci(fatti, n_distrattori=0, lingua="it"):
    """Uno store NUOVO e monolingue per lingua, con `n_distrattori` frasi della stessa forma."""
    mem = Memory(Path(tempfile.mkdtemp()) / "s.db")
    for f in fatti:
        mem.add(f, topic="m2/baseline")
    for f in distrattori(n_distrattori, lingua):
        mem.add(f, topic="m2/rumore")
    return mem


def misura(mem, fatti, queries, nome):
    primo = entro_k = 0
    ranghi = []
    for i, q in enumerate(queries):
        r = mem.search(q, k=K)
        pos = -1
        for j, x in enumerate(r):
            if (x.get("text") or "")[:40].strip() == fatti[i][:40].strip():
                pos = j + 1
                break
        ranghi.append(pos)
        if pos == 1:
            primo += 1
        if pos > 0:
            entro_k += 1
    print(f"  {nome:<34} primo posto {primo:>2}/{len(queries)} | entro k={K} "
          f"{entro_k:>2}/{len(queries)} | ranghi {ranghi}", flush=True)
    return primo, entro_k, ranghi


def main():
    n = len(CASI)
    print(f"verimem {verimem.__version__} | {n} fatti, due store monolingui, k={K}", flush=True)
    it_f = [c[0] for c in CASI]
    en_f = [c[3] for c in CASI]
    tutto = {}

    for nd in (0, 200):
        etichetta = "SENZA distrattori (caso facile)" if nd == 0 else f"con {nd} DISTRATTORI"
        print(f"\n{'#' * 78}\n### {etichetta} — corpus {n + nd} fatti per store\n{'#' * 78}",
              flush=True)
        mem_it = costruisci(it_f, nd, "it")
        mem_en = costruisci(en_f, nd, "en")
        print("=== store ITALIANO ===", flush=True)
        a = misura(mem_it, it_f, [c[1] for c in CASI], "A  parola del fatto")
        b = misura(mem_it, it_f, [c[2] for c in CASI], "B  sinonimo")
        print("=== store INGLESE ===", flush=True)
        c = misura(mem_en, en_f, [c[4] for c in CASI], "C  parola del fatto")
        d = misura(mem_en, en_f, [c[5] for c in CASI], "D  sinonimo")

        print(f"{'':<16}{'parola del fatto':>20}{'sinonimo':>14}", flush=True)
        print(f"{'ITALIANO':<16}{a[0]:>18}/{n}{b[0]:>12}/{n}", flush=True)
        print(f"{'INGLESE':<16}{c[0]:>18}/{n}{d[0]:>12}/{n}", flush=True)
        ok = a[0] >= 10 and c[0] >= 10
        print(f"  CONTROLLO POSITIVO (A e C >= 10/12): "
              f"{'OK' if ok else 'ROTTO — non conclude'}", flush=True)
        print(f"  effetto LINGUA    |A-C| = {abs(a[0]-c[0])}   (<=2 non cieco alla lingua · "
              f">=4 il muro regge)", flush=True)
        print(f"  effetto SINONIMO   A-B  = {a[0]-b[0]}   C-D = {c[0]-d[0]}   (>=5 barriera)",
              flush=True)
        tutto[nd] = {"it_parola": a[0], "it_sinonimo": b[0], "en_parola": c[0],
                     "en_sinonimo": d[0], "controllo_positivo_ok": ok,
                     "it_parola_entro_k": a[1], "it_sinonimo_entro_k": b[1],
                     "en_parola_entro_k": c[1], "en_sinonimo_entro_k": d[1],
                     "ranghi": {"A": a[2], "B": b[2], "C": c[2], "D": d[2]}}

    print("\n" + "=" * 78, flush=True)
    print("PREDIZIONE (scritta prima, valeva per il caso SENZA distrattori): "
          "A 11-12 · B 2-5 · C 10-12 · D 2-5.", flush=True)
    print("⚠️ Un 12/12 su tutti e quattro i bracci e' EFFETTO SOFFITTO: una baseline satura "
          "non puo' mostrare\n   ne' peggioramenti ne' miglioramenti. I distrattori servono a "
          "questo, non ad allargare lo scope.", flush=True)
    print("=" * 78, flush=True)

    out = Path(__file__).resolve().parent.parent / "docs" / "stato-reale" / "m2_baseline.json"
    out.write_text(json.dumps({"n": n, "k": K, "per_distrattori": tutto},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"dati: {out}", flush=True)


if __name__ == "__main__":
    main()
