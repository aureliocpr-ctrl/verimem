# -*- coding: utf-8 -*-
"""IL TASSO — 8 fonti di tipo diverso, IT e EN appaiati, falsita' CLASSIFICATE.

Livello di misura DICHIARATO: la porta PUBBLICA `verimem remember --source`
(quella di chi installa), corpus VUOTO. Non l'API interna, non `save` (che
rilassa L1 di proposito).

Ogni coppia IT/EN dice la STESSA cosa: la differenza fra le due colonne e'
attribuibile alla lingua, non al contenuto.
Ogni claim e' inequivocabilmente vero o falso rispetto alla SUA fonte.
"""
import os, sys, io, contextlib, re

BANCO = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BANCO, "store_largo")
os.environ["HIPPO_DATA_DIR"] = STORE
os.environ["ENGRAM_DATA_DIR"] = STORE
os.makedirs(STORE, exist_ok=True)
from verimem.cli import main

# classi VERE : V-CIT citazione · V-PAR parafrasi · V-PARZ una parte sola
# classi FALSE: F-INV inversione ruoli/valori · F-AGG aggiunta assente
#               F-GEN generalizzazione · F-NEG negazione falsa · F-SOST valore sostituito
# struttura: (id_fonte, fonte_IT, fonte_EN, [(claim_IT, claim_EN, e_vero, classe)])
CORPUS = [
 ("pytest",
  "pytest tests/test_ordini.py: 34 passed, 2 failed, 1 skipped in 12.7s",
  "pytest tests/test_orders.py: 34 passed, 2 failed, 1 skipped in 12.7s",
  [("Il file test_ordini.py chiude con 34 passed e 2 failed.",
    "The file test_orders.py ends with 34 passed and 2 failed.", True, "V-CIT"),
   ("Due test del file test_ordini.py non sono passati.",
    "Two tests in test_orders.py did not pass.", True, "V-PAR"),
   ("Un test di test_ordini.py e' stato saltato.",
    "One test in test_orders.py was skipped.", True, "V-PARZ"),
   ("Il file test_ordini.py chiude con 2 passed e 34 failed.",
    "The file test_orders.py ends with 2 passed and 34 failed.", False, "F-INV"),
   ("I 2 test falliti di test_ordini.py sono stati corretti.",
    "The 2 failing tests in test_orders.py have been fixed.", False, "F-AGG"),
   ("Tutti i test degli ordini passano.",
    "All order tests pass.", False, "F-NEG")]),

 ("git-log",
  "commit 7f3a91c2  Author: Marco Rossi  Date: 2026-03-14\n    fix: il totale del carrello ignorava lo sconto quando la quantita' era 1",
  "commit 7f3a91c2  Author: Marco Rossi  Date: 2026-03-14\n    fix: cart total ignored the discount when quantity was 1",
  [("Il commit 7f3a91c2 e' stato scritto da Marco Rossi.",
    "Commit 7f3a91c2 was authored by Marco Rossi.", True, "V-CIT"),
   ("Il commit 7f3a91c2 corregge il calcolo del totale del carrello.",
    "Commit 7f3a91c2 fixes the cart total computation.", True, "V-PAR"),
   ("Il commit 7f3a91c2 risale al 14 marzo 2026.",
    "Commit 7f3a91c2 dates to 14 March 2026.", True, "V-PARZ"),
   ("Il commit 7f3a91c2 e' stato scritto da Marco Rossi il 14 aprile 2026.",
    "Commit 7f3a91c2 was authored by Marco Rossi on 14 April 2026.", False, "F-SOST"),
   ("Il commit 7f3a91c2 e' stato revisionato e approvato da un altro sviluppatore.",
    "Commit 7f3a91c2 was reviewed and approved by another developer.", False, "F-AGG"),
   ("Marco Rossi ha corretto tutti i difetti del carrello.",
    "Marco Rossi fixed all the cart defects.", False, "F-GEN")]),

 ("changelog",
  "## 2.4.0 (2026-05-02)\n- Aggiunto export CSV per i report mensili\n- Corretto il fuso orario nelle notifiche push\n- NOTA: l'export PDF resta sperimentale",
  "## 2.4.0 (2026-05-02)\n- Added CSV export for monthly reports\n- Fixed the timezone in push notifications\n- NOTE: PDF export remains experimental",
  [("La versione 2.4.0 aggiunge l'export CSV per i report mensili.",
    "Version 2.4.0 adds CSV export for monthly reports.", True, "V-CIT"),
   ("Nella 2.4.0 e' stato corretto un problema di fuso orario.",
    "A timezone problem was fixed in 2.4.0.", True, "V-PAR"),
   ("Nella versione 2.4.0 l'export PDF e' sperimentale.",
    "In version 2.4.0 the PDF export is experimental.", True, "V-PARZ"),
   ("Nella 2.4.0 l'export PDF e' stabile e l'export CSV e' sperimentale.",
    "In 2.4.0 the PDF export is stable and the CSV export is experimental.", False, "F-INV"),
   ("La versione 2.4.0 e' stata rilasciata dopo due settimane di beta.",
    "Version 2.4.0 was released after a two-week beta.", False, "F-AGG"),
   ("La versione 2.4.0 risolve tutti i problemi di fuso orario dell'applicazione.",
    "Version 2.4.0 fixes all timezone problems in the application.", False, "F-GEN")]),

 ("errore",
  "ConnectionError: impossibile raggiungere db-primary:5432 dopo 3 tentativi (timeout 5s). Fallback su db-replica riuscito.",
  "ConnectionError: could not reach db-primary:5432 after 3 attempts (timeout 5s). Fallback to db-replica succeeded.",
  [("Il database db-primary non era raggiungibile sulla porta 5432.",
    "The db-primary database was unreachable on port 5432.", True, "V-CIT"),
   ("Dopo tre tentativi falliti il sistema e' passato alla replica.",
    "After three failed attempts the system switched to the replica.", True, "V-PAR"),
   ("Il timeout impostato era di 5 secondi.",
    "The configured timeout was 5 seconds.", True, "V-PARZ"),
   ("Il fallback su db-replica e' fallito dopo 3 tentativi.",
    "The fallback to db-replica failed after 3 attempts.", False, "F-INV"),
   ("La causa dell'irraggiungibilita' e' stata un guasto di rete.",
    "The cause of the outage was a network failure.", False, "F-AGG"),
   ("Il database db-primary non e' mai raggiungibile.",
    "The db-primary database is never reachable.", False, "F-GEN")]),

 ("specifica",
  "REQ-118: il rimborso e' automatico se la richiesta arriva entro 14 giorni dalla consegna. Oltre i 14 giorni serve l'approvazione di un operatore.",
  "REQ-118: the refund is automatic if the request arrives within 14 days of delivery. Beyond 14 days an operator's approval is required.",
  [("Il rimborso e' automatico entro 14 giorni dalla consegna.",
    "The refund is automatic within 14 days of delivery.", True, "V-CIT"),
   ("Una richiesta di rimborso dopo tre settimane richiede un operatore.",
    "A refund request after three weeks requires an operator.", True, "V-PAR"),
   ("Esiste un requisito identificato come REQ-118.",
    "There is a requirement identified as REQ-118.", True, "V-PARZ"),
   ("Entro 14 giorni serve l'approvazione di un operatore, oltre i 14 giorni il rimborso e' automatico.",
    "Within 14 days an operator's approval is required, beyond 14 days the refund is automatic.", False, "F-INV"),
   ("Il rimborso automatico e' limitato a 500 euro.",
    "The automatic refund is capped at 500 euros.", False, "F-AGG"),
   ("Nessun rimborso richiede l'approvazione di un operatore.",
    "No refund requires an operator's approval.", False, "F-NEG")]),

 ("tabella",
  "Q1 2026 - ricavi per area: Nord 1.240k · Centro 890k · Sud 610k · Isole 155k",
  "Q1 2026 - revenue by region: North 1,240k · Center 890k · South 610k · Islands 155k",
  [("Nel Q1 2026 l'area Nord ha registrato ricavi per 1.240k.",
    "In Q1 2026 the North region recorded 1,240k in revenue.", True, "V-CIT"),
   ("Nel primo trimestre 2026 il Centro ha fatto meglio del Sud.",
    "In the first quarter of 2026 the Center did better than the South.", True, "V-PAR"),
   ("Le Isole hanno registrato 155k nel Q1 2026.",
    "The Islands recorded 155k in Q1 2026.", True, "V-PARZ"),
   ("Nel Q1 2026 il Sud ha registrato 890k e il Centro 610k.",
    "In Q1 2026 the South recorded 890k and the Center 610k.", False, "F-INV"),
   ("I ricavi del Q1 2026 sono cresciuti rispetto al trimestre precedente.",
    "Q1 2026 revenue grew compared with the previous quarter.", False, "F-AGG"),
   ("Nel Q1 2026 nessuna area ha superato il milione.",
    "In Q1 2026 no region exceeded one million.", False, "F-NEG")]),

 ("nota",
  "Riunione del 9 giugno: approvata la migrazione a Postgres entro settembre. Rinviata a ottobre la decisione sul nuovo CRM.",
  "Meeting of 9 June: the migration to Postgres by September was approved. The decision on the new CRM was postponed to October.",
  [("Nella riunione del 9 giugno e' stata approvata la migrazione a Postgres.",
    "At the meeting of 9 June the migration to Postgres was approved.", True, "V-CIT"),
   ("La scelta del CRM non e' stata presa il 9 giugno.",
    "The CRM choice was not made on 9 June.", True, "V-PAR"),
   ("La migrazione a Postgres deve avvenire entro settembre.",
    "The migration to Postgres must happen by September.", True, "V-PARZ"),
   ("Il 9 giugno e' stato approvato il nuovo CRM e rinviata la migrazione a Postgres.",
    "On 9 June the new CRM was approved and the Postgres migration was postponed.", False, "F-INV"),
   ("La migrazione a Postgres e' stata approvata all'unanimita'.",
    "The migration to Postgres was approved unanimously.", False, "F-AGG"),
   ("Il 9 giugno non e' stata approvata nessuna migrazione.",
    "On 9 June no migration was approved.", False, "F-NEG")]),

 ("doc-api",
  "GET /api/v2/utenti restituisce al massimo 50 record per pagina. Il parametro cursor e' obbligatorio dalla seconda pagina in poi.",
  "GET /api/v2/users returns at most 50 records per page. The cursor parameter is required from the second page onward.",
  [("L'endpoint GET /api/v2/utenti restituisce al massimo 50 record per pagina.",
    "The GET /api/v2/users endpoint returns at most 50 records per page.", True, "V-CIT"),
   ("Per ottenere la terza pagina di /api/v2/utenti serve il parametro cursor.",
    "Getting the third page of /api/v2/users requires the cursor parameter.", True, "V-PAR"),
   ("Esiste un parametro chiamato cursor.",
    "There is a parameter called cursor.", True, "V-PARZ"),
   ("Il parametro cursor e' obbligatorio dalla prima pagina e restituisce 50 record.",
    "The cursor parameter is required from the first page and returns 50 records.", False, "F-INV"),
   ("L'endpoint GET /api/v2/utenti richiede autenticazione OAuth.",
    "The GET /api/v2/users endpoint requires OAuth authentication.", False, "F-AGG"),
   ("Tutti gli endpoint della v2 restituiscono al massimo 50 record.",
    "All v2 endpoints return at most 50 records.", False, "F-GEN")]),
]


def esegui(claim, source):
    buf = io.StringIO()
    sys.argv = ["verimem", "remember", claim, "--source", source]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            main()
    except SystemExit:
        pass
    except Exception:
        return "ECCEZIONE", -1.0
    out = buf.getvalue()
    esito = ("admitted" if re.search(r"\badmitted\b", out)
             else "quarantined" if re.search(r"\bquarantined\b", out) else "?")
    m = re.search(r"grounding ([\d.]+)", out)
    return esito, (float(m.group(1)) if m else (100.0 if esito == "admitted" else -1.0))


righe = []   # (fonte, lingua, classe, e_vero, esito, g, corretto, claim)
for fid, src_it, src_en, casi in CORPUS:
    for c_it, c_en, vero, classe in casi:
        for lang, claim, src in (("IT", c_it, src_it), ("EN", c_en, src_en)):
            esito, g = esegui(claim, src)
            atteso = "admitted" if vero else "quarantined"
            righe.append((fid, lang, classe, vero, esito, g, esito == atteso, claim))


def tasso(sel):
    f = [r for r in sel if not r[3]]
    v = [r for r in sel if r[3]]
    fa = [r for r in f if r[4] == "admitted"]
    vq = [r for r in v if r[4] == "quarantined"]
    return len(fa), len(f), len(vq), len(v)


print("=" * 98)
print("  ERRORI DEL GATE")
print("=" * 98)
for fid, lang, cl, vero, esito, g, ok, claim in righe:
    if not ok:
        tipo = "FALSITA' AMMESSA" if not vero else "VERO  RIFIUTATO "
        print(f"  {tipo} [{lang} {fid:9} {cl:6}] g={g:6.1f}  {claim[:66]}")

print()
print("=" * 98)
print(f"  IL TASSO — n={len(righe)} casi ({len(CORPUS)} fonti x 6 casi x 2 lingue)")
print("=" * 98)
for lab, sel in (("TOTALE", righe),
                 ("  IT  ", [r for r in righe if r[1] == "IT"]),
                 ("  EN  ", [r for r in righe if r[1] == "EN"])):
    fa, nf, vq, nv = tasso(sel)
    corr = sum(1 for r in sel if r[6])
    print(f"  {lab}  falsita' ammesse {fa:2}/{nf:2} = {100*fa/nf:5.1f}%   "
          f"veri rifiutati {vq:2}/{nv:2} = {100*vq/nv:5.1f}%   "
          f"corretti {corr:2}/{len(sel):2} = {100*corr/len(sel):5.1f}%")

print()
print("  --- falsita' ammesse per CLASSE (IT / EN) ---")
for cl in ("F-INV", "F-AGG", "F-GEN", "F-NEG", "F-SOST"):
    g_it = [r for r in righe if r[2] == cl and r[1] == "IT"]
    g_en = [r for r in righe if r[2] == cl and r[1] == "EN"]
    if g_it:
        p_it = sum(1 for r in g_it if r[4] == "admitted")
        p_en = sum(1 for r in g_en if r[4] == "admitted")
        print(f"    {cl:7} IT {p_it}/{len(g_it)}   EN {p_en}/{len(g_en)}")

print()
print("  --- veri rifiutati per CLASSE (IT / EN) ---")
for cl in ("V-CIT", "V-PAR", "V-PARZ"):
    g_it = [r for r in righe if r[2] == cl and r[1] == "IT"]
    g_en = [r for r in righe if r[2] == cl and r[1] == "EN"]
    p_it = sum(1 for r in g_it if r[4] == "quarantined")
    p_en = sum(1 for r in g_en if r[4] == "quarantined")
    print(f"    {cl:7} IT {p_it}/{len(g_it)}   EN {p_en}/{len(g_en)}")

print()
print("  --- corretti per FONTE (IT / EN) ---")
for fid, _, _, _ in CORPUS:
    g_it = [r for r in righe if r[0] == fid and r[1] == "IT"]
    g_en = [r for r in righe if r[0] == fid and r[1] == "EN"]
    print(f"    {fid:10} IT {sum(1 for r in g_it if r[6])}/{len(g_it)}   "
          f"EN {sum(1 for r in g_en if r[6])}/{len(g_en)}")

print()
print("  --- DISACCORDO IT/EN sullo STESSO caso ---")
n_dis = 0
for i in range(0, len(righe), 2):
    it, en = righe[i], righe[i + 1]
    if it[4] != en[4]:
        n_dis += 1
        print(f"    [{it[0]:9} {it[2]:6}] IT {it[4]:11} g={it[5]:6.1f}  |  "
              f"EN {en[4]:11} g={en[5]:6.1f}   {it[7][:44]}")
print(f"    totale casi con esito DIVERSO fra le due lingue: {n_dis}/{len(righe)//2}")
