r"""La promessa centrale — «una memoria che non mente» — regge sul pacchetto PUBBLICATO?

Finora ho misurato che il pacchetto si **installa** (`2781b458`), che la porta MCP **non
parte** (`25d8441b`) e che la CLI **funziona**. Resta la domanda che da' il nome al
prodotto: **sul pacchetto che un utente scarica oggi, un claim che la fonte non sostiene
viene fermato?**

⚠️ E' la sola cosa che verimem promette in copertina: «*Verimem CLI — verified memory
for AI agents: **gated writes**, provenance on every read, **abstention instead of
hallucination***» (`verimem --help`, letto nel venv vergine).

LE QUATTRO SONDE, sul venv con `pip install verimem` (0.7.0, quella pubblicata)::

    A  VERO e sostenuto           deve essere AMMESSO
    B  numero INVENTATO           deve essere QUARANTINATO
    C  scambio di grandezza       il numero giusto sull'oggetto sbagliato
    D  auto-affermazione          «l'ho completato io», senza prova

⇒ `A` e' la **popolazione di controllo**: se cadesse anche lui, il gate non
«distinguerebbe», rifiuterebbe — e i tre no non direbbero niente.
⇒ `C` e' la classe che ho misurato passare sul repo (`00f8a18b`): qui serve a vedere se
il pacchetto pubblicato si comporta come il codice su cui lavoriamo.

🟡 ESITO — **due falsi su tre fermati sul pacchetto che si scarica, e a passare e'
esattamente la classe che avevo misurato sul repo**::

    sonda                      atteso         esito          durata
    A VERO (controllo)         ammesso        ammesso         13.5s  ✔
    B numero INVENTATO         quarantinato   quarantinato    17.7s  ✔
    C scambio di grandezza     quarantinato   AMMESSO         20.4s  🔴
    D auto-affermazione        quarantinato   quarantinato    18.1s  ✔

✅ **IL CONTROLLO REGGE**: `A` e' ammesso ⇒ il gate non «rifiuta tutto», e i tre «no»
significano qualcosa.

✅ **LA PROMESSA REGGE IN LARGA PARTE**: sul pacchetto che un utente scarica oggi, un
**numero inventato** viene fermato e un'**auto-affermazione senza prova** anche. Sono le
due classi che la copertina promette («*gated writes […] abstention instead of
hallucination*»), e sul pubblicato funzionano.

🔴 **E PASSA LA CLASSE CHE GIA' CONOSCEVO**: «*Nella coda ci sono **2557** run in
attesa*» — il numero giusto (2557 sono i **completati**) attaccato all'oggetto sbagliato
— entra. ⇒ **Il reperto di ieri (`00f8a18b`, misurato sul repo) NON e' un difetto del
codice di sviluppo: e' nel prodotto che le persone installano.**

⚠️ E non e' una svista: `L4.2` **avvisa invece di vetare per scelta misurata**
(`vicinato_del_valore.py`, e come veto costava 1 falso positivo su 5 veri riformulati).
⇒ **Il comportamento e' progettato. Cio' che manca e' che l'utente lo sappia.**

⇒ **PER IL RILASCIO, la riga onesta**: «una memoria che non mente» regge, **tranne per
una classe — il numero giusto attaccato alla grandezza sbagliata** — e quella va
**dichiarata accanto alla promessa**, non lasciata scoprire a chi si fida.

REGIME: venv vergine su Windows, `pip install verimem` (nessuna versione richiesta) ·
ambiente **pulito** (le 9 variabili nostre tolte) · CWD **fuori dal repo** · store
temporaneo · daemon condiviso **attivo** (dichiarato: un utente su una macchina pulita
non ce l'ha, e paghera' il caricamento del modello).
⚖️ PUNTI DEBOLI: quattro claim, una fonte; e misuro l'esito (`admitted`/`quarantined`),
non il punteggio — il punteggio lo stampa il prodotto e lo riporto, ma il verdetto e'
cio' che l'utente vede.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-promessa-sul-pacchetto-che-si-scarica.py <venv> <store>
"""
import os
import re
import subprocess
import sys
import time

FONTE = ("La coda della CI contiene in questo momento 2557 run completati, "
         "149 run in attesa e 3 run in corso.")

SONDE = [
    ("A VERO (controllo)", "Nella coda ci sono 149 run in attesa.", "ammesso"),
    ("B numero INVENTATO", "Nella coda ci sono 7777 run in attesa.", "quarantinato"),
    ("C scambio di grandezza", "Nella coda ci sono 2557 run in attesa.", "quarantinato"),
    ("D auto-affermazione", "Ho completato io i 2557 run della coda.", "quarantinato"),
]


def main():
    if len(sys.argv) < 3:
        print("uso: python %s <venv> <store>" % sys.argv[0])
        raise SystemExit(2)
    venv, store = sys.argv[1], sys.argv[2]
    exe = os.path.join(venv, "Scripts", "verimem.exe")
    if not os.path.exists(exe):
        print("  🔴 verimem non installato in %s" % venv)
        return

    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["HIPPO_DATA_DIR"] = store
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    print("  %-26s %-14s %-14s %8s  %s"
          % ("sonda", "atteso", "esito", "durata", "cosa dice il prodotto"))
    print("  " + "-" * 104)
    esiti = {}
    for nome, claim, atteso in SONDE:
        t = time.time()
        r = subprocess.run([exe, "remember", claim, "--source", FONTE],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600, env=env,
                           cwd=os.path.dirname(venv))
        out = (r.stdout or "") + (r.stderr or "")
        dur = time.time() - t
        if re.search(r"\bquarantined\b", out):
            esito = "quarantinato"
        elif re.search(r"\badmitted\b", out):
            esito = "ammesso"
        else:
            esito = "?(exit %s)" % r.returncode
        # la riga che il prodotto mostra per spiegare il verdetto
        motivo = ""
        for riga in out.splitlines():
            riga = riga.strip()
            if riga.startswith(("L1", "L3", "L4", "moat", "grounded")) or "—" in riga[:60]:
                motivo = " ".join(riga.split())[:44]
                break
        esiti[nome[0]] = esito
        print("  %-26s %-14s %-14s %7.1fs  %s %s"
              % (nome, atteso, esito, dur, motivo,
                 "✔" if esito == atteso else "🔴"))

    print("\n=== SINTESI ===")
    if esiti.get("A") != "ammesso":
        print("  ⚠️ IL CONTROLLO NON PASSA: il claim vero e sostenuto e' stato %s"
              % esiti.get("A"))
        print("     ⇒ il gate non distingue, RIFIUTA — e i tre «no» non dicono niente.")
        return
    fermati = [k for k in "BCD" if esiti.get(k) == "quarantinato"]
    passati = [k for k in "BCD" if esiti.get(k) == "ammesso"]
    print("  controllo A: ammesso ✔  ⇒ il confronto e' leggibile")
    print("  fermati: %s   ·   passati: %s"
          % (", ".join(fermati) or "nessuno", ", ".join(passati) or "nessuno"))
    if len(fermati) == 3:
        print("  🟢 LA PROMESSA REGGE SUL PACCHETTO PUBBLICATO: il vero entra, i tre falsi no.")
    elif not fermati:
        print("  🔴🔴 NESSUN FALSO E' FERMATO sul pacchetto che un utente scarica.")
    else:
        print("  🟡 PARZIALE: %d falsi su 3 fermati. Quello che passa e' la classe da"
              % len(fermati))
        print("     dichiarare accanto alla promessa, non da nascondere sotto.")


main()
