r"""La cura del moat spento: dove innestarla, quanto costa, e cosa NON cura.

@lead-audit: «*il primo remember con source (o l'avvio di `verimem mcp`) si procura il
giudice da solo — `ensure_gate_model()` e' chiamata solo dal warmup (`cli.py:594`):
proponi il punto d'innesto e la misura prima/dopo, nasce ACCESA*».

Questo file **misura i numeri che la decisione richiede** e propone l'innesto. Non
modifica `verimem/`: la modifica e' una scelta di prodotto, i numeri no.

═══ IL DIFETTO, misurato oggi sul pacchetto 0.7.1 servito da PyPI ═══

    utente nuovo, HOME vergine, `pip install verimem==0.7.1`, poi:
      $ verimem remember "<claim falso>" --source "<fonte che lo smentisce>"
        flow.write  layers=[]  status=model_claim  stored=True
        admitted                                                    EXIT=0

⇒ **Il claim falso entra, e nulla lo dice.** `doctor` lo sa e lo spiega benissimo
(«*NO grounding judge … writes are admitted with an L4-skipped advisory (moat OFF)*»),
ma `doctor` e' il comando che un utente **non lancia**; `remember` e' quello che lancia.
⇒ E l'«L4-skipped advisory» che `doctor` promette **non compare nell'output di
`remember`**.

═══ IL PUNTO D'INNESTO — `local_grounding.py:175`, `_ensure_scorer()` ═══

Oggi, quando il modello non c'e'::

    try:
        self._scorer = make_finetuned_scorer(self.model_dir, ...)
    except Exception as exc:
        self._load_failed = True          # <- cachea il fallimento: MAI un secondo tentativo
        _emit_flow("flow.warmup", ..., phase="failed", reason=...)
        raise

⚠️ **E il commento accanto dice PERCHE' quel cache esiste**: «*a broken/absent model must
not re-pay the load attempt on every gated write*». ⇒ **La cura non e' «chiama
`ensure_gate_model()` qui»**: e' **distinguere ASSENTE da ROTTO**, scaricare solo nel
primo caso, e cachear comunque dopo **un** tentativo. Chi innesta senza quella distinzione
reintroduce esattamente il costo che quel cache evita.

═══ QUANTO COSTA — misurato, non stimato ═══

    ensure_gate_model() da sola, HOME vergine     26,9s   (711,5 MB a 26,4 MB/s)
    caricamento del modello in-process            16,2s
    ---------------------------------------------------
    primo write con source, CON la cura          ~43s     poi 0,217s a giudizio

    per confronto, gia' misurati:
    warmup completo (reranker+gate+daemon)       8m37s    <- NON e' il download del gate
    prima scrittura MCP con source, SENZA cura    >90s    <- import di scipy (W5-31..34)

🔑 **Il download NON e' il collo di bottiglia**: 27s contro i >90s che la porta MCP gia'
paga per l'import di `scipy`. ⇒ **L'innesto nel write path e' praticabile**, e chi teme
che «scaricare 700 MB al primo write» sia proibitivo sta stimando 8 minuti quando sono 27
secondi — l'8m37s del warmup e' quasi tutto **reranker** (153,5s) e altro.

⚠️ **Ma 26,4 MB/s e' la MIA rete.** A 2 MB/s lo stesso download sono **~6 minuti**. ⇒ Il
numero da mettere nella decisione non e' «27s»: e' «**711,5 MB**», e i secondi dipendono
da chi installa.

✅ ESEGUITO END-TO-END (19:18, una sola esecuzione, HOME nuova)::

    ensure_gate_model()                13,4s    711,5 MB
    1o giudizio (carica il modello)    54,1s    grounding  0,5308  (claim FALSO)
    2o giudizio (modello caldo)         0,2s    grounding 99,6747  (claim VERO)
    ------------------------------------------------------------------
    costo della cura sul primo write   67,5s    poi 0,184s a giudizio

✅ **Controllo positivo E negativo nella stessa esecuzione**: il falso prende **0,53**,
il vero **99,67**. ⇒ Il giudice non e' solo presente: **separa**.

⚠️ **E I TEMPI VARIANO MOLTO — un numero solo ingannerebbe**::

    download      13,4s  ..  26,9s     (due esecuzioni, stessa rete, stesso file)
    caricamento   16,2s  ..  54,1s     (braccio A pulito .. questa esecuzione)
    ---------------------------------
    primo write     30s  ..    81s

⇒ Quello che **non** varia e' la proporzione: **il download e' una frazione del costo**,
e il caricamento — che si paga **gia' oggi, senza nessuna cura** — e' la parte grossa.
⇒ **La cura aggiunge 13-27s a un'operazione che gia' ne costa 16-54.**

═══ LA PROPOSTA, e cosa la rende diversa da «scarica e basta» ═══

  ①  **`_ensure_scorer()` distingue assente da rotto.** Se la cartella non esiste ->
     `ensure_gate_model()` e UN retry. Se esiste ed e' illeggibile -> comportamento di
     oggi (cache del fallimento, nessun download).
  ②  **`VERIMEM_OFFLINE=1` la disattiva** — esiste gia' ed e' citata da `doctor`
     («*for air-gapped deploys*»). Un download automatico che ignora quella variabile
     rompe una promessa scritta.
  ③  **L'avviso resta anche quando la cura NON scatta**: se il download fallisce o e'
     disattivato, `remember` deve DIRE che sta ammettendo senza giudicare. E' il pezzo
     che oggi manca del tutto, e da solo vale piu' del download automatico: **un utente
     informato puo' decidere; uno che legge solo `admitted` no.**
  ④  **Nasce ACCESA** (direttiva Aurelio), con ② come unica via per spegnerla.

═══ LA MISURA PRIMA/DOPO, da eseguire sulla build con la cura ═══

    caso                              PRIMA (misurato)        DOPO (atteso)
    primo write con source, HOME nuova  admitted, layers=[]     fermato, ['L4-grounding']
    durata del primo write              23,6s                   ~43s (+27s una volta)
    secondo write                       23,6s  non giudicato    0,217s giudicato
    con VERIMEM_OFFLINE=1               admitted, silenzioso    admitted + AVVISO
    modello ROTTO (non assente)         admitted, silenzioso    admitted + AVVISO, 1 solo
                                                                tentativo (nessun loop)

⇒ Le ultime due righe sono i **controlli negativi**: senza, una cura che scarica sempre
passerebbe per buona anche se ignora `OFFLINE` o riprova all'infinito su un modello rotto.

⚖️ **COSA QUESTA CURA NON CURA, e va detto**: la porta **MCP** non giudica per un'altra
ragione (`W5-30`: nel pacchetto `mcp_server.py` non passa mai `ground_write`, 0 occorrenze
contro 7 su `main`), e la prima scrittura MCP non torna per l'import di `scipy`
(`W5-31..34`). ⇒ **Tre difetti distinti sulla stessa superficie**: procurarsi il modello
ne risolve **uno**.

RIPRODUCI (la misura del costo):
  python docs/stato-reale/banchi/ws5-il-giudice-si-procura-da-solo-proposta.py <venv> <home-nuova>
"""
import os
import subprocess
import sys

if os.environ.get("_WS5_PULITO") != "1":
    # il filtro sta DENTRO lo script: uno nel comando puo' saltare (mi e' successo oggi,
    # e i numeri sono usciti meta' di quelli veri)
    if len(sys.argv) < 3:
        print("uso: python %s <venv> <home-nuova>" % sys.argv[0])
        raise SystemExit(2)
    venv, home = sys.argv[1], os.path.abspath(sys.argv[2])
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        print("  🔴 venv assente: %s" % venv)
        raise SystemExit(1)
    os.makedirs(home, exist_ok=True)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env.update({"_WS5_PULITO": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "HOME": home, "USERPROFILE": home,
                "HIPPO_DATA_DIR": os.path.join(home, "store")})
    raise SystemExit(subprocess.run([py, "-u", os.path.abspath(__file__)] + sys.argv[1:],
                                    env=env).returncode)

import time
from pathlib import Path

from verimem.local_grounding import DEFAULT_MODEL_DIR, ensure_gate_model

print("  HOME isolata: %s" % os.environ.get("HOME"))
gia = Path(DEFAULT_MODEL_DIR).exists()
print("  il modello c'e' gia'? %s" % ("SI — la misura del DOWNLOAD non varrebbe" if gia
                                      else "no: si misura un download vero"))
t = time.time()
got, msg = ensure_gate_model()
dur = time.time() - t
print("\n  ensure_gate_model()   got=%s   %.1fs" % (got, dur))
d = Path(DEFAULT_MODEL_DIR)
if d.exists():
    mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1048576.0
    print("  scaricato: %.1f MB   ⇒ %.1f MB/s" % (mb, mb / dur if dur else 0))
    print("  ⚠️ i secondi sono della RETE di chi misura: a 2 MB/s sarebbero %.0f minuti"
          % (mb / 2 / 60))

# il caricamento in-process, che si somma al download sul PRIMO write
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
from verimem.anti_confab_gate import run_validation_gate
t = time.time()
g = run_validation_gate(proposition="Nella coda ci sono 7777 run in corso.",
                        verified_by=None, topic=None, agent=None,
                        source=FONTE, ground_write=True)
carico = time.time() - t
t = time.time()
g2 = run_validation_gate(proposition="Nella coda ci sono 149 run in attesa.",
                         verified_by=None, topic=None, agent=None,
                         source=FONTE, ground_write=True)
secondo = time.time() - t
print("\n  1o giudizio (carica il modello):  %6.1fs   grounding %s"
      % (carico, getattr(g, "grounding_score", None)))
print("  2o giudizio (modello caldo):      %6.1fs   grounding %s"
      % (secondo, getattr(g2, "grounding_score", None)))
if getattr(g, "grounding_score", None) is None:
    print("  ⚠️ grounding None: il giudice NON ha girato ⇒ i tempi non sono di giudizio.")
else:
    print("\n  ⇒ COSTO DELLA CURA sul primo write: %.1fs (download) + %.1fs (carico) = %.1fs"
          % (dur, carico, dur + carico))
    print("    e da li' in poi: %.3fs a giudizio" % secondo)
