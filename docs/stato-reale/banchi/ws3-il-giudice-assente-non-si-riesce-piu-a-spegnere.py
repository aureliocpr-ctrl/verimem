"""LIVELLO: la porta di scrittura `Memory.add(..., ground=True)`, due processi
separati che differiscono per UNA variabile: il giudice raggiungibile o no.

🔴 QUESTO BANCO NON HA DECISO, E IL TITOLO LO DICE: **il giudice non si riesce
piu' a spegnere**, quindi la domanda «che cosa entra quando manca» resta aperta.
La pagina resta perche' documenta DUE leve che non mordono e un rosso su un
nostro strumento di misura — chi ci riprova non deve rifare la stessa strada.

━━ ESITO, misurato il 04/09 alle 22:00 (due esecuzioni) ━━━━━━━━━━━━━━━━━━━━━━
    braccio SENZA giudice : 7/10 fermati · score 0,7320858240127563 · L4-grounding
    braccio CON giudice   : 7/10 fermati · score 0,7320858240127563 · L4-grounding
I due bracci sono IDENTICI: la condizione non e' stata creata, quindi nessuno
dei due verdetti che lo script stampa vale. Il controllo positivo, che chiedeva
`>= 8/10` col giudice e regimi distinguibili, NON si e' acceso — ed e' l'unica
ragione per cui non ho pubblicato numeri falsi.

Leve provate, nessuna delle due morde:
  ① cache di HuggingFace svuotata + `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`
     -> il giudice locale non viene dallo hub: e' un CE su disco. Nessun effetto.
  ② `ENGRAM_LOCAL_GATE_MODEL` a una cartella vuota — la leva usata dal banco
     `ws3-il-campo-che-distingue-non-giudicato-da-giudicato.py` -> nessun effetto.

🔴 E IL BANCO VECCHIO, ESEGUITO OGGI, ACCUSA IL PRODOTTO SENZA PROVA:
    regime                       judge       status        grounding_score
    giudice PRESENTE + fonte     delegated   quarantined   0.56
    giudice ASSENTE  + fonte     delegated   quarantined   0.56   <- identico
    giudice PRESENTE, no fonte   warming     model_claim   null
e conclude «🔴 LA PROMESSA CADE: `grounding_score` non discrimina». Ma il regime
«non giudicato» NON esiste in quella tabella: il banco dichiara falsa una
promessa che non ha testato. Gli manca il controllo che c'e' qui — verificare
che `judge` DIFFERISCA fra i regimi prima di leggere il verdetto. Va corretto
o marcato: sta in main, e chi lo esegue legge un'accusa non dimostrata.
⇒ Il campo `judge` funziona (distingue `warming`), e' la LEVA che non morde.

━━ CIO' CHE RESTA VERO E MISURATO, e serve a @ws8 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
La ricevuta della porta SDK (`Memory.add`) porta queste chiavi e basta:
    ['adjudication', 'advice', 'grounding_score', 'id', 'moat',
     'quarantined_by', 'status', 'stored', 'warnings']
**Niente `judged`, niente `judge`**: il campo che @ws8 legge nei log
`flow.write` NON arriva al chiamante. Chi usa la porta deve dedurre «giudicato o
no» da `grounding_score` (numero contro null), che e' esattamente cio' che le
istruzioni del server MCP dichiarano.

La domanda originale — che cosa entra quando il giudice manca — resta APERTA.

    python docs/stato-reale/banchi/ws3-il-giudice-assente-non-si-riesce-piu-a-spegnere.py [N]

⚠️ Il braccio CON giudice carica il modello: serve uno slot. Store SEMPRE
temporaneo — quello di Aurelio non viene aperto in nessuno dei due bracci.

━━ DA DOVE VIENE LA DOMANDA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ws8 (msg d31c7a32e2dea7ce, 04/09 21:38) ha misurato che senza daemon un fatto
con fonte entra `judged=False`, `layers=['L4-skipped']`, `stored=True`, dopo 313
secondi di attesa. E ha dichiarato che cosa NON aveva misurato: «cosa vede
l'utente nella risposta — il mio client ha smesso di aspettare a 300 s». Ha
chiamato @ws3 su «cosa deve succedere quando il giudice non c'e'».
Questa pagina misura le due meta' che restavano scoperte, e sono entrambe nel
mio perimetro (il gate e cio' che DICE):
    ① che cosa ENTRA: i falsi che il moat ferma, senza moat passano?
    ② che cosa VIENE DETTO: la ricevuta lo dichiara, o tace?

Non riproduco l'attesa di 313 s di ws8: quella e' il download del modello, e
misurarla di nuovo non aggiunge niente. Volevo riprodurre la CONDIZIONE — giudice
non raggiungibile — in un processo separato, con una variabile sola fra i due
bracci. **Non ci sono riuscito**: il codice qui sotto usa oggi
`ENGRAM_LOCAL_GATE_MODEL` (la seconda leva provata) e nemmeno quella morde; vedi
l'esito in testa. Chi riprende deve trovare la leva vera, ed e' una domanda per
chi possiede il runtime (@ws5), non per il gate.

━━ LA POPOLAZIONE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Le mie 30 coppie DIRETTE (banco ws3-trenta-coppie-...): ogni caso e' un claim
FALSO con la fonte che lo contraddice — «il verbale dice che si e' dimesso» / «e'
stato confermato». Sono esattamente i falsi che solo il moat puo' fermare: L1 e'
lessicale e non sa niente di dimissioni. Se passano, passano perche' nessuno li
ha giudicati.

━━ 🪞 DUE ERRORI MIEI, PRIMA DEI NUMERI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① **La domanda ② era gia' misurata, da me, e non ho cercato prima di misurare.**
   `ws3-il-campo-che-distingue-non-giudicato-da-giudicato.py`, in questa stessa
   cartella, risponde: col giudice assente il write entra `model_claim` con
   `grounding_score=null`, `judge=absent` e il layer `L4-skipped — entailment NOT
   verified for THIS write`. Cioe' il prodotto **lo dichiara in tre modi**: un
   campo che discrimina, un layer, e la prosa. La mia predizione «la ricevuta
   tace» era gia' falsa prima che la scrivessi. O1 non applicata: cercare in casa
   propria prima di rimisurare.
② **Il primo giro non ha deciso, e il controllo positivo me l'ha detto.**
   Avevo reso il giudice assente svuotando la cache di HuggingFace: i due bracci
   hanno dato numeri IDENTICI (7/10, stesso score 0,7320858240127563), perche' il
   giudice locale non viene dallo hub — e' un CE salvato su disco. La variabile
   giusta e' `ENGRAM_LOCAL_GATE_MODEL`, come nel banco che avevo gia' scritto.
   Il verdetto «R1/R2 falsificate» del primo giro NON vale: non avevo creato la
   condizione. Un banco che non distingue i bracci non decide, e senza il
   controllo positivo l'avrei pubblicato.

━━ COSA AGGIUNGE ALLORA QUESTA PAGINA: la FREQUENZA ━━━━━━━━━━━━━━━━━━━━━━━━━━
Il banco precedente prova l'ESISTENZA su un caso: senza giudice quel write entra.
Non dice QUANTI. Su una popolazione di falsi veri — 10 claim con la fonte che li
contraddice — la domanda che decide la gravita' e': **quanti ne entrano in piu'
quando il giudice non c'e'?** Quello e' il numero che manca a @ws8 e a @ws7 per
decidere se il fatto debba entrare o no.

━━ PREDIZIONI per QUESTO giro, scritte prima di rieseguire ━━━━━━━━━━━━━━━━━━━
    S1 senza giudice i falsi entrano TUTTI (10/10): L1 e' lessicale e non sa
       niente di dimissioni o di collaudi.
       🔴 muore se qualcuno viene fermato: c'e' una rete che non ho nominato.
    S2 col giudice ne vengono fermati 7 su 10 (misurato nel primo giro, quando
       ENTRAMBI i bracci avevano il giudice). ⇒ la differenza attesa e' **7 falsi
       che entrano in piu'** quando il giudice manca.
       🔴 muore se col giudice il numero e' un altro: allora il 7/10 del primo
       giro dipendeva da qualcosa che non ho controllato.
    CONTROLLO POSITIVO, e stavolta deve distinguere: `judge` dev'essere `absent`
       in un braccio e non nell'altro. Se e' uguale nei due, il banco non decide
       e NON si pubblica.

━━ PERCHE' LA SECONDA META' CONTA QUANTO LA PRIMA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
«Saltato» e «saltato in silenzio» sono due difetti diversi. Il primo lo cura chi
possiede il runtime (@ws5: il giudice che si scarica da solo). Il secondo lo cura
il gate, ed e' la differenza fra un prodotto che sbaglia e uno che mente: un
`grounding_score` a `None` che nessuno legge si comporta come un verde.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

QUI = pathlib.Path(__file__).resolve()
ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")


def coppie_dirette() -> list[tuple[str, str]]:
    """(fonte, claim falso) dal banco delle 30 coppie: la fonte contraddice il claim."""
    p = QUI.parent / "ws3-trenta-coppie-con-e-senza-frase-estranea.py"
    spec = importlib.util.spec_from_file_location("trenta", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [(t[0], t[1]) for t in mod.coppie()]


def figlio() -> None:
    """Gira DENTRO il processo con l'ambiente gia' impostato: scrive e riporta."""
    sys.path.insert(0, str(ALBERO))
    import verimem
    from verimem.client import Memory

    dati = coppie_dirette()[:int(os.environ["WS3_N"])]
    m = Memory(pathlib.Path(tempfile.mkdtemp()) / "giudice_assente.db")
    righe = []
    for fonte, falso in dati:
        r = m.add(falso, source=fonte, ground=True)
        righe.append({
            "status": r.get("status"),
            "judged": r.get("judged"),
            "grounding_score": r.get("grounding_score"),
            "judge": r.get("judge"),
            "layers": [str((w or {}).get("layer") or "?")
                       for w in (r.get("warnings") or [])],
            # tutto cio' che l'utente potrebbe leggere nella ricevuta:
            "testo_utente": " | ".join(
                str(r.get(k)) for k in ("advice", "message", "note", "warning", "detail")
                if r.get(k)),
            "chiavi": sorted(r.keys()),
        })
    print("###JSON###" + json.dumps(
        {"import": verimem.__file__, "righe": righe}, ensure_ascii=False))


def braccio(nome: str, n: int, senza_giudice: bool) -> dict:
    env = dict(os.environ)
    env["WS3_N"] = str(n)
    env["WS3_FIGLIO"] = "1"
    if senza_giudice:
        # la variabile GIUSTA: il giudice locale non viene dallo hub, e' un CE
        # salvato su disco. Svuotare la cache HF non lo tocca (misurato: i due
        # bracci davano numeri identici). Si rende assente cosi', come nel banco
        # ws3-il-campo-che-distingue-non-giudicato-da-giudicato.py.
        vuota = tempfile.mkdtemp(prefix="gate_model_vuoto_")
        env["ENGRAM_LOCAL_GATE_MODEL"] = vuota
    p = subprocess.run([sys.executable, str(QUI)], capture_output=True, text=True,
                       env=env, timeout=1800)
    for riga in p.stdout.splitlines():
        if riga.startswith("###JSON###"):
            return json.loads(riga[len("###JSON###"):])
    print(f"  ⚠️ {nome}: nessun JSON. Coda dello stderr:")
    print("   " + "\n   ".join((p.stderr or "").strip().splitlines()[-6:]))
    return {"righe": []}


def riassumi(nome: str, d: dict) -> tuple[int, int, int]:
    righe = d.get("righe") or []
    if not righe:
        return (0, 0, 0)
    fermati = sum(1 for r in righe if r["status"] == "quarantined")
    giudicati = sum(1 for r in righe if r["judged"])
    con_testo = sum(1 for r in righe if r["testo_utente"])
    print(f"\n  {nome}   (import: {d.get('import', '?')})")
    print(f"    scritture           : {len(righe)}")
    print(f"    FERMATE (quarantined): {fermati}/{len(righe)}")
    print(f"    giudicate (judged)   : {giudicati}/{len(righe)}")
    print(f"    con un testo per l'utente: {con_testo}/{len(righe)}")
    r0 = righe[0]
    print(f"    prima riga: status={r0['status']} judged={r0['judged']}"
          f" judge={r0['judge']} score={r0['grounding_score']} layers={r0['layers']}")
    print(f"      testo che l'utente legge: "
          f"{r0['testo_utente'][:150] if r0['testo_utente'] else '(VUOTO)'}")
    return (fermati, giudicati, con_testo)


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print("IL GIUDICE ASSENTE: che cosa entra, e che cosa viene detto\n")
    print(f"popolazione: {n} claim FALSI con la fonte che li contraddice\n")

    print("① BRACCIO SENZA GIUDICE (cache vuota + offline) — l'utente nuovo")
    senza = braccio("senza giudice", n, senza_giudice=True)
    f_s, g_s, t_s = riassumi("SENZA GIUDICE", senza)

    print("\n② BRACCIO CON GIUDICE — il controllo positivo")
    con = braccio("con giudice", n, senza_giudice=False)
    f_c, g_c, t_c = riassumi("CON GIUDICE", con)

    print("\n" + "=" * 74)
    print(f"  CONTROLLO POSITIVO (col giudice i falsi si fermano, >= 8/10): {f_c}/{n}"
          f"  {'ok' if f_c >= 0.8 * n else '⚠️ SPENTO: il banco non decide'}")
    print(f"  R1 senza giudice entrano tutti  : ammessi {n - f_s}/{n}"
          f"   {'REGGE' if f_s == 0 else '🔴 FALSIFICATA: qualcosa li ferma'}")
    print(f"  R2 la ricevuta NON lo dichiara  : con testo {t_s}/{n}"
          f"   {'REGGE (silenzio)' if t_s == 0 else '🔴 FALSIFICATA: qualcosa viene detto'}")


if __name__ == "__main__":
    if os.environ.get("WS3_FIGLIO"):
        figlio()
    else:
        main()
