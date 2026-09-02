"""R10 — ACCENDERE L'ASTENSIONE SU `search` CONVIENE? Quanto costa in risposte vere.

    python scripts/banco_astensione_search.py it-en
    python scripts/banco_astensione_search.py en-it

IL PRECEDENTE, letto PRIMA di scrivere il banco (`verimem/relevance_floor.py`, docstring
di `env_floor`). La misura del 2026-07-29, venti domande sullo store vivo:

    gate OFF   0 wrong abstentions   2 expected facts missed   0/8 caught   1.22s
    gate ON    0 wrong abstentions   2 expected facts missed   8/8 caught   4.21s

⚠️ QUELLA MISURA E' PASSATA DA `explain`, che ha il gate cross-encoder. `search` ha SOLO
il pavimento bi-encoder. Lo stesso docstring dichiara perche' il default `auto` non e'
stato esteso a `search`/`recall`/`ask`: «turning abstention on by default for a path
nobody measured is the shape of the 2026-07-30 mistake» — l'incidente `max(floor,
noise_floor)`, scritto, misurato e RITIRATO perche' mutava la mappa dell'ignoranza.
⇒ QUESTO BANCO MISURA ESATTAMENTE IL PERCORSO CHE QUELLA DECISIONE DICHIARA NON MISURATO.

DUE BRACCI, stessa query, stesso store, stesso processo:
    A  mem.search(q, k=10)                       il default di oggi (nessun pavimento)
    B  mem.search(q, k=10, min_relevance=<pav>)  il pavimento che `auto` calcola

TRE MISURE:
  (1) VERE PERSE      A trovava il fatto atteso entro k, B non lo trova piu'.
                      E' il costo dell'accensione, pagato da chi una risposta ce l'aveva.
  (2) RUMORE TOLTO    A NON trovava il fatto atteso ma restituiva comunque dei vicini,
                      B restituisce VUOTO. E' un «non lo so» al posto di un vicino
                      sbagliato — il beneficio dell'accensione.
  (3) CONTROLLO NEGATIVO FUORI DOMINIO: query su un dominio che nello store non c'e'.
                      A restituira' comunque dei vicini; B dovrebbe tacere.

⚠️ RERANK SPENTO in entrambi i bracci (`ENGRAM_RECALL_RERANK=0`): e' il regime che il
02/09 alle 19:31 ha dato ripetizioni IDENTICHE su due ordini. Processo nuovo a ogni
esecuzione (il breaker e' per-processo). Due ordini per falsificare la ripetibilita'.

🔑 CONTROLLO CHE FERMA: se il pavimento calcolato vale 0.0, il braccio B e' IDENTICO ad A
e il banco stampa «0 perse, 0 tolte» — un risultato che sembra ottimo e non misura nulla.
In quel caso il banco SI FERMA e lo dichiara.

PREDIZIONE SCRITTA PRIMA (02/09 20:26, ws1):
  (1) le VERE PERSE stanno sopra il 20% — molto peggio dello 0% del 29/07, perche' li'
      a decidere era il cross-encoder e qui c'e' solo la distanza coseno
  (2) il RUMORE TOLTO sta sopra il 50%
  (3) il CONTROLLO NEGATIVO: almeno l'80% delle query fuori dominio torna VUOTO con B.
      Se non torna vuoto, il pavimento non e' un filtro d'ignoranza e la (1) da sola
      non basta a dare un verdetto.
CONDIZIONE D'USCITA (scritta prima):
  perse <= 5%  E  rumore tolto >= 50%   -> accendere CONVIENE
  perse >= 20%                          -> accendere NON conviene
  in mezzo                              -> INCONCLUSO, serve una misura diversa
⚠️ In nessun caso questo banco accende alcunche': un default e' comportamento del
prodotto, e la decisione non e' di chi misura.
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
os.environ["ENGRAM_RECALL_RERANK"] = "0"          # regime ripetibile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.config import CONFIG  # noqa: E402

K = 10
N_PER_LINGUA = 40

_IT_STOP = {"il", "lo", "la", "i", "gli", "le", "di", "che", "non", "per", "con", "sono",
            "della", "dei", "alla", "una", "un", "nel", "sulla", "come"}
_EN_STOP = {"the", "of", "and", "is", "are", "to", "with", "that", "for", "not", "this",
            "from", "was", "were", "has", "have", "in", "on", "by", "as"}

#: Query FUORI DOMINIO: cucina, botanica, calcio, meteo. Lo store e' fatto di memoria,
#: gate, recall, rilasci. Se il pavimento serve a qualcosa, qui deve tacere.
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


def esito(mem, query, atteso, pavimento):
    """(trovato_A, trovato_B, vuoto_B) per una query."""
    a = mem.search(query, k=K)
    b = mem.search(query, k=K, min_relevance=pavimento)

    def dentro(res):
        return any((x.get("text") or "")[:60].strip() == atteso[:60].strip() for x in res)

    return dentro(a), dentro(b), (len(b) == 0)


def misura(mem, fatti, nome, pavimento):
    perse = perse_n = 0          # (1) A trovava, B no
    tolto = tolto_n = 0          # (2) A non trovava; B tace
    a_ok = 0
    for f in fatti:
        tk = token6(f)
        if not tk:
            continue
        ta, tb, vuoto = esito(mem, " ".join(tk), f, pavimento)
        a_ok += ta
        if ta:
            perse_n += 1
            perse += (not tb)
        else:
            tolto_n += 1
            tolto += vuoto
    print(f"  {nome}", flush=True)
    print(f"    braccio A (oggi)   recall@{K} {a_ok:>2}/{len(fatti)}", flush=True)
    if perse_n:
        print(f"    (1) VERE PERSE     {perse:>2}/{perse_n} "
              f"({perse / perse_n * 100:5.1f}%)  [A le trovava, B no]", flush=True)
    if tolto_n:
        print(f"    (2) RUMORE TOLTO   {tolto:>2}/{tolto_n} "
              f"({tolto / tolto_n * 100:5.1f}%)  [A sbagliava, B tace]", flush=True)
    return {"a_ok": (a_ok, len(fatti)), "perse": (perse, perse_n), "tolto": (tolto, tolto_n)}


def controllo_negativo(mem, pavimento):
    vuoti_a = vuoti_b = 0
    for q in _FUORI_DOMINIO:
        vuoti_a += (len(mem.search(q, k=K)) == 0)
        vuoti_b += (len(mem.search(q, k=K, min_relevance=pavimento)) == 0)
    n = len(_FUORI_DOMINIO)
    print(f"  CONTROLLO NEGATIVO fuori dominio ({n} query)", flush=True)
    print(f"    A tace {vuoti_a}/{n}   B tace {vuoti_b}/{n} "
          f"({vuoti_b / n * 100:5.1f}%)", flush=True)
    return (vuoti_a, vuoti_b, n)


def main():
    mem = Memory(CONFIG.semantic_db)
    pav = mem._auto_relevance_floor()
    print(f"verimem {verimem.__version__} | rerank=OFF | ordine={_ORDINE} | "
          f"{N_PER_LINGUA} fatti per lingua | k={K} | PAVIMENTO auto = {pav}", flush=True)
    if not pav:
        print("STOP — il pavimento calcolato vale 0.0: il braccio B sarebbe IDENTICO ad A "
              "e ogni numero qui sotto direbbe «nessuna perdita» senza misurare nulla. "
              "Il banco NON e' eseguibile in questo regime.", flush=True)
        return 2
    it, en = campiona()
    if _ORDINE == "en-it":
        b = misura(mem, en, "INGLESE", pav)
        a = misura(mem, it, "ITALIANO", pav)
    else:
        a = misura(mem, it, "ITALIANO", pav)
        b = misura(mem, en, "INGLESE", pav)
    cn = controllo_negativo(mem, pav)
    print(f"RIGA ordine={_ORDINE} pavimento={pav} it_a={a['a_ok']} it_perse={a['perse']} "
          f"it_tolto={a['tolto']} en_a={b['a_ok']} en_perse={b['perse']} "
          f"en_tolto={b['tolto']} fuori_dominio_vuoti_a_b_n={cn}", flush=True)
    print("PREDIZIONE (scritta prima): vere perse > 20% · rumore tolto > 50% · "
          "fuori dominio B tace >= 80%.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
