"""Il recall toglie fatti e lo DICHIARA. Ma da quali porte esce quella riga?

    python docs/stato-reale/banchi/ws6-quante-porte-dicono-cosa-hanno-tolto.py

`Risultati` ha cinque avvisi — `sotto_il_pavimento`, `tagliati_dal_pavimento`,
`letto_al_passato`, `trattenuti`, e da oggi `esclusi_perche_scaduti`. Ognuno
esiste perche' una lettura toglieva materiale senza dirlo, e l'assenza del
campo si legge come «non ha tolto nulla».

⚠️ MA UN CAMPO ESISTE SULL'OGGETTO, NON SULLA PORTA. Un `grep` dei nomi dice
che nessuno dei cinque compare in `cli.py` — e un grep di un nome NON prova
un'assenza: la CLI potrebbe leggerli per altra via (getattr dinamico, un dict,
un serializzatore che copia tutti gli attributi). L'assenza si prova
ESEGUENDO. Questo banco esegue.

METODO: si prepara uno store con due fatti sulla stessa cosa, uno scaduto, poi
si fa la STESSA domanda da ogni porta disponibile e si guarda se la riga esce.

⚠️ CONTROLLO POSITIVO, senza il quale il banco non misura niente: la porta
deve rispondere. Se una porta non servisse NULLA, l'assenza dell'avviso non
direbbe «non lo espone», direbbe «non ha risposto» — due cose diverse, e la
seconda non e' un difetto dell'avviso.

⛔ Store isolato in tempdir: non tocca lo store di casa.
"""
import json
import os
import subprocess
import sys
import tempfile

_RADICE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _RADICE)

_tmp = tempfile.mkdtemp(prefix="ws6_porte_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

SCADUTO = "Il deposito di Verona ospita quattromilaseicento pallet di ricambi."
F_SCAD = "Inventario: il deposito di Verona ospita 4600 pallet di ricambi."
VIVO = "Il deposito di Verona custodisce pallet di imballaggi in un'area coperta."
F_VIVO = ("Inventario: il deposito di Verona custodisce pallet di imballaggi "
          "in un'area coperta.")
QUERY = "quanti pallet ospita il deposito di Verona"

import time  # noqa: E402

m = Memory()
m.add(SCADUTO, topic="porte/scaduto", source=F_SCAD, valid_until=time.time() - 86_400)
m.add(VIVO, topic="porte/vivo", source=F_VIVO)

print("QUANTE PORTE DICONO CHE LA SCADENZA HA TOLTO QUALCOSA\n")
print("  %-16s %-9s %-9s %s" % ("porta", "risponde", "dichiara", "cosa si vede"))

righe = []

# ── porta 1: SDK ──────────────────────────────────────────────────────────
r = m.recall(QUERY, k=10)
av = getattr(r, "esclusi_perche_scaduti", None)
righe.append(("SDK (Memory)", bool(len(r)), av is not None,
              json.dumps(av, ensure_ascii=False)[:44] if av else "—"))

# ── porta 2: CLI ──────────────────────────────────────────────────────────
env = dict(os.environ)
for cmd in (["recall", QUERY], ["search", QUERY]):
    try:
        p = subprocess.run([sys.executable, "-m", "verimem.cli"] + cmd,
                           capture_output=True, text=True, timeout=300,
                           cwd=_RADICE, env=env, encoding="utf-8", errors="replace")
        out = (p.stdout or "") + (p.stderr or "")
    except Exception as e:                    # noqa: BLE001 — il banco misura
        out = "ERRORE: %s" % e
    risponde = ("Verona" in out) or ("imballaggi" in out)
    dichiara = ("scadut" in out.lower()) or ("esclusi_perche_scaduti" in out)
    estratto = next((L.strip() for L in out.splitlines()
                     if "scadut" in L.lower()), "—")
    righe.append(("CLI %s" % cmd[0], risponde, dichiara, estratto[:44]))

for nome, risp, dich, vis in righe:
    print("  %-16s %-9s %-9s %s" % (
        nome, "si" if risp else "NO", "SI" if dich else "no", vis))

print("\n  ── LETTURA ──")
mute = [n for n, risp, dich, _ in righe if risp and not dich]
morte = [n for n, risp, _, _ in righe if not risp]
if morte:
    print("  ⚠️ porte che NON RISPONDONO: %s" % ", ".join(morte))
    print("     per queste il banco non dice nulla sull'avviso: una porta che")
    print("     non risponde non e' una porta che tace, e' un'altra domanda.")
if mute:
    print("  ⛔ porte che RISPONDONO e NON DICHIARANO: %s" % ", ".join(mute))
    print("     chi le usa riceve una risposta ridotta dalla scadenza senza")
    print("     alcun modo di accorgersene.")
if not mute and not morte:
    print("  ✅ ogni porta che risponde dichiara anche cosa ha tolto.")
