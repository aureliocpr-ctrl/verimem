"""R10 bis — LA CURVA DEL PAVIMENTO: esiste una taratura che vale la pena accendere?

    python scripts/banco_curva_pavimento.py it-en
    python scripts/banco_curva_pavimento.py en-it

DA DOVE NASCE. Alle 20:32 avevo chiuso R10 con «accendere non conviene: costa il 55,1%
delle risposte vere». @lead-audit ha obiettato, e ha ragione: il meccanismo FUNZIONA
(10 query fuori dominio zittite su 10) e quello che e' sbagliato e' il VALORE — `0,8805`
sta sopra i best delle domande vere (`0,809`-`0,864`). ⇒ la domanda giusta non e' «acceso
o spento» ma «ESISTE UN VALORE che separa le due popolazioni?».

CRITERIO D'ACCENSIONE (dato da @lead-audit, scritto qui PRIMA di eseguire):
    esiste una soglia con  vere perse <= 10%  E  fuori-dominio zittiti >= 80%  ?
    se SI -> si accende di default con quel valore (TDD, misura prima/dopo, cella)
    se NO -> resta spento CON IL NUMERO SCRITTO NELLA VETRINA

UNA SOLA PASSATA, POI SI SIMULA. Il pavimento taglia i risultati DOPO il top-k
(`client.py:1267`), quindi da una passata senza pavimento — dove per ogni query si
registrano gli score dei 10 risultati e lo score del fatto atteso — ogni soglia si ottiene
per confronto, senza rifare 14 volte 90 interrogazioni.

🔑 CONTROLLO CHE FERMA: la simulazione a `0,8805` DEVE riprodurre i numeri gia' misurati
alle 20:32 — IT `24/38`, EN `14/31`, fuori dominio `10/10`. Se non li riproduce, la
simulazione sta misurando un'altra cosa e il banco si ferma senza stampare la curva.

⚠️ IL PAVIMENTO AUTO NON E' LO STESSO NUMERO OGNI VOLTA. Tre stime sullo stesso store:
`0,8853` (31/08), `0,8797` (31/08, daemon caldo), `0,8805` (oggi). ⇒ se un valore va
acceso, va acceso come NUMERO FISSO, non come `auto`: `auto` cambia fra esecuzioni.

⚠️ RERANK SPENTO (`ENGRAM_RECALL_RERANK=0`), due ordini, processi separati.

PREDIZIONE SCRITTA PRIMA (02/09 20:47, ws1):
  (1) UN VALORE CHE SODDISFA ENTRAMBE ESISTE, e sta fra `0,78` e `0,80`: le mie 10 query
      fuori dominio sono lontane per costruzione (cucina, botanica, calcio, meteo) mentre
      le domande vere derivano dai fatti, quindi le due popolazioni non dovrebbero
      sovrapporsi in quella banda.
  (2) alla soglia scelta le vere perse stanno sotto il 10% E i fuori-dominio zittiti sopra
      l'80%.
⚠️ SE LA (1) SI AVVERA, IL MERITO PUO' ESSERE DEL BANCO E NON DEL PRODOTTO: un
fuori-dominio scelto lontano e' facile da separare. Il caso vero e' la domanda VICINA a cui
lo store non sa rispondere, e QUELLA POPOLAZIONE QUI NON C'E'. Va detto accanto al numero.
"""
import os
import re
import sqlite3
import sys
from pathlib import Path

_ORDINE = (sys.argv[1] if len(sys.argv) > 1 else "it-en").lower()
for _v in ("ENGRAM_GROUNDING_BACKEND", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_MIN_RELEVANCE",
           "ENGRAM_GATEWAY_MIN_RELEVANCE"):
    os.environ.pop(_v, None)
os.environ["ENGRAM_RECALL_RERANK"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.config import CONFIG  # noqa: E402

K = 10
N_PER_LINGUA = 40
#: griglia grossa 0,75-0,88 a passi di 0,01; col secondo argomento `fine` si stringe a
#: 0,825-0,860 a passi di 0,002, per misurare QUANTO E' LARGA la finestra che passa —
#: un valore che funziona solo in un centesimo e' fragile, e la larghezza va misurata.
_FINE = len(sys.argv) > 2 and sys.argv[2].lower() == "fine"
SOGLIE = ([0.825 + 0.002 * i for i in range(18)] if _FINE
          else [0.75 + 0.01 * i for i in range(14)])
RIFERIMENTO = 0.8805                                    # il valore misurato alle 20:32
ATTESO = {"it": (24, 38), "en": (14, 31), "fuori": (10, 10)}

_IT_STOP = {"il", "lo", "la", "i", "gli", "le", "di", "che", "non", "per", "con", "sono",
            "della", "dei", "alla", "una", "un", "nel", "sulla", "come"}
_EN_STOP = {"the", "of", "and", "is", "are", "to", "with", "that", "for", "not", "this",
            "from", "was", "were", "has", "have", "in", "on", "by", "as"}

_FUORI_DOMINIO = [
    "ricetta carbonara guanciale pecorino uova",
    "potatura vite settembre grappoli maturazione",
    "formazione calcio centrocampo difesa punizione",
    "previsione meteo pioggia domani pomeriggio nuvole",
    "cambio olio motore filtro chilometri tagliando",
    "accordatura chitarra corde plettro capotasto",
    "lievito madre impasto pizza forno lievitazione",
    "vaccinazione gatto richiamo veterinario libretto",
    "biglietto treno prenotazione posto finestrino",
    "cucitura orlo pantaloni ago filo macchina",
]


def lingua(testo):
    p = set(re.findall(r"[a-zà-ù']+", testo.lower()))
    a, b = len(p & _IT_STOP), len(p & _EN_STOP)
    return "it" if a > b else ("en" if b > a else "?")


def token6(testo):
    tok = re.findall(r"[\w\-.]{3,}", testo)
    if not tok:
        return []
    return sorted(sorted(set(tok), key=tok.index), key=len, reverse=True)[:6]


def campiona():
    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT proposition FROM facts WHERE proposition IS NOT NULL "
        "AND length(proposition) BETWEEN 60 AND 300"
    ).fetchall()
    con.close()
    it, en = [], []
    for (p,) in righe:
        p = str(p)
        lg = lingua(p)
        if lg == "it" and len(it) < N_PER_LINGUA:
            it.append(p)
        elif lg == "en" and len(en) < N_PER_LINGUA:
            en.append(p)
        if len(it) >= N_PER_LINGUA and len(en) >= N_PER_LINGUA:
            break
    return it, en


def passata(mem, fatti):
    """Per ogni fatto: (score del fatto atteso o None, best score dei k risultati)."""
    fuori = []
    for f in fatti:
        tk = token6(f)
        if not tk:
            continue
        res = mem.search(" ".join(tk), k=K)
        atteso, best = None, 0.0
        for x in res:
            s = float(x.get("score") or 0.0)
            best = max(best, s)
            if (x.get("text") or "")[:60].strip() == f[:60].strip():
                atteso = s
        fuori.append((atteso, best))
    return fuori


def conta(dati, soglia):
    """(vere perse, denominatore) e (rumore tolto, denominatore) a quella soglia."""
    perse = perse_n = tolto = tolto_n = 0
    for atteso, best in dati:
        if atteso is not None:
            perse_n += 1
            perse += (atteso < soglia)
        else:
            tolto_n += 1
            tolto += (best < soglia)
    return (perse, perse_n), (tolto, tolto_n)


def main():
    mem = Memory(CONFIG.semantic_db)
    # 🔑 DA CHE ALBERO STIAMO LEGGENDO: nel worktree si importa il worktree, da
    # uno script lanciato altrove si importa l albero condiviso. Un banco che non
    # lo dichiara puo misurare un codice diverso da quello che credi (@ws2, 03/09).
    print(f"IMPORT DA {verimem.__file__}", flush=True)
    print(f"verimem {verimem.__version__} | rerank=OFF | ordine={_ORDINE} | "
          f"{N_PER_LINGUA} fatti per lingua | k={K} | soglie {SOGLIE[0]:.3f}-{SOGLIE[-1]:.3f}",
          flush=True)
    it, en = campiona()
    if _ORDINE == "en-it":
        d_en, d_it = passata(mem, en), passata(mem, it)
    else:
        d_it, d_en = passata(mem, it), passata(mem, en)
    d_fd = [(None, max((float(x.get("score") or 0.0) for x in mem.search(q, k=K)),
                       default=0.0)) for q in _FUORI_DOMINIO]

    # --- CONTROLLO CHE FERMA: la simulazione deve riprodurre la misura delle 20:32
    (pi, pin), _ = conta(d_it, RIFERIMENTO)
    (pe, pen), _ = conta(d_en, RIFERIMENTO)
    zit = sum(1 for _, b in d_fd if b < RIFERIMENTO)
    reale = {"it": (pi, pin), "en": (pe, pen), "fuori": (zit, len(d_fd))}
    print(f"  controllo a {RIFERIMENTO}: {reale}  atteso {ATTESO}", flush=True)
    if reale != ATTESO:
        print("STOP — la simulazione NON riproduce la misura diretta delle 20:32: sta "
              "misurando un'altra cosa. La curva non viene stampata.", flush=True)
        return 2
    print("  controllo PASSATO: la simulazione riproduce la misura diretta.", flush=True)

    print("  soglia   IT perse        EN perse        TOTALE perse    fuori-dom zittiti",
          flush=True)
    buoni = []
    for t in SOGLIE:
        (pi, pin), _ = conta(d_it, t)
        (pe, pen), _ = conta(d_en, t)
        z = sum(1 for _, b in d_fd if b < t)
        tot, totn = pi + pe, pin + pen
        perc, zperc = (tot / totn * 100 if totn else 0), z / len(d_fd) * 100
        ok = (perc <= 10.0 and zperc >= 80.0)
        if ok:
            buoni.append((t, perc, zperc))
        print(f"  {t:.3f}   {pi:>2}/{pin} ({pi / pin * 100:5.1f}%)  "
              f"{pe:>2}/{pen} ({pe / pen * 100:5.1f}%)  "
              f"{tot:>2}/{totn} ({perc:5.1f}%)  {z:>2}/{len(d_fd)} ({zperc:5.1f}%)"
              f"{'   <-- CRITERIO SODDISFATTO' if ok else ''}", flush=True)
    print(f"RIGA ordine={_ORDINE} soglie_che_soddisfano={[(round(t, 3), round(p, 1), round(z, 1)) for t, p, z in buoni]}",
          flush=True)
    print("CRITERIO (dato da lead-audit, scritto prima): vere perse <= 10% E "
          "fuori-dominio zittiti >= 80%.", flush=True)
    print("PREDIZIONE (scritta prima): un valore esiste, fra 0,78 e 0,80. ⚠️ Se si avvera, "
          "il merito puo' essere del banco: il fuori-dominio VICINO qui non c'e'.",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
