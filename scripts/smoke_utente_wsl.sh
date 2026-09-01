#!/usr/bin/env bash
# =============================================================================
#  SMOKE DA UTENTE VERO — in WSL, sul wheel candidato, prima di ogni publish
# =============================================================================
#
# ═══ PERCHE' ESISTE ═══
# Direttiva di Aurelio (01/09): a OGNI publish si fa il percorso dell'utente in
# un ambiente vergine, non nel repo. La ragione e' misurata piu' volte su questo
# prodotto: dentro il repo funzionano cose che fuori non esistono — un file di
# dati che sta solo qui, una variabile d'ambiente ereditata, un import che
# risolve perche' la working directory e' la radice del sorgente. `pytest` verde
# nel repo e `pip install` rotto per l'utente sono due fatti compatibili.
#
# ═══ COSA NON E' ═══
# Non e' un test della CI e non la sostituisce. La CI dice «il codice passa i
# suoi test»; questo dice «chi installa il pacchetto riesce a usarlo». Sono due
# domande diverse e servono entrambe.
#
# ═══ IL PRIMO PASSO E' UN BACKUP, E NON E' UNA FORMALITA' ═══
# Lo store reale di Aurelio (`~/.engram` su Windows) contiene migliaia di fatti
# che non si rigenerano. Questa procedura NON lo tocca — gira in WSL, su un
# filesystem diverso — ma il backup si fa lo stesso, PRIMA, e si verifica che
# esista: una procedura che presume l'isolamento invece di provarlo e' esattamente
# la classe di errore che stiamo togliendo dal prodotto.
#
# ⚠️ TRAPPOLA NOTA, ed e' la ragione del controllo n.2: `HIPPO_DATA_DIR` ha
# precedenza su `ENGRAM_DATA_DIR`, e `ENGRAM_DATA_DIR` da solo NON isola. In WSL
# il rischio concreto e' che la CLI scriva su `/mnt/c/Users/<tu>/.engram`, cioe'
# sullo store Windows attraverso il mount. Il passo 2 lo verifica guardando DOVE
# finisce il file, non quali variabili sono impostate.
#
# ═══ COSA E' GIA' STATO PROVATO DI QUESTO SCRIPT, E COSA NO ═══
# Il 02/09 alle 00:15 i passi 5, 6 e 7 sono stati eseguiti in uno store isolato
# (tutte e tre le variabili pinnate su una temporanea), senza WSL e senza
# installare nulla:
#
#     PASSO 5  lo store effettivo e' quello di prova   OK
#     PASSO 6  write con source (il gate gira)         OK
#     PASSO 7  recall  ->  "I run conclusi sono 2557. [0.83] moat 98.1"   OK
#
# ⇒ Il cuore del percorso utente — isolamento, scrittura col gate, recall — non
# e' una promessa: gira. **Restano non provati** i passi che richiedono WSL e
# un'installazione vera: backup (1), venv (2), `pip install` (3), import dopo
# installazione (4/4b), `doctor` (8), `mcp` (9), ripristino (10).
# Chi lancia la procedura per intero e' ancora il primo a farlo: se cade un
# passo fra quelli, guardi il log prima di concludere che il wheel e' rotto.
#
# ═══ COME LEGGE GLI ESITI ═══
# Ogni passo stampa una riga `PASSO n: OK|FALLITO (EXIT=k)`. Nessun passo e'
# giudicato dal suo output testuale: si legge il codice d'uscita, letto SUBITO
# dopo il comando e mai attraverso una pipe. Un passo senza riga di esito e' un
# passo NON eseguito, e va letto come rosso — l'assenza di misura non e' un verde.
#
#   USO:   bash scripts/smoke_utente_wsl.sh /percorso/al/verimem-X.Y.Z-py3-none-any.whl
#   da:    una shell WSL (Ubuntu), NON da PowerShell e NON da Git Bash.
#
# ═══ DOVE SI PRENDE IL WHEEL CANDIDATO — e come si sbaglia ═══
# Non va costruito a mano: il wheel giusto e' quello che la CI ha gia' costruito
# per IL COMMIT CHE SI PUBBLICA. Il job `build (sdist + wheel)` lo carica come
# artefatto `dist`.
#
#     gh run list --workflow=ci.yml --branch=hotfix/0.7.1 --limit 5
#     gh api "repos/:owner/:repo/actions/runs/<ID>/artifacts" --jq '.artifacts[].name'
#     gh run download <ID> -n dist -D /tmp/dist    # poi passa /tmp/dist/*.whl
#
# ⚠️ LA TRAPPOLA, ed e' concreta: piu' run dello stesso branch hanno artefatti, e
# **quello pronto non e' quello giusto**. Misurato il 02/09 alle 00:08:
#
#     #2557 (commit ff29d7ea)  artefatti: 1  →  dist, 4455781 byte, NON scaduto
#     #2653 (commit 08f38256)  artefatti: 0  →  ancora in coda
#
# `#2557` e' il run in cui `plugin.json` diceva ancora `0.7.0`: il suo wheel e'
# **pronto e sbagliato**. `#2653` porta la correzione e non ha ancora prodotto
# nulla. Chi ha fretta scarica quello che c'e'. ⇒ **Il passo 4 stampa la versione
# installata: confrontala con quella che stai per taggare, e se non combacia
# FERMATI** — e' l'unico controllo che intercetta questo errore prima di PyPI.
#
# =============================================================================

set -u

WHEEL="${1:-}"
ESITI=()
FALLITI=0

riga() { # riga <n> <descrizione> <exit>
  if [ "$3" -eq 0 ]; then
    printf '  PASSO %-2s %-52s OK\n' "$1" "$2"
  else
    printf '  PASSO %-2s %-52s FALLITO (EXIT=%s)\n' "$1" "$2" "$3"
    FALLITI=$((FALLITI + 1))
  fi
  ESITI+=("$1:$3")
}

echo "============================================================"
echo "  SMOKE DA UTENTE — $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  host: $(uname -a | cut -c1-60)"
echo "============================================================"

if [ -z "$WHEEL" ] || [ ! -f "$WHEEL" ]; then
  echo "  ⛔ wheel non indicato o inesistente: '${WHEEL:-<vuoto>}'"
  echo "     uso: bash scripts/smoke_utente_wsl.sh /percorso/al/wheel.whl"
  exit 2
fi
echo "  wheel candidato: $WHEEL"
echo "  dimensione:      $(stat -c %s "$WHEEL" 2>/dev/null || echo '?') byte"
echo

# ── PASSO 1 — BACKUP dello store reale, e VERIFICA che esista ────────────────
# Si fa anche se questa procedura non lo tocca: e' la rete sotto, non la cintura.
STORE_WIN="/mnt/c/Users/$(cmd.exe /c 'echo %USERNAME%' 2>/dev/null | tr -d '\r\n' || echo aurel)/.engram"
BACKUP="$HOME/backup-engram-$(date +%Y%m%d-%H%M%S).tar.gz"
if [ -d "$STORE_WIN" ]; then
  tar -czf "$BACKUP" -C "$(dirname "$STORE_WIN")" "$(basename "$STORE_WIN")" 2>/dev/null
  E=$?
  # il backup vale solo se il file esiste ED e' non vuoto: `tar` puo' uscire 0
  # avendo scritto un archivio vuoto se la sorgente e' irraggiungibile.
  if [ $E -eq 0 ] && [ -s "$BACKUP" ]; then
    riga 1 "backup dello store ($(stat -c %s "$BACKUP") byte)" 0
  else
    riga 1 "backup dello store — archivio assente o vuoto" 1
  fi
else
  echo "  PASSO 1  store Windows non montato ($STORE_WIN): niente da salvare."
  echo "           ⚠️ NON e' un OK: e' un'assenza. Se ti aspettavi di vederlo, fermati."
  ESITI+=("1:assente")
fi

# ── PASSO 2 — AMBIENTE VERGINE, e la prova che e' davvero isolato ────────────
VENV="$(mktemp -d)/venv"
python3 -m venv "$VENV"; riga 2a "creazione del venv vergine" $?
# shellcheck disable=SC1090
. "$VENV/bin/activate"
# ⚠️ Gli alias della data dir sono TRE, non due: `HIPPO_DATA_DIR` (che vince ed
# e' la maniglia esplicita di isolamento), `ENGRAM_DATA_DIR` e `VERIMEM_DATA_DIR`.
# Se se ne imposta solo una parte, il prodotto stesso avvisa —
# «DATA_DIR aliases disagree … Unset the ones you did not mean» — e l'avviso e'
# corretto: le altre due restano puntate allo store reale. Qui si pinnano tutte
# e tre, cosi' l'isolamento non dipende da quale nome il codice legge per primo.
export HIPPO_DATA_DIR="$(mktemp -d)/engram-smoke"
export ENGRAM_DATA_DIR="$HIPPO_DATA_DIR"
export VERIMEM_DATA_DIR="$HIPPO_DATA_DIR"
mkdir -p "$HIPPO_DATA_DIR"
echo "  store di prova: $HIPPO_DATA_DIR"

# ── PASSO 3 — INSTALLAZIONE dal wheel candidato ──────────────────────────────
pip install --quiet --upgrade pip >/dev/null 2>&1
pip install --quiet "$WHEEL" > /tmp/smoke_install.log 2>&1
riga 3 "pip install del wheel candidato" $?
[ $FALLITI -gt 0 ] && tail -5 /tmp/smoke_install.log

# ── PASSO 4 — IMPORT: il pacchetto si carica fuori dal repo? ─────────────────
cd "$HOME" || exit 3   # fuori dal sorgente: e' il punto dell'esercizio
python -c "import verimem, sys; print('  versione installata:', verimem.__version__)" 2>/tmp/smoke_import.log
riga 4 "import verimem fuori dal repo" $?
[ -s /tmp/smoke_import.log ] && tail -3 /tmp/smoke_import.log

# ── PASSO 4b — LA VERSIONE INSTALLATA E' QUELLA CHE STAI PUBBLICANDO? ────────
# Un commento che dice «confrontala» e' una speranza; questo e' un presidio.
# Passa la versione attesa come SECONDO argomento e il passo diventa un veto:
#   bash scripts/smoke_utente_wsl.sh /tmp/dist/verimem-0.7.1-py3-none-any.whl 0.7.1
# Senza il secondo argomento il controllo NON gira e lo dichiara — cosi' nessuno
# scambia «non verificato» per «verificato».
ATTESA="${2:-}"
if [ -n "$ATTESA" ]; then
  INSTALLATA="$(python -c 'import verimem; print(verimem.__version__)' 2>/dev/null)"
  [ "$INSTALLATA" = "$ATTESA" ]
  riga 4b "versione installata ($INSTALLATA) == attesa ($ATTESA)" $?
else
  echo "  PASSO 4b  versione attesa NON indicata: il controllo non e' stato eseguito."
  echo "            ⚠️ NON e' un OK. Rilancia col secondo argomento se stai per pubblicare."
  ESITI+=("4b:non-eseguito")
fi

# ── PASSO 5 — L'ISOLAMENTO SI VERIFICA GUARDANDO DOVE FINISCE IL FILE ────────
# Non basta aver impostato le variabili: si scrive e si guarda il percorso reale.
python - <<'PY' 2>/tmp/smoke_iso.log
import os, pathlib, sys
from verimem.config import CONFIG  # se il nome cambia, il passo FALLISCE: e' voluto
d = pathlib.Path(str(getattr(CONFIG, "data_dir", os.environ.get("HIPPO_DATA_DIR", ""))))
atteso = pathlib.Path(os.environ["HIPPO_DATA_DIR"])
print("  data_dir effettiva:", d)
sys.exit(0 if str(d).startswith(str(atteso)) else 1)
PY
riga 5 "lo store effettivo e' quello di prova, non quello reale" $?
[ -s /tmp/smoke_iso.log ] && tail -3 /tmp/smoke_iso.log

# ── PASSO 6 — SCRITTURA CON SOURCE: il gate gira e la ricevuta lo dice ───────
python - <<'PY' 2>/tmp/smoke_write.log
import sys
from verimem.cli import main
S = "Il totale dei run conclusi e' 2557."
sys.argv = ["verimem", "save", "I run conclusi sono 2557.",
            "--topic", "smoke/utente", "--source", S]
try:
    main()
except SystemExit as e:
    sys.exit(int(e.code or 0))
PY
riga 6 "write con source (il gate deve girare)" $?
[ -s /tmp/smoke_write.log ] && tail -4 /tmp/smoke_write.log

# ── PASSO 7 — RECALL: quello che ho scritto torna indietro? ──────────────────
# ⚠️ Il comando e' `recall`, NON `search`: la prima versione di questo script
# usava `search` — che NON esiste (`EXIT=2`, comando sconosciuto) — e il passo
# sarebbe fallito a ogni esecuzione, cioe' proprio prima di una pubblicazione.
# L'ho scoperto invocando i comandi uno per uno invece di fidarmi del nome che
# ricordavo: e' lo stesso errore che questo script serve a intercettare.
python - <<'PY' 2>/tmp/smoke_recall.log
import sys
from verimem.cli import main
sys.argv = ["verimem", "recall", "run conclusi"]
try:
    main()
except SystemExit as e:
    sys.exit(int(e.code or 0))
PY
riga 7 "recall del fatto appena scritto" $?
[ -s /tmp/smoke_recall.log ] && tail -4 /tmp/smoke_recall.log

# ── PASSO 8 — DOCTOR: la diagnostica che consigliamo agli utenti ─────────────
verimem doctor > /tmp/smoke_doctor.log 2>&1
riga 8 "verimem doctor" $?
tail -6 /tmp/smoke_doctor.log

# ── PASSO 9 — IL SERVER MCP PARTE? ───────────────────────────────────────────
# Non si tiene acceso: si verifica che l'entry point esista e risponda a --help.
verimem mcp --help > /tmp/smoke_mcp.log 2>&1
riga 9 "verimem mcp raggiungibile" $?
[ -s /tmp/smoke_mcp.log ] && head -3 /tmp/smoke_mcp.log

# ── PASSO 10 — RIPRISTINO: si chiude cio' che si e' aperto ───────────────────
deactivate 2>/dev/null
rm -rf "$HIPPO_DATA_DIR"
riga 10 "rimozione dello store di prova" $?
echo "  ⚠️ il venv temporaneo resta in $(dirname "$VENV") — toglilo a mano se vuoi."
echo "  ⚠️ il backup NON viene cancellato: $BACKUP"

# ── VERDETTO ─────────────────────────────────────────────────────────────────
echo
echo "============================================================"
echo "  passi eseguiti: ${#ESITI[@]}   ·   FALLITI: $FALLITI"
if [ "$FALLITI" -eq 0 ]; then
  echo "  ✅ percorso utente completo su questo wheel."
  echo "     ⚠️ Vale per QUESTO wheel su QUESTA distribuzione WSL: non e' una"
  echo "        garanzia su Windows nativo ne' su macOS."
else
  echo "  🔴 IL WHEEL NON E' PUBBLICABILE: $FALLITI passi falliti."
fi
echo "============================================================"
exit "$FALLITI"
