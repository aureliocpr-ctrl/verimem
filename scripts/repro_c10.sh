#!/usr/bin/env bash
# ============================================================================
# REPRO-C10 — un estraneo rifà il nostro numero di copertina, con UN comando.
#
#   bash scripts/repro_c10.sh
#
# Il numero: «di cio' che viene SERVITO, e' falso il 15,9% (40/252) contro il
# 50,0% dello stesso corpus senza gate» (REPORT-30-08, righe 29-31).
#
# ═══ PERCHE' ESISTE ═══
# Un numero di copertina che nessun estraneo puo' rifare e' una dichiarazione,
# non una misura. Questo script esiste per rendere FALSIFICABILE quella riga:
# se il numero non regge, deve rompersi QUI, sulla macchina di chi dubita.
#
# ═══ COSA NON FA, DETTO SUBITO ═══
# ① NON gira in 5 minuti da un ambiente vergine. Il gate usa un cross-encoder
#    LOCALE da ~746 MB che non sta nel repo. Il tempo vero e':
#         download del modello (746 MB, dipende dalla banda)  +  esecuzione.
#    Chi ha gia' il modello parte dal secondo addendo. Lo script MISURA e
#    STAMPA i due tempi separati, perche' un tempo unico nasconde quale dei
#    due comanda.
# ② NON misura mem0. Il confronto col concorrente sta in c10_lato_mem0.py e
#    richiede un interprete separato (.venv-mem0bench): e' un altro pacchetto,
#    e mescolarlo qui renderebbe questo script non riproducibile.
# ③ NON prova che il gate sia buono. Produce DUE facce (falsi ammessi, veri
#    persi) e vanno lette insieme: un gate che rifiuta tutto ha la prima
#    perfetta e la seconda catastrofica.
#
# ═══ L'ESITO SI LEGGE DAL CODICE D'USCITA, MAI DA UNA PIPE ═══
#   0  il numero rifatto cade nella tolleranza dichiarata
#   3  il numero DIVERGE  → e' il caso interessante: la riga pubblicata non regge
#   2  prerequisito mancante (modello, dataset, python) → NON e' un verdetto
# ============================================================================
set -u

# La radice si deduce dalla posizione dello script, ma resta SOVRASCRIVIBILE:
# senza questo, una copia dello script fuori dal repo cerca il dataset accanto
# a se' e si ferma al PASSO 1 — cioe' il presidio non e' falsificabile, perche'
# ogni tentativo di provarlo con un valore atteso sbagliato muore prima di
# arrivare al confronto. Trovato provando a falsificarlo, non ragionandoci.
RADICE="${REPRO_C10_RADICE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$RADICE" || exit 2

DATASET="benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
MODELLI="${HOME}/.engram/models"
ATTESO_SERVITO=15.9      # % di falsita' fra i SERVITI (REPORT-30-08)
TOLLERANZA=3.0           # punti percentuali; vedi NOTA SULLA TOLLERANZA in fondo
USCITA="benchmark/results/c10_lato_verimem.json"

riga() { printf '  %-9s %-58s %s\n' "$1" "$2" "$3"; }

echo "============================================================================"
echo "  REPRO-C10 — rifare il numero di copertina di verimem"
echo "  $(date '+%F %H:%M %Z')   ·   $(git log -1 --format=%h 2>/dev/null || echo 'no-git')"
echo "============================================================================"

# --- PASSO 1  il dataset e' nel repo: nessun download, nessuna rete ----------
if [ -f "$DATASET" ]; then
  RIGHE=$(wc -l < "$DATASET")
  riga "PASSO 1" "dataset presente nel repo ($RIGHE righe)" "OK"
else
  riga "PASSO 1" "dataset ASSENTE: $DATASET" "FERMO"
  echo "  ⛔ prerequisito mancante. NON e' un verdetto sul numero."; exit 2
fi

# --- PASSO 2  il modello: il vero costo, dichiarato prima di pagarlo ---------
if [ -d "$MODELLI/local_gate_ce" ] || [ -d "$MODELLI/local_gate_ce_v2" ]; then
  PESO=$(du -sh "$MODELLI" 2>/dev/null | cut -f1)
  riga "PASSO 2" "cross-encoder gia' presente ($PESO in $MODELLI)" "OK"
  T_DOWNLOAD=0
else
  riga "PASSO 2" "cross-encoder ASSENTE — servono ~746 MB" "FERMO"
  echo "  Il gate senza giudice locale NON produce questo numero: si fermerebbe"
  echo "  a un verdetto lessicale, che e' una misura DIVERSA. Scaricalo con:"
  echo "      verimem doctor --download-model      # ~746 MB, una volta sola"
  echo "  poi rilancia questo script. (Il tempo di download NON e' incluso nei"
  echo "  numeri qui sotto: e' l'addendo che domina su una banda lenta.)"
  exit 2
fi

# --- PASSO 3  l'esecuzione, cronometrata ------------------------------------
# `--secco` salta l'esecuzione e verifica la CATENA (dataset → artefatto →
# confronto) su un artefatto gia' presente. Serve a due cose oneste: provare
# questo script senza spendere 746 MB, e permettere a chi dubita di vedere
# COME il numero viene letto prima di decidere se rifarlo davvero.
# ⚠️ NON e' una riproduzione: non rimisura nulla. Lo dice, e cambia il verdetto
#    in una parola diversa, perche' «verificato» e «riletto» non sono sinonimi.
SECCO=0
[ "${1:-}" = "--secco" ] && SECCO=1

echo
if [ "$SECCO" = "1" ]; then
  if [ ! -f "$USCITA" ]; then
    riga "PASSO 3" "--secco richiede un artefatto gia' presente: $USCITA" "FERMO"; exit 2
  fi
  QUANDO=$(date -r "$USCITA" '+%F %H:%M' 2>/dev/null || echo "data ignota")
  riga "PASSO 3" "SALTATO (--secco): rileggo l'artefatto del $QUANDO" "NON RIMISURATO"
  T_ESEC=0
else
  riga "PASSO 3" "eseguo il banco su tutte le $RIGHE righe (nessun campionamento)" "..."
  T0=$(date +%s)
  python benchmark/c10_falsita_servite_vs_mem0.py --popolazione truthfulqa --out "$USCITA"
  EXIT_BANCO=$?
  T1=$(date +%s)
  T_ESEC=$((T1 - T0))
  riga "PASSO 3" "banco concluso in ${T_ESEC}s" "EXIT=$EXIT_BANCO"
  if [ "$EXIT_BANCO" -ne 0 ]; then
    echo "  ⛔ il banco e' uscito con $EXIT_BANCO: nessun numero da confrontare."; exit 2
  fi
fi

# --- PASSO 4  il confronto con l'atteso: qui il numero si rompe o regge ------
echo
OTTENUTO=$(python -c "
import json,sys
d=json.load(open(r'$USCITA', encoding='utf-8'))
s=d.get('serviti') or 0
f=d.get('falsi_fra_i_serviti') or 0
print(f'{100*f/s:.1f}' if s else 'NA')
" 2>/dev/null)

if [ "$OTTENUTO" = "NA" ] || [ -z "$OTTENUTO" ]; then
  riga "PASSO 4" "non ho potuto leggere il numero da $USCITA" "FERMO"; exit 2
fi

DELTA=$(python -c "print(f'{abs($OTTENUTO - $ATTESO_SERVITO):.1f}')")
echo "  ─────────────────────────────────────────────────────────────────────"
echo "    atteso (REPORT-30-08) : ${ATTESO_SERVITO}%   di falsita' fra i SERVITI"
echo "    ottenuto qui          : ${OTTENUTO}%"
echo "    scarto                : ${DELTA} punti   (tolleranza ${TOLLERANZA})"
echo "    tempo esecuzione      : ${T_ESEC}s        (download: ${T_DOWNLOAD}s)"
echo "  ─────────────────────────────────────────────────────────────────────"

VERDETTO=$(python -c "print('DENTRO' if $DELTA <= $TOLLERANZA else 'FUORI')")
if [ "$SECCO" = "1" ] && [ "$VERDETTO" = "DENTRO" ]; then
  echo "  ⚠️ CATENA VERIFICATA, NUMERO NON RIMISURATO (--secco): l'artefatto sul"
  echo "     disco dice ${OTTENUTO}% e la riga pubblicata dice ${ATTESO_SERVITO}%. Questo prova"
  echo "     che la vetrina cita il suo artefatto, NON che l'artefatto sia giusto."
  echo "     Per la riproduzione vera togli --secco: il banco rigira le $RIGHE righe."
  exit 0
fi
if [ "$VERDETTO" = "DENTRO" ]; then
  echo "  ✔ il numero pubblicato REGGE su questa macchina."
  echo
  echo "  ⚠️ E ora la parte che conta, che il solo 15,9% non dice: il confronto"
  echo "     col 50,0% ha DUE BASI DIVERSE — 15,9% e' su cio' che il gate SERVE,"
  echo "     50,0% su TUTTO il corpus. Il banco stampa entrambe le basi qui sopra:"
  echo "     leggile, e leggi le DUE FACCE (falsi ammessi / veri persi). Un tasso"
  echo "     solo, staccato dalla sua base e dalla sua faccia, e' marketing."
  exit 0
else
  echo "  🔴 il numero pubblicato NON regge qui: scarto ${DELTA} punti."
  echo "     Questo e' il caso interessante, non un errore dello script."
  echo "     Prima di concludere, guarda: stessa popolazione? stesso commit?"
  echo "     stesso modello (local_gate_ce vs _v2)? Sono le tre variabili che"
  echo "     spostano il numero senza che nessuno lo dichiari."
  exit 3
fi

# ═══ NOTA SULLA TOLLERANZA — perche' 3.0 e non 0 ═══
# Il banco stesso avverte: «con n per faccia non si distingue nulla sotto ~N
# punti». La tolleranza NON e' indulgenza verso di noi: e' la larghezza sotto
# la quale due giri NON differiscono, e pretendere l'uguaglianza esatta
# farebbe fallire lo script su rumore. Se qualcuno stringe questa costante,
# stringa prima l'intervallo di confidenza che il banco stampa.
