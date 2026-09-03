"""L'AVVISO C'E' GIA' ED E' ACCESO: quante volte marca, e quante volte marca a VUOTO.

    python scripts/banco_avviso_marcatura.py

DA DOVE NASCE. @lead-audit ha deciso la «terza via»: l'astensione su `search` non taglia
ma MARCA — la risposta si serve con un campo che dice «sotto il pavimento di confidenza».
**Quel campo esiste gia'**: `client.py:1469` `sotto_il_pavimento`, con `pavimento`,
`score_migliore`, `tagliati` e una nota che dice «I risultati sono qui sotto, non tagliati
— decidi tu». **Ed e' gia' acceso nel default**: provato alle 21:13 su tre query, esce su
tutte e tre — VERA, VICINA e LONTANA — perche' la soglia che usa e' il pavimento AUTO
(`0,8805`), che sta sopra il `best` di quasi tutto.

⇒ **il lavoro non e' implementare l'avviso: e' RICALIBRARE il numero che usa.**

IL CRITERIO DI @lead-audit, riportato qui PRIMA di eseguire:
    le 10 fuori dominio devono uscire marcate 10/10  ·  le vere marcate <= 6%

⚠️ LA GRANDEZZA GIUSTA E' IL `best`, NON LO SCORE DEL FATTO ATTESO. L'avviso guarda
`_best_prima` (`client.py:1266`), cioe' il MIGLIORE dei risultati: e' una proprieta' della
domanda, non del fatto che speravo di trovare. La curva delle 20:49 misurava l'altra cosa
— qui si misura quella che l'avviso usa davvero.

PREDIZIONE SCRITTA PRIMA (02/09 21:15, ws1):
  (1) a `0,8805` (oggi) le VERE marcate stanno SOPRA il 50% ⇒ l'avviso di oggi e' rumore:
      esce sulle risposte buone quanto sulle altre.
  (2) a `0,839` le VERE marcate stanno SOTTO il 6% ⇒ il criterio di @lead-audit e'
      soddisfatto DALLA RICALIBRAZIONE, non da codice nuovo.
  (3) le VICINE restano marcate poco (~3/17): l'avviso non le prende, ed e' il limite
      misurato alle 21:07 — la sovrapposizione fra vere e vicine.

⚠️ RERANK SPENTO, un processo, sola lettura, nessuna modifica al prodotto.
"""
import os
import re
import sqlite3
import sys
from pathlib import Path

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
OGGI = 0.8805
PROPOSTA = 0.839

_IT_STOP = {"il", "lo", "la", "i", "gli", "le", "di", "che", "non", "per", "con", "sono",
            "della", "dei", "alla", "una", "un", "nel", "sulla", "come"}
_EN_STOP = {"the", "of", "and", "is", "are", "to", "with", "that", "for", "not", "this",
            "from", "was", "were", "has", "have", "in", "on", "by", "as"}

VICINE = [
    "quale versione di Redis usa la cache dei giudizi del gate",
    "come si configura il backend PostgreSQL per lo store semantico",
    "quanti nodi ha il cluster Kubernetes di produzione del prodotto",
    "come si abilita l autenticazione a due fattori nella console della memoria",
    "quale licenza copre il modulo di quarantena, MIT o Apache",
    "come si esporta lo store dei fatti in formato Parquet per Spark",
    "quale algoritmo di compressione usa il journal su disco",
    "come si configura il rate limit per chiamata del gateway di recall",
    "qual e la latenza garantita dallo SLA per il recall semantico",
    "come si integra la memoria con Elasticsearch per la ricerca ibrida",
    "quale porta TCP ascolta il demone di embedding in produzione",
    "come si ruota la chiave di cifratura del database dei fatti",
    "quanti utenti concorrenti regge il server MCP prima di degradare",
    "come si configura il backup incrementale su S3 dello store dei fatti",
    "quale versione minima di CUDA serve per il cross encoder del gate",
    "come si disattiva la telemetria anonima del prodotto verso il fornitore",
    "quale broker di code usa la pipeline di consolidamento notturna",
]

LONTANE = [
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
    return sorted(sorted(set(tok), key=tok.index), key=len, reverse=True)[:6]


def query_vere():
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
            it.append(" ".join(token6(p)))
        elif lg == "en" and len(en) < N_PER_LINGUA:
            en.append(" ".join(token6(p)))
        if len(it) >= N_PER_LINGUA and len(en) >= N_PER_LINGUA:
            break
    return it + en


def bests(mem, query):
    fuori = []
    for q in query:
        res = mem.search(q, k=K)
        fuori.append(max((float(x.get("score") or 0.0) for x in res), default=0.0))
    return fuori


def riga(nome, b, soglia):
    m = sum(1 for x in b if x < soglia)
    return f"{nome:>10} {m:>3}/{len(b)} ({m / len(b) * 100:5.1f}%)", m


def main():
    mem = Memory(CONFIG.semantic_db)
    # 🔑 DA CHE ALBERO STIAMO LEGGENDO: nel worktree si importa il worktree, da
    # uno script lanciato altrove si importa l albero condiviso. Un banco che non
    # lo dichiara puo misurare un codice diverso da quello che credi (@ws2, 03/09).
    print(f"IMPORT DA {verimem.__file__}", flush=True)
    print(f"verimem {verimem.__version__} | rerank=OFF | k={K} | marcatura = best < soglia",
          flush=True)

    # CONTROLLO CHE FERMA: l'avviso deve uscire davvero, e sulla soglia di oggi.
    r = mem.search(LONTANE[0], k=K)
    sp = getattr(r, "sotto_il_pavimento", None)
    if not sp:
        print("STOP — il campo `sotto_il_pavimento` non esce su una query fuori dominio: "
              "l'avviso non e' acceso come credo e la misura sotto non varrebbe.",
              flush=True)
        return 2
    print(f"  controllo: l'avviso ESCE, pavimento dichiarato = {sp.get('pavimento')}",
          flush=True)

    b_vere, b_vic, b_lon = bests(mem, query_vere()), bests(mem, VICINE), bests(mem, LONTANE)
    for soglia, eti in ((OGGI, "OGGI"), (PROPOSTA, "PROPOSTA")):
        print(f"  soglia {soglia}  ({eti})", flush=True)
        for nome, b in (("VERE", b_vere), ("VICINE", b_vic), ("LONTANE", b_lon)):
            testo, _ = riga(nome, b, soglia)
            print(f"    marcate {testo}", flush=True)
    mv_oggi = sum(1 for x in b_vere if x < OGGI)
    mv_prop = sum(1 for x in b_vere if x < PROPOSTA)
    ml_prop = sum(1 for x in b_lon if x < PROPOSTA)
    print(f"RIGA vere_marcate_oggi={mv_oggi}/{len(b_vere)} "
          f"vere_marcate_proposta={mv_prop}/{len(b_vere)} "
          f"lontane_marcate_proposta={ml_prop}/{len(b_lon)} "
          f"vicine_marcate_proposta={sum(1 for x in b_vic if x < PROPOSTA)}/{len(b_vic)}",
          flush=True)
    print("CRITERIO (@lead-audit, scritto prima): lontane marcate 10/10 E vere marcate "
          "<= 6%.", flush=True)
    print("PREDIZIONE (scritta prima): a 0,8805 le vere marcate sopra il 50%; a 0,839 "
          "sotto il 6%; le vicine restano poco marcate.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
