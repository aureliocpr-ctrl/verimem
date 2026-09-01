r"""`HIPPO_DATA_DIR` isola lo store. NON isola il daemon di encoding.

Trovato durante il percorso utente (`1b065c65`): un venv **vergine**, con
`HIPPO_DATA_DIR` puntato a una directory temporanea appena creata, ha scritto e riletto
in **4.5s** e **1.6s** — e `verimem doctor` ha stampato «*shared encode daemon warm on
:50296*». ⇒ Quel daemon non e' suo: e' quello che serve lo store principale.

LA CAUSA, una riga (`verimem/encode_service.py:41`)::

    DISCOVERY_PATH = Path.home() / ".engram" / "encode_service.json"

⇒ Il percorso e' **hardcoded su `~/.engram`** e **non deriva** da `HIPPO_DATA_DIR` ne'
da `ENGRAM_DATA_DIR`. Chiunque imposti la variabile per «isolare un banco» isola **lo
store** e continua a parlare con **il daemon di tutti**.

⚠️ **PERCHE' CI RIGUARDA PIU' DI QUANTO SEMBRI**, e sono tre cose diverse:
  ① **I nostri banchi.** Ogni banco che usa `HIPPO_DATA_DIR` per isolarsi usa comunque
     il **modello caricato dal daemon condiviso**. Se il daemon avesse un modello
     diverso da quello atteso, il banco misurerebbe **quel** modello senza dirlo.
  ② **I nostri TEMPI.** Un banco eseguito col daemon caldo e uno col daemon spento
     differiscono di un caricamento del modello — il commento in
     `encode_service.py` lo quantifica: «*the next store()/recall() cold-loaded the
     model in-process (~22s measured)*». ⇒ **Due esecuzioni dello stesso banco possono
     differire di venti secondi per una ragione che nessuna delle due dichiara.**
  ③ **Gli utenti.** Due installazioni distinte sulla stessa utenza Windows — un venv di
     prova e quello di lavoro — **condividono il daemon**. E' efficiente, ma non e'
     quello che «ambiente isolato» fa credere.

LA MISURA, e sono due domande separate::

    ①  con `HIPPO_DATA_DIR` diverso, `read_discovery()` legge lo STESSO file?
    ②  lo store e' davvero separato? (se non lo fosse, il difetto sarebbe un altro
       e molto peggiore)

⇒ La ② e' la **popolazione di controllo**: senza, «non isola» non distinguerebbe «non
isola il daemon» da «non isola niente».

🔴 ESITO — **provato, e il controllo regge: isola lo store, non il daemon**::

    regime                 file di discovery                 porta   semantic_db
    store TEMPORANEO A     ~\.engram\encode_service.json      50296   Temp\ws5_store_a_…
    store TEMPORANEO B     ~\.engram\encode_service.json      50296   Temp\ws5_store_b_…
    nessuna variabile      ~\.engram\encode_service.json      50296   ~\.engram\semantic…

✅ **IL CONTROLLO REGGE**: il `semantic_db` **cambia in ogni regime** ⇒ lo store e'
davvero separato, e il difetto e' **solo** sul daemon. Senza questa riga «non isola» non
distinguerebbe «non isola il daemon» da «non isola niente».

🔴 **Il file di discovery e la porta sono gli STESSI in tutti e tre** ⇒ tre processi che
si credono isolati parlano allo **stesso daemon**, con **il modello che ha caricato
lui** (`intfloat/multilingual-e5-base`).

⇒ **PER I NOSTRI BANCHI**: `HIPPO_DATA_DIR` non basta a dire «isolato». Un banco che
misura tempi o vettori sta usando il daemon di tutti — e due esecuzioni dello stesso
banco, una col daemon caldo e una senza, differiscono di **un caricamento del modello**
(«*~22s measured*», commento in `encode_service.py`). **Chi pubblica un tempo dovrebbe
dire se il daemon era su**, ed e' un dato che `verimem doctor` stampa in chiaro.

📌 **E potrebbe spiegare un mio reperto di ieri** (`W5-20`: `hippo_facts_recall` a
**61.585 ms** alla prima chiamata contro 392 dopo): se il daemon idle-muore, la prima
chiamata del processo successivo **carica il modello in-process**. **E' un'ipotesi
coerente e NON l'ho misurata** — la misura richiederebbe di fermare il daemon di
Aurelio, cosa che non faccio.

SOLA LETTURA: legge il file di discovery e i percorsi che il prodotto calcola; non
avvia, non ferma e non tocca nessun daemon.
⚖️ PUNTI DEBOLI: verifico che il **percorso** sia condiviso, non che due processi
ricevano lo stesso vettore; e non misuro il caso «daemon spento», che richiederebbe di
fermare quello di Aurelio — cosa che non faccio.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-hippo-data-dir-non-isola-il-daemon.py
"""
import os
import subprocess
import sys
import tempfile


CODICE = (
    "import os, json;"
    "from verimem.encode_service import DISCOVERY_PATH, read_discovery;"
    "from verimem.config import CONFIG;"
    "d = read_discovery() or {};"
    "print(json.dumps({"
    "'data_dir': os.environ.get('HIPPO_DATA_DIR', '(non impostato)'),"
    "'discovery_path': str(DISCOVERY_PATH),"
    "'porta': d.get('port'), 'modello': d.get('model'),"
    "'semantic_db': str(CONFIG.semantic_db)}))"
)


def chiedi(data_dir):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if data_dir:
        env["HIPPO_DATA_DIR"] = data_dir
    else:
        env.pop("HIPPO_DATA_DIR", None)
    env.pop("ENGRAM_DATA_DIR", None)
    env.pop("VERIMEM_DATA_DIR", None)
    r = subprocess.run([sys.executable, "-c", CODICE], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env,
                       cwd=tempfile.gettempdir())
    import json
    for riga in (r.stdout or "").splitlines():
        riga = riga.strip()
        if riga.startswith("{"):
            return json.loads(riga)
    return {"errore": (r.stderr or "")[-200:]}


def main():
    a = tempfile.mkdtemp(prefix="ws5_store_a_")
    b = tempfile.mkdtemp(prefix="ws5_store_b_")
    casi = [("store TEMPORANEO A", a), ("store TEMPORANEO B", b), ("nessuna variabile", None)]

    print("  %-22s %-30s %-8s %s" % ("regime", "file di discovery", "porta", "semantic_db"))
    print("  " + "-" * 104)
    letti = []
    for nome, dd in casi:
        r = chiedi(dd)
        letti.append((nome, r))
        if "errore" in r:
            print("  %-22s 🔴 %s" % (nome, r["errore"][:70]))
            continue
        print("  %-22s %-30s %-8s %s"
              % (nome, str(r["discovery_path"])[-30:], r["porta"] or "-",
                 str(r["semantic_db"])[-46:]))

    print("\n=== SINTESI ===")
    ok = [r for _, r in letti if "errore" not in r]
    if len(ok) < 2:
        print("  ⚠️ meno di due letture riuscite: non confrontabile.")
        return
    percorsi = {r["discovery_path"] for r in ok}
    db = {r["semantic_db"] for r in ok}
    porte = {r["porta"] for r in ok if r["porta"]}

    if len(percorsi) == 1:
        print("  🔴 IL FILE DI DISCOVERY E' LO STESSO in tutti i regimi:")
        print("     %s" % percorsi.pop())
        print("     ⇒ `HIPPO_DATA_DIR` NON isola il daemon.")
    else:
        print("  🟢 il file di discovery cambia col data dir: il daemon E' isolato.")

    if len(db) == len(ok):
        print("  ✅ CONTROLLO: il `semantic_db` invece CAMBIA in ogni regime")
        print("     ⇒ lo store e' davvero separato, e il difetto e' SOLO sul daemon.")
    else:
        print("  🔴🔴 CONTROLLO FALLITO: anche il `semantic_db` coincide fra regimi")
        print("       diversi ⇒ non isola nemmeno lo store, che sarebbe molto peggio.")

    if len(porte) == 1:
        print("  📌 e la porta letta e' la stessa (%s): tutti parlerebbero allo stesso"
              % porte.pop())
        print("     daemon, con il modello che ha caricato LUI.")


main()
