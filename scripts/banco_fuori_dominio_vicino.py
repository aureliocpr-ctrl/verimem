"""IL FUORI-DOMINIO VICINO — il 100% di zittiti della curva è un artefatto del banco?

    python scripts/banco_fuori_dominio_vicino.py

DA DOVE NASCE. La curva delle 20:49 dà `0,839` con **10/10** query fuori dominio zittite,
e il criterio d'accensione risulta soddisfatto. **Ma le 10 query le ho scelte io LONTANE**
— cucina, botanica, calcio, meteo — e l'avevo scritto PRIMA di eseguire: *«il caso vero è
la domanda VICINA a cui lo store non sa rispondere, e quella popolazione qui non c'è»*.
Questo banco la mette.

LE TRE POPOLAZIONI:
  VICINE   17 domande nel dominio del prodotto (memoria, gate, recall, store, embedding)
           su aspetti che nello store NON ci sono (infrastruttura, licenze, prezzi, SLA).
           Condividono il VOCABOLARIO con i fatti, ma non hanno risposta.
  VERE      3 query derivate da fatti realmente presenti — il CONTROLLO POSITIVO.
  LONTANE   le 10 di prima, come riferimento.

PREDIZIONE SCRITTA PRIMA (02/09 21:05, ws1):
  la MAGGIORANZA delle VICINE avrà `best` SOPRA `0,839` — condividono il lessico dello
  store, e il coseno misura la vicinanza lessicale prima di quella della risposta.
  ⇒ la soglia NON le zittirà, e il `100%` della curva sarà un artefatto della distanza
  che avevo scelto io.
CONDIZIONE D'USCITA (scritta prima):
  >= 80% delle vicine sotto `0,839`  -> l'accensione regge anche sul caso difficile
  <  50% delle vicine sotto `0,839`  -> il criterio NON è soddisfatto sul caso vero,
                                        e va detto a @lead-audit prima di accendere
  in mezzo                           -> INCONCLUSO

🔑 CONTROLLO CHE DEVE POTER FERMARE: le 3 VERE devono stare SOPRA `0,839`. Se cadessero
sotto insieme alle vicine, il banco non separerebbe niente e nessun numero varrebbe.

⚠️ «Senza risposta» è una MIA assunzione sulle 17: per poterla falsificare il banco stampa
il primo risultato di ognuna, così si vede se per caso una risposta c'era.

⚠️ RERANK SPENTO (`ENGRAM_RECALL_RERANK=0`), un solo processo, sola lettura.
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
SOGLIA = 0.839

#: NEL DOMINIO (memoria, gate, recall, store, embedding) ma su cose che lo store non ha:
#: infrastruttura, licenze, prezzi, SLA, integrazioni. Il lessico è quello dei fatti.
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


def token6(testo):
    tok = re.findall(r"[\w\-.]{3,}", testo)
    return sorted(sorted(set(tok), key=tok.index), key=len, reverse=True)[:6]


def tre_vere():
    """Tre query derivate da fatti realmente presenti: il controllo positivo."""
    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT proposition FROM facts WHERE proposition IS NOT NULL "
        "AND length(proposition) BETWEEN 60 AND 300 LIMIT 3"
    ).fetchall()
    con.close()
    return [(" ".join(token6(str(p))), str(p)) for (p,) in righe]


def best(mem, q):
    res = mem.search(q, k=K)
    if not res:
        return 0.0, ""
    b = max(float(x.get("score") or 0.0) for x in res)
    primo = max(res, key=lambda x: float(x.get("score") or 0.0))
    return b, (primo.get("text") or "")[:90].replace("\n", " ")


def gruppo(mem, query, nome, mostra_testo=False):
    sotto = 0
    print(f"  {nome}", flush=True)
    for q in query:
        b, testo = best(mem, q)
        giu = b < SOGLIA
        sotto += giu
        marca = "sotto" if giu else "SOPRA"
        print(f"    {b:.4f} {marca}  {q[:58]}", flush=True)
        if mostra_testo and not giu:
            print(f"             ^ primo risultato: {testo}", flush=True)
    n = len(query)
    print(f"    => sotto {SOGLIA}: {sotto}/{n} ({sotto / n * 100:.1f}%)", flush=True)
    return sotto, n


def main():
    mem = Memory(CONFIG.semantic_db)
    # 🔑 DA CHE ALBERO STIAMO LEGGENDO: nel worktree si importa il worktree, da
    # uno script lanciato altrove si importa l albero condiviso. Un banco che non
    # lo dichiara puo misurare un codice diverso da quello che credi (@ws2, 03/09).
    print(f"IMPORT DA {verimem.__file__}", flush=True)
    print(f"verimem {verimem.__version__} | rerank=OFF | k={K} | soglia={SOGLIA}", flush=True)

    vere = tre_vere()
    print("  CONTROLLO POSITIVO — 3 query da fatti REALMENTE presenti", flush=True)
    sopra_vere = 0
    for q, _f in vere:
        b, _ = best(mem, q)
        sopra_vere += (b >= SOGLIA)
        print(f"    {b:.4f} {'SOPRA' if b >= SOGLIA else 'sotto'}  {q[:58]}", flush=True)
    if sopra_vere == 0:
        print("STOP — nessuna delle 3 query VERE supera la soglia: il banco non separa "
              "niente e nessun numero sotto varrebbe.", flush=True)
        return 2
    print(f"    => sopra soglia: {sopra_vere}/3 — il banco separa, si procede.", flush=True)

    sv, nv = gruppo(mem, VICINE, "VICINE (nel dominio, senza risposta)", mostra_testo=True)
    sl, nl = gruppo(mem, LONTANE, "LONTANE (il riferimento della curva)")

    perc = sv / nv * 100
    print(f"RIGA vicine_sotto={sv}/{nv} ({perc:.1f}%) lontane_sotto={sl}/{nl} "
          f"vere_sopra={sopra_vere}/3 soglia={SOGLIA}", flush=True)
    print("PREDIZIONE (scritta prima): la MAGGIORANZA delle vicine sta SOPRA la soglia.",
          flush=True)
    print("CONDIZIONE: >=80% sotto -> l'accensione regge; <50% sotto -> il criterio NON "
          "e' soddisfatto sul caso vero.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
