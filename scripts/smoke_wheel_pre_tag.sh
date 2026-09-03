#!/usr/bin/env bash
# ============================================================================
# SMOKE PRE-TAG — Windows, da utente vero, sul WHEEL CANDIDATO della CI.
#
#   bash smoke_wheel_windows.sh <run-id> [versione-attesa]
#
# ═══ PERCHE' SUL WHEEL DELLA CI E NON SU UNO COSTRUITO QUI ═══
# Il pacchetto che l'utente installa e' quello che la CI ha prodotto e che il
# publish caricherebbe. Un wheel costruito a mano sulla macchina di chi verifica
# prova che il codice si impacchetta, non che l'artefatto candidato funzioni: il
# 2026-09-02 il veto sul registro fu rifatto proprio per questo sull'artefatto
# `dist` della CI invece che su uno locale.
#
# ═══ COSA CONTROLLA, E PERCHE' QUESTE COSE ═══
# I passi 1-6 sono «parte e dice la verita' su di se'». I passi 7-9 sono LE
# CURE della release: uno smoke che si ferma a «l'import riesce» avrebbe dato
# verde anche il 2026-09-02, quando la porta ammetteva senza giudicare.
#   7  una scrittura CON FONTE viene giudicata      -> `layers` NON vuoti
#   8  un claim che la fonte smentisce viene FERMATO
#   9  il server dichiara la PROPRIA versione, non quella della libreria mcp
#
# ═══ COSA NON PROVA ═══
# Un solo sistema operativo (questo e' il braccio Windows; WSL e' l'altro, e i
# due sono serviti a scoprire che lo stesso pacchetto dava moat MISSING su uno
# e moat ON sull'altro). Non prova la porta MCP sotto un client reale: prova che
# risponde all'handshake. Non prova nulla sulla velocita'.
#
# ═══ L'ESITO SI LEGGE DAL CODICE D'USCITA, MAI DA UNA PIPE ═══
#   0  tutti i passi passati        1  almeno un passo fallito
#   2  prerequisito mancante (artefatto, rete, python) -> NON e' un verdetto
# ============================================================================
set -u

# ═══ DUE MODI DI AVERE IL WHEEL, PERCHE' I DUE CAMPI SONO DIVERSI ═══
#   bash smoke_wheel_pre_tag.sh <run-id> [versione]        <- scarica con gh
#   bash smoke_wheel_pre_tag.sh --wheel <path> [versione]  <- usa un file gia' qui
# In WSL `gh` non c'e' (verificato da lead-audit: `command -v gh` vuoto), e un
# secondo script per l'altro campo sarebbe un DOPPIONE: due copie divergono, e
# allora i due bracci non misurerebbero piu' la stessa cosa — che e' esattamente
# il punto di averne due.
RUN_ID=""
WHEEL_DATO=""
ATTESA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --wheel) WHEEL_DATO="${2:-}"; shift 2 ;;
    --wheel=*) WHEEL_DATO="${1#--wheel=}"; shift ;;
    *) if [ -z "$RUN_ID" ] && [ -z "$WHEEL_DATO" ]; then RUN_ID="$1"
       else ATTESA="$1"; fi; shift ;;
  esac
done
# con --wheel il primo argomento libero e' la versione, non il run-id
[ -n "$WHEEL_DATO" ] && [ -z "$ATTESA" ] && [ -n "$RUN_ID" ] && { ATTESA="$RUN_ID"; RUN_ID=""; }

if [ -z "$RUN_ID" ] && [ -z "$WHEEL_DATO" ]; then
  echo "  uso: bash smoke_wheel_pre_tag.sh <run-id> [versione]"
  echo "       bash smoke_wheel_pre_tag.sh --wheel <path/al/file.whl> [versione]"
  exit 2
fi
if [ -n "$WHEEL_DATO" ] && [ ! -f "$WHEEL_DATO" ]; then
  echo "  ⛔ il wheel indicato non esiste: $WHEEL_DATO"
  echo "     NON e' un verdetto sul pacchetto."; exit 2
fi
# Il path va reso ASSOLUTO ORA: fra due righe si va in una temporanea e un path
# relativo punterebbe altrove — un file che «sparisce» dopo il cd.
[ -n "$WHEEL_DATO" ] && WHEEL_DATO="$(cd "$(dirname "$WHEEL_DATO")" && pwd)/$(basename "$WHEEL_DATO")"

# Il repository va risolto ORA, finche' siamo ancora dentro il repo: subito sotto
# si va in una temporanea, e li' `gh` non sa piu' quale repo interrogare — il
# download fallisce con «no such file or directory» sulla cartella degli
# artefatti, che sembra un problema di artefatti e invece e' di contesto.
# Trovato alla prova generale, che serve a questo.
# Il suffisso `.git` va tolto con una sostituzione SUA: dentro un solo regex il
# gruppo se lo mangia e REPO diventa «owner/nome.git», che l'API rifiuta con un
# 404 sugli ARTEFATTI — un errore che sembra «non ci sono artefatti» e invece e'
# un nome di repository sbagliato. Due sostituzioni, non una furba.
# Serve solo quando si scarica: con --wheel il file c'e' gia', e pretendere il
# repository escluderebbe proprio il campo per cui --wheel esiste (WSL, dove non
# c'e' `gh` e lo script puo' girare fuori dal clone).
REPO=""
if [ -z "$WHEEL_DATO" ]; then
  REPO="$(git remote get-url origin 2>/dev/null | sed -E 's#^.*[:/]([^/]+/[^/]+)$#\1#; s#\.git$##')"
  [ -z "$REPO" ] && { echo "  ⛔ non riesco a risolvere il repository: lancia dal repo, o usa --wheel."; exit 2; }
  echo "  repository: $REPO"
fi

BASE="$(mktemp -d)/smoke-wheel"
STORE="$BASE/store"          # store ISOLATO: mai ~/.engram di Aurelio
mkdir -p "$BASE" "$STORE" || exit 2
cd "$BASE" || exit 2

# I TRE alias della data dir: uno solo non basta (misurato il 02/09).
export HIPPO_DATA_DIR="$STORE" ENGRAM_DATA_DIR="$STORE" VERIMEM_DATA_DIR="$STORE"

FALLITI=0
riga() {  # riga <n> <cosa> <exit>
  printf '  PASSO %-3s %-52s EXIT=%s\n' "$1" "$2" "$3"
  [ "$3" -ne 0 ] && FALLITI=$((FALLITI + 1))
  return 0
}

echo "============================================================================"
echo "  SMOKE PRE-TAG · Windows · wheel del run $RUN_ID"
echo "  $(date '+%F %H:%M %Z')"
echo "  store isolato: $STORE   (lo store di Aurelio NON e' toccato)"
echo "============================================================================"

# --- 1  il wheel CANDIDATO: scaricato dalla CI, oppure dato da fuori --------
if [ -n "$WHEEL_DATO" ]; then
  WHEEL="$WHEEL_DATO"
  riga 1 "wheel fornito da fuori (nessun download)" 0
  echo "         ⚠️ chi lancia cosi' garantisce la PROVENIENZA del file: questo"
  echo "            script non puo' sapere da quale run venga. Scrivilo nel registro."
else
  gh run download "$RUN_ID" -R "$REPO" --dir art 2>&1 | tail -2
  riga 1 "artefatto del run scaricato" $?
  WHEEL="$(find art -name 'verimem-*.whl' | head -1)"
  if [ -z "$WHEEL" ]; then
    echo "  ⛔ nessun .whl nell'artefatto: NON e' un verdetto sul pacchetto."; exit 2
  fi
fi
echo "         wheel: $(basename "$WHEEL")"
# L'impronta del file: e' l'unico modo perche' i DUE bracci possano dire di aver
# provato LO STESSO artefatto. Senza, «windows OK» e «wsl OK» potrebbero essere
# due wheel diversi e nessuno se ne accorgerebbe.
SHA256="$( { sha256sum "$WHEEL" 2>/dev/null || shasum -a 256 "$WHEEL" 2>/dev/null; } | cut -d' ' -f1)"
echo "         sha256: ${SHA256:-non calcolabile su questo sistema}"

# --- 2  venv vergine, fuori dal repo ---------------------------------------
python -m venv .venv; riga 2 "venv vergine" $?
PY=".venv/Scripts/python.exe"; [ -f "$PY" ] || PY=".venv/bin/python"
[ -f "$PY" ] || { echo "  ⛔ interprete non trovato"; exit 2; }

# --- 3  installazione DAL WHEEL, non da PyPI -------------------------------
T0=$(date +%s)
"$PY" -m pip install --quiet "$WHEEL"
EX=$?; T1=$(date +%s)
riga 3 "pip install <wheel candidato>  ($((T1 - T0))s)" $EX
[ "$EX" -ne 0 ] && { echo "  ⛔ installazione fallita: i passi seguenti non hanno senso."; exit 2; }

# --- 4  dice la verita' su di se' ------------------------------------------
# ⚠️ PRIMA della versione: da DOVE viene il pacchetto che stiamo per misurare.
# Se `import verimem` risolve al SORGENTE DEL REPO invece che al venv, tutti i
# passi seguenti misurano il codice di lavoro e non il wheel candidato — e lo
# smoke darebbe VERDE su un artefatto mai provato. Qui si fa `cd` in una
# temporanea apposta, ma quella e' una protezione IMPLICITA: basta che qualcuno
# lanci lo script da dentro il repo perche' salti, e nessuno se ne accorgerebbe.
# (Misurato: con cwd nel repo, `import verimem` risolve a
#  C:\Users\aurel\Code\HippoAgent\verimem\__init__.py.)
ORIGINE="$("$PY" -c 'import verimem, pathlib; print(pathlib.Path(verimem.__file__).resolve())' 2>&1)"
echo "         origine: $ORIGINE"
case "$ORIGINE" in
  *"$BASE"*|*site-packages*) EX_ORIG=0 ;;
  *)                         EX_ORIG=1 ;;
esac
riga 3b "il pacchetto importato viene DAL VENV, non dal repo" $EX_ORIG
[ "$EX_ORIG" -ne 0 ] && { echo "  ⛔ stiamo per misurare il SORGENTE, non il wheel: mi fermo."; exit 2; }

V="$("$PY" -c 'import verimem; print(verimem.__version__)' 2>&1)"; riga 4 "import verimem -> $V" $?
if [ -n "$ATTESA" ]; then
  [ "$V" = "$ATTESA" ]; riga 4b "versione installata == attesa ($ATTESA)" $?
else
  echo "  PASSO 4b  versione attesa NON indicata: controllo non eseguito."
fi

# --- 5  il tetto sulla dipendenza che ci ha rotti una volta ----------------
"$PY" -c "
import sys
from importlib.metadata import version
v = version('mcp'); print('         mcp =', v)
sys.exit(0 if int(v.split('.')[0]) < 2 else 1)"
riga 5 "il tetto mcp<2 regge sul servito" $?

# --- 6  la CLI risponde -----------------------------------------------------
"$PY" -m verimem.cli --help > /dev/null 2>&1; riga 6 "verimem --help" $?

# ============ LE CURE DELLA RELEASE — qui uno smoke pigro darebbe verde ====
# --- 7  una scrittura CON FONTE viene giudicata ----------------------------
"$PY" - <<'PYEOF' > /tmp/smoke7.txt 2>&1
import sys
from verimem import open_memory
m = open_memory()
r = m.add("Il banco ha girato su duecento casi.",
          topic="smoke/giudicata",
          source="Il banco ha girato su duecento casi.")
layers = r.get("anti_confab_warnings") or []
gs = r.get("grounding_score")
print(f"         status={r.get('status')} grounding_score={gs} layers={len(layers)}")
# La cura: una fonte data DEVE far girare il giudice -> un punteggio esiste.
sys.exit(0 if gs is not None else 1)
PYEOF
EX=$?; grep -m1 'status=' /tmp/smoke7.txt
riga 7 "una fonte data VIENE GIUDICATA (grounding_score non nullo)" $EX

# --- 8  un claim che la fonte smentisce viene FERMATO ----------------------
"$PY" - <<'PYEOF' > /tmp/smoke8.txt 2>&1
import sys
from verimem import open_memory
m = open_memory()
r = m.add("Il numero di serie del dispositivo e 99999.",
          topic="smoke/falso",
          source="Oggi a Milano il cielo e sereno e la temperatura e di 21 gradi.")
st = r.get("status")
print(f"         status={st} grounding_score={r.get('grounding_score')}")
# Fermato = quarantined (o comunque NON servito come verita').
sys.exit(0 if st == "quarantined" else 1)
PYEOF
EX=$?; grep -m1 'status=' /tmp/smoke8.txt
riga 8 "un claim smentito dalla fonte viene FERMATO" $EX

# --- 9  il server dichiara la PROPRIA versione -----------------------------
"$PY" - <<'PYEOF' > /tmp/smoke9.txt 2>&1
import sys
from importlib.metadata import version
import verimem
from verimem.mcp_server import server
sv = getattr(server, "version", None)
print(f"         server.version={sv}  verimem={verimem.__version__}  mcp={version('mcp')}")
sys.exit(0 if sv == verimem.__version__ else 1)
PYEOF
EX=$?; grep -m1 'server.version' /tmp/smoke9.txt
riga 9 "serverInfo dichiara la versione di verimem, non di mcp" $EX

echo
if [ "$FALLITI" -eq 0 ]; then
  # Il campo si RILEVA, non si presume: questo script gira su due sistemi e un
  # registro che dichiara «windows» mentre e' girato su Linux e' falso — e il
  # cancello cerca proprio quella parola.
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) CAMPO="windows"; ALTRO="wsl" ;;
    Linux*)               CAMPO="wsl (o linux)"; ALTRO="windows" ;;
    *)                    CAMPO="$(uname -s 2>/dev/null || echo ignoto)"; ALTRO="l'altro" ;;
  esac
  echo "  OK  tutti i passi passati sul braccio: $CAMPO"
  echo "      Il verdetto del tag richiede anche $ALTRO, sullo STESSO wheel:"
  echo "      confrontate lo sha256 stampato sopra, non il nome del file."
  echo "      I due bracci esistono perche' il 2026-09-02 lo stesso pacchetto"
  echo "      dava moat MISSING su uno e moat ON sull'altro."
  exit 0
fi
echo "  KO  $FALLITI passi falliti: vedi le righe con EXIT diverso da 0."
exit 1
