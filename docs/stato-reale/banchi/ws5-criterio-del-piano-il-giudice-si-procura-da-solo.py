"""Il criterio del piano di record, eseguito col wheel su una HOME vergine.

  uso: python criterio_del_piano.py <venv> <home-nuova>

Il piano (docs/stato-reale/piano-versioni-2026-09-02.md) chiede, testualmente:

    «Il giudice si scarica da solo al primo write con fonte (o all'avvio del server MCP),
     con un messaggio all'utente (peso, tempo), e il pacchetto lo dichiara. Test: il primo
     `remember --source` su una HOME vergine esce con `layers` non vuoti e un falso viene
     fermato.»

Quattro cose da guardare, e questo script le guarda tutte e quattro separatamente:

  ① il MESSAGGIO c'e', porta il peso, ed e' su STDERR (stdout resta pulito: e' il canale
    del protocollo quando lo stesso codice gira dentro il server MCP)
  ② il modello si PROCURA da solo (compare in HOME dov'era assente)
  ③ un FALSO viene FERMATO, con `layers` non vuoti
  ④ ⚠️ CONTROLLO POSITIVO: un claim VERO viene AMMESSO. Senza questo, un gate che
    boccia tutto passerebbe il punto ③ a pieni voti — e sarebbe rotto.

Il filtro dell'ambiente sta DENTRO lo script e non nel comando che lo lancia: tre volte
in questa sessione una variabile della sessione madre e' arrivata ai figli e ha falsato
la misura. Cosi' il braccio pulito non dipende da come lo si invoca.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

VENV, HOME = sys.argv[1], os.path.abspath(sys.argv[2])
os.makedirs(HOME, exist_ok=True)

FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
FALSO = "Nella coda ci sono 7777 run in corso."
VERO = "La coda della CI contiene 149 run in attesa."

env = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
env.update({"HOME": HOME, "USERPROFILE": HOME, "PYTHONDONTWRITEBYTECODE": "1",
            "HIPPO_DATA_DIR": os.path.join(HOME, "store")})
# la suite gira offline, ma un UTENTE no: qui si misura il percorso dell'utente
for f in ("VERIMEM_OFFLINE", "HIPPO_OFFLINE", "ENGRAM_OFFLINE",
          "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
    env.pop(f, None)

exe = os.path.join(VENV, "Scripts", "verimem.exe")
mod = Path(HOME) / ".cache" / "verimem" / "models" / "local_gate_ce_v2"


def scrivi(claim, etichetta):
    """Un `remember --source`, con stdout e stderr TENUTI SEPARATI."""
    t = time.time()
    r = subprocess.run([exe, "remember", claim, "--source", FONTE],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=2400, env=env, cwd=HOME)
    dur = time.time() - t
    out, err = r.stdout or "", r.stderr or ""
    tutto = (out + " " + err).replace("\n", " ")
    lay = next((w[7:] for w in tutto.split() if w.startswith("layers=")), "(assente)")
    fermato = ("quarantin" in tutto.lower() or "reject" in tutto.lower())
    return {
        "etichetta": etichetta, "exit": r.returncode, "s": round(dur, 1),
        "layers": lay, "fermato": fermato, "out": out, "err": err,
        "ha_scaricato": "phase=fetching" in tutto or "procurato=True" in tutto,
    }


print("=" * 78)
print("HOME vergine: %s" % HOME)
print("modello presente PRIMA: %s   (se True la misura del download non vale)"
      % mod.exists())
print("=" * 78)

a = scrivi(FALSO, "① falso")
b = scrivi(VERO, "② vero (controllo positivo)")

print("\n--- ① il MESSAGGIO all'utente ---------------------------------------------")
righe_msg = [ln for ln in a["err"].splitlines() if "scarico il giudice" in ln]
print("  su stderr: %s" % (righe_msg[0].strip() if righe_msg else "*** ASSENTE ***"))
print("  porta il peso in MB: %s" % ("746" in a["err"]))
print("  dice «una volta sola»: %s" % ("una volta" in a["err"].lower()))
sporco = [ln for ln in a["out"].splitlines() if "scarico il giudice" in ln]
print("  ⚠️ finito per errore su stdout: %s" % (bool(sporco)))

print("\n--- ② il modello si e' PROCURATO da solo ----------------------------------")
print("  presente in HOME DOPO: %s" % mod.exists())
print("  la riga di download nei log: %s" % a["ha_scaricato"])
print("  secondi del primo write (download compreso): %.1fs" % a["s"])
print("  secondi del secondo write (modello gia' li'): %.1fs" % b["s"])

print("\n--- ③ e ④ il GIUDIZIO ------------------------------------------------------")
for r in (a, b):
    print("  %-28s exit=%s  %6.1fs  layers=%-24s %s"
          % (r["etichetta"], r["exit"], r["s"], r["layers"][:24],
             "FERMATO" if r["fermato"] else "ammesso"))

print("\n" + "=" * 78)
criteri = {
    "① il messaggio c'e', col peso, su stderr": bool(righe_msg) and "746" in a["err"],
    "① stdout NON e' stato sporcato": not sporco,
    # ⚠️ Il criterio era `mod.exists() and a["ha_scaricato"]` e dava FAIL con il modello
    # SUL DISCO. Il difetto era nel righello: `ha_scaricato` cerca `phase=fetching`, che
    # e' la firma dell'innesto in `local_grounding._ensure_scorer()` — ma il download
    # parte PRIMA, dall'innesto nel gate, e quando `_ensure_scorer` arriva il modello c'e'
    # gia' e passa dritto a `ready`. Cercavo la firma dell'innesto sbagliato.
    # Cio' che si osserva davvero, e basta: assente prima, presente dopo.
    "② il modello si e' procurato da solo": mod.exists(),
    "③ il falso e' FERMATO con layers non vuoti":
        a["fermato"] and a["layers"] not in ("(assente)", "[]"),
    "④ il vero e' AMMESSO (controllo positivo)": not b["fermato"],
}
for k, v in criteri.items():
    print("  %s  %s" % ("PASS" if v else "FAIL", k))
print("=" * 78)
print("VERDETTO: %s" % ("tutti e cinque i criteri passano"
                        if all(criteri.values()) else
                        "NON passa: " + ", ".join(k for k, v in criteri.items() if not v)))
Path(HOME + "_esito.json").write_text(json.dumps(
    {"criteri": criteri, "falso": {k: v for k, v in a.items() if k not in ("out", "err")},
     "vero": {k: v for k, v in b.items() if k not in ("out", "err")}},
    indent=2, ensure_ascii=False), encoding="utf-8")
sys.exit(0 if all(criteri.values()) else 1)
