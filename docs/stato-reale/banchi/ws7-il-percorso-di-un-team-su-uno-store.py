"""U-B — «un team su uno store»: il percorso che nessuno aveva mai eseguito.

    python docs/stato-reale/banchi/ws7-il-percorso-di-un-team-su-uno-store.py

⚡ **STORE TEMPORANEO**, mai quello di Aurelio.

🔴 **LA SCELTA DI REGIME CHE HO SBAGLIATO, e la lascio scritta invece di
correggerla in silenzio.** Avevo scritto: *«niente giudice: si scrive senza
`source`, perche' U-B misura provenienza, revisione, audit e scadenza, NON il
gate. Chi pensa che questo lo invalidi lo dica: e' una scelta, non una
dimenticanza.»*
**Lo dico io: quella scelta invalida i passi 3 e 4.** La **revisione E' il gate**
— classificare una scrittura successiva come conflitto o supersessione passa da
`supersession_policy.classify_write_relation`, cioe' dal giudizio. Senza `source`
il moat non gira, la relazione fra i due fatti **non viene classificata**, e la
ricevuta lo dice a chiare lettere: `evidence_class: lexical_only`, `judge: null`.
⇒ **Il passo 4 («solo il corrente») non poteva passare per costruzione**, e il
passo 3 ha risposto a una domanda piu' debole di quella che credevo di fargli.
⇒ **Passi 1, 2, 6 restano validi in questo regime; 3 e 4 vanno rifatti CON la
fonte.** Avevo invitato gli altri a contestare il mio regime e sono cascata
esattamente li': **avevo dichiarato una scelta e non ne avevo tracciato le
conseguenze.**

━━ IL CRITERIO E' SCRITTO PRIMA DI ESEGUIRE, e questa e' la ragione ━━━━━━━━━━
`docs/stato-reale/PERCORSI-UTENTE.md` dichiara per U-B un criterio solo:

    «un quarto che non era presente ricostruisce dallo store chi ha scritto
     cosa, quando, e perche' il valore corrente e' quello — senza chiedere
     niente a nessuno.»

Ogni passo qui sotto porta il SUO criterio, deciso prima di guardare l'esito.
Senza, «funziona» vuol dire quello che vuole chi esegue — ed e' la forma in cui
sono cascata due volte il 04 e il 05/09.

━━ LA PREVISIONE DEL PASSO 3, DEPOSITATA PRIMA DI ESEGUIRE ━━━━━━━━━━━━━━━━━━━
`verimem/client.py` documenta, nel commento di `asserted_at`:

    «Senza, le due si ordinano per momento di SCRITTURA e la piu' recente vince
     sempre — una correzione supersede IN SILENZIO invece di andare al giudice
     come conflitto ... Misurato il 30/08: valorizzato su 0 fatti su 15.978, ed
     e' esposto da tutte e tre le porte — la conseguenza qui sopra non era
     dichiarata in nessuna.»

⇒ **PREDICO** che al passo 3, senza `asserted_at`, la correzione di Bruno sul
fatto di Anna **supersede senza essere dichiarata un conflitto**. Se la
previsione cade, tanto meglio: il prodotto e' migliore di quanto dice di se'.
Il banco prova ENTRAMBI i bracci — con e senza `asserted_at` — perche' un
braccio solo non distingue «il prodotto non lo rileva» da «non ho dato al
prodotto cio' che gli serve per rilevarlo».
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

STORE = Path(tempfile.mkdtemp(prefix="iris-ub-"))
os.environ["HIPPO_DATA_DIR"] = str(STORE)
os.environ["ENGRAM_DATA_DIR"] = str(STORE)
# ⚠️ NON spengo piu' l'encode service. Alla prima esecuzione l'avevo spento
# («un team nuovo non ha il daemon») e il prodotto ha dichiarato: «il fatto
# viene scritto SENZA embedding, recall keyword finche' il daemon non torna».
# Con la ricerca ridotta a keyword, il passo 4 misurava il MIO regime, non la
# supersessione. Il regime «senza daemon» e' una domanda VERA ma e' un altro
# banco, e va confrontato con questo — non sostituito a questo.

from verimem import Memory  # noqa: E402  (dopo le variabili: lo store si lega all'import)

#: ⚠️ TROVATO ESEGUENDO, e si somma a T12: il nome del parametro del limite
#: cambia fra le porte gemelle — SDK `search(k=)`, MCP `hippo_facts_recall(k=)`,
#: MCP `hippo_facts_search(limit=)`. Non solo il VALORE massimo differisce (50
#: contro 100, reperto di Giano): differisce il NOME. Chi porta un client da una
#: porta all'altra lo scopre con un TypeError.
#: `--con-fonte` accende il giudice: senza, la RELAZIONE fra due scritture non
#: viene classificata e i passi 3-4 sono indecidibili (vedi il regime in cima).
#: I due bracci si confrontano, non si sostituiscono: uno dice cosa fa il
#: prodotto quando il team non ha il giudice, l'altro quando ce l'ha.
CON_FONTE = "--con-fonte" in sys.argv


def FONTE(testo: str) -> dict:
    return {"source": testo} if CON_FONTE else {}


ESITI: list[tuple[str, str, str]] = []


def passo(n: str, criterio: str, ok: bool, detta: str) -> None:
    ESITI.append((n, "PASSA" if ok else "NON PASSA", detta))
    print(f"  [{n}] {'PASSA    ' if ok else 'NON PASSA'} · {criterio}")
    print(f"        {detta}")


def main() -> None:
    print(f"  store TEMPORANEO: {STORE}")
    m = Memory(str(STORE / "team.db"))

    # ── PASSO 1 · due scrittori diversi sullo stesso store ──────────────────
    # criterio: entrambe le scritture entrano e portano principal diversi.
    FONTE_A = ("Verbale riunione infrastruttura del 3 settembre: il servizio "
               "checkout usa Stripe come fornitore di pagamenti dal 2024, e la "
               "regione di esecuzione e' eu-west-1.")
    FONTE_C = ("Comunicazione al team del 5 settembre: la migrazione del "
               "checkout ad Adyen e' completata, Stripe non e' piu' il "
               "fornitore di pagamenti del servizio checkout.")
    a = m.add("Il fornitore di pagamenti del servizio checkout e' Stripe.",
              topic="team/infra", principal="anna", **FONTE(FONTE_A))
    b = m.add("Il servizio checkout gira nella regione eu-west-1.",
              topic="team/infra", principal="bruno", **FONTE(FONTE_A))
    due = bool(a.get("stored")) and bool(b.get("stored"))
    passo("1 due scrittori", "entrambe le scritture entrano",
          due, f"anna id={str(a.get('id'))[:12]} · bruno id={str(b.get('id'))[:12]}")

    # ── PASSO 2 · il secondo legge il fatto del primo e VEDE DA CHI VIENE ───
    # criterio: nel risultato della lettura compare l'identita' di chi ha scritto.
    letti = m.search("fornitore di pagamenti", k=5)
    righe = letti if isinstance(letti, list) else (letti or {}).get("items", [])
    campi = sorted({k for r in righe for k in (r if isinstance(r, dict) else {})})
    prov = [k for k in campi if any(s in k.lower() for s in
                                    ("principal", "writer", "author", "agent", "by"))]
    # ⚠️ IL CRITERIO GUARDA I VALORI, NON I NOMI DEI CAMPI. Alla prima esecuzione
    # chiedevo solo che i campi ESISTESSERO, e il passo ha detto PASSA con la
    # provenienza VUOTA. E' lo stesso difetto che @ws1 Marie ha trovato nella
    # cella di @ws2 Giano («asseriva che e' tornato UN risultato, non QUELLO
    # giusto»): un controllo che non puo' distinguere il caso buono dal cattivo.
    # Ora: il campo dev'essere presente E valorizzato E uguale a chi ha scritto.
    atteso = "anna"
    trovati = [r.get("writer_principal") for r in righe if isinstance(r, dict)]
    ha_prov = any(v == atteso for v in trovati)
    passo("2 provenienza", "la lettura dice DA CHI viene il fatto, col nome giusto",
          ha_prov,
          f"campi disponibili: {prov or 'NESSUNO'} · writer_principal letti: "
          f"{trovati or '—'} · atteso {atteso!r}")

    # ── PASSO 3 · uno CORREGGE il fatto dell'altro ──────────────────────────
    # criterio: la correzione e' dichiarata (conflitto o supersessione esplicita),
    #           non un silenzioso «l'ultimo vince».
    # ⚠️ DUE BRACCI: senza e con `asserted_at` (vedi la previsione in cima).
    for braccio, kw in (("senza asserted_at", {}),
                        ("con asserted_at", {"asserted_at": time.time() + 60})):
        c = m.add("Il fornitore di pagamenti del servizio checkout e' Adyen.",
                  topic="team/infra", principal="bruno", **FONTE(FONTE_C), **kw)
        chiavi = sorted(c) if isinstance(c, dict) else []
        parla = [k for k in chiavi if any(s in k.lower() for s in
                 ("conflict", "supersed", "adjudic", "relation", "conflitt"))]
        detta = {k: c.get(k) for k in parla}
        passo(f"3 correzione ({braccio})",
              "la correzione e' DICHIARATA, non un silenzioso ultimo-vince",
              bool(parla) and any(detta.values()),
              f"campi che parlano di conflitto/supersessione: {parla or 'NESSUNO'} · {detta}")

    # ── PASSO 4 · un terzo riceve SOLO IL CORRENTE, e puo' chiedere la storia ─
    # criterio: la top-k contiene il nuovo e non il vecchio; la storia si ottiene.
    dopo = m.search("fornitore di pagamenti", k=10)
    righe4 = dopo if isinstance(dopo, list) else (dopo or {}).get("items", [])
    # ⚠️ IL CAMPO SI CHIAMA `text`, NON `proposition`. Alla prima esecuzione
    # leggevo `r.get("proposition", r)` e il FALLBACK su `r` faceva trovare i
    # nomi nella rappresentazione dell'oggetto: il conteggio era giusto per
    # caso. `proposition` e' il nome che usa la porta MCP; l'SDK usa `text`
    # (una quarta divergenza di contratto, T12).
    testi = " || ".join(str(r.get("text", "")) for r in righe4)
    superati = [(str(r.get("text", ""))[:40], r.get("superseded_by")) for r in righe4]
    solo_corrente = ("Adyen" in testi) and ("Stripe" not in testi)
    passo("4 solo il corrente", "la top-k rende il nuovo e NON il vecchio",
          solo_corrente,
          f"Adyen presente: {'Adyen' in testi} · Stripe ancora presente: "
          f"{'Stripe' in testi} · superseded_by di ogni riga: {superati}")

    # ── PASSO 5 · qualcuno chiede COSA E' SUCCESSO (l'audit) ────────────────
    # criterio: esiste un registro leggibile che dice chi ha fatto cosa.
    # ⚠️ NON MISURABILE DA QUESTO BANCO, e lo dico invece di contarlo come rosso.
    # `mcp_audit.log` lo scrive SOLO il server MCP (`mcp_server.py:887`,
    # `CONFIG.data_dir / "mcp_audit.log"`): con l'SDK non esiste PER COSTRUZIONE.
    # Alla prima esecuzione l'avevo contato NON PASSA — cercavo il registro di una
    # porta usandone un'altra. **«Non l'ho misurato» non e' «non funziona».**
    tracce = sorted(p.name for p in STORE.rglob("*")
                    if p.is_file() and any(s in p.name.lower()
                                           for s in ("audit", "journal", "log")))
    ESITI.append(("5 audit", "NON MISURABILE",
                  f"l'audit e' della porta MCP e questo banco usa l'SDK; "
                  f"file trovati: {tracce or 'nessuno'} (atteso: nessuno)"))
    print("  [5 audit] NON MISURABILE · l'audit e' della porta MCP, questo banco usa l'SDK")
    print("        va eseguito da MCP: qui l'assenza NON e' un difetto del prodotto")

    # ── PASSO 6 · un fatto SCADE e chi legge lo sa ──────────────────────────
    # criterio: la lettura DICHIARA che qualcosa e' stato tolto dalla scadenza.
    m.add("La chiave di test del checkout vale fino a stanotte.",
          topic="team/infra", principal="anna", valid_until=time.time() - 1)
    # ⚠️ L'AVVISO E' UN ATTRIBUTO DI `Risultati`, NON UNA CHIAVE DEL JSON.
    # `search()` torna `Risultati`, che E' una lista con attributi sopra
    # (`esclusi_perche_scaduti`, `letto_al_passato`, `sotto_il_pavimento`).
    # Alla prima esecuzione leggevo `json.dumps(risultati, default=str)`, che di
    # una lista serializza SOLO GLI ELEMENTI e butta via gli attributi: il passo
    # dava NON PASSA su un prodotto che invece dichiara benissimo. Il rosso era
    # mio, e il verde e' del prodotto (cura 50f4e05b).
    scaduto = m.search("chiave di test", k=5)
    nota = getattr(scaduto, "esclusi_perche_scaduti", None)
    passo("6 scadenza dichiarata", "la lettura DICHIARA cio' che la scadenza ha tolto",
          bool(nota), f"esclusi_perche_scaduti = {str(nota)[:160]}")

    # ── IL CRITERIO DI ARRIVO, che e' uno solo ──────────────────────────────
    print()
    passati = sum(1 for _, e, _ in ESITI if e == "PASSA")
    print(f"  ⇒ {passati} passi su {len(ESITI)} passano.")
    print("  ⇒ CRITERIO DI ARRIVO: un quarto che non era presente ricostruisce")
    print("     chi ha scritto cosa, quando, e perche' il corrente e' quello.")
    print("     Serve il passo 2 (chi) + il 4 (cosa vale ora) + il 5 (cosa e'")
    print("     successo). Se uno dei tre non passa, il criterio NON e' raggiunto")
    print("     anche se il conteggio sembra alto.")
    tre = {n.split()[0]: e for n, e, _ in ESITI}
    arrivato = all(tre.get(k) == "PASSA" for k in ("2", "4", "5"))
    if tre.get("5") == "NON MISURABILE":
        print("  ⚠️ il passo 5 NON e' misurato da qui: il criterio di arrivo")
        print("     resta INDECIDIBILE finche' non lo si esegue da MCP.")
    print(f"  ⇒ **U-B {'ARRIVA' if arrivato else 'NON ARRIVA'} IN FONDO.**")

    fuori = Path(__file__).with_name(
        Path(__file__).stem + ("-con-fonte" if CON_FONTE else "") + ".json")
    fuori.write_text(json.dumps(
        {"store": str(STORE), "regime": ("SDK, con fonte (il moat GIRA)" if CON_FONTE
                                 else "SDK, senza fonte (il moat NON gira)"),
         "esiti": [{"passo": n, "esito": e, "dettaglio": d} for n, e, d in ESITI],
         "criterio_di_arrivo_raggiunto": arrivato},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  scritto {fuori}")
    shutil.rmtree(STORE, ignore_errors=True)
    print(f"  store temporaneo rimosso: {STORE}")


if __name__ == "__main__":
    main()
