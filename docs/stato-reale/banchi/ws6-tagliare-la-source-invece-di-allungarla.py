"""Verifica indipendente della cura di @ws2 su un caso MIO gia' caduto.

@ws4 (W7-102) misura che 72 fatti hanno TUTTI i numeri nella fonte e il moat li
boccia comunque - il 30,4% dei quarantinati con numeri - e attribuisce la causa
alle fonti che confrontano piu' valori della stessa grandezza. @ws2 propone la
cura: "taglia la source alla riga che sostiene il claim".

Io ho un caso adatto: stanotte un mio fatto e' caduto a grounding 2,55 con la
source INTERA (una tabella a tre righe) ed e' passato a 99,97 quando ho AGGIUNTO
una riga che enunciava il legame. Ho curato ALLUNGANDO; ws2 dice di TAGLIARE.

Tre bracci sullo stesso claim, stesso store temporaneo:
  A  source INTERA (la tabella)                                -> atteso: cade
  B  INTERA + riga che LEGA (la mia cura)                      -> atteso: passa
  C  TAGLIATA alla sola riga che sostiene (la cura di ws2)     -> ?

⚠️ PRIMA VERSIONE SBAGLIATA, e la lascio scritta: usava `Memory.add()`. Tutti e
tre i bracci passavano con `grounding_score` a None - cioe' IL MOAT NON GIRAVA
AFFATTO, e il banco misurava una porta che non fa il controllo che volevo
misurare. "Il livello a cui misuri decide il verdetto": qui la porta giusta e'
quella che uso davvero per salvare, `verimem save` via `verimem.cli.main`.

⚠️ Store TEMPORANEO: HIPPO_DATA_DIR prima degli import.
"""
import io
import os
import re
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="ws6_taglio_")
os.environ["HIPPO_DATA_DIR"] = _tmp
for _v in ("ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
    os.environ.pop(_v, None)

CLAIM = ("Interrogando con domande in italiano i 16 fatti scritti in inglese se "
         "ne ritrovano 8, con sovrapposizione lessicale 2.7 per cento.")

TABELLA = (
    "Il banco stampa: fatti INGLESI nel banco: 16; domanda in INGLESE (la "
    "lingua del fatto) n=16 trovati 9 = 56.2% primi 9 = 56.2% sovr 89.4%; la "
    "STESSA domanda in ITALIANO n=16 trovati 8 = 50.0% primi 6 = 37.5% sovr "
    "2.7%; in INGLESE col NOME PROPRIO (controllo) n=16 trovati 9 = 56.2% "
    "primi 9 = 56.2% sovr 90.7%. La colonna sovr misura quante parole della "
    "domanda compaiono nel fatto interrogato."
)
LEGAME = (
    " I 16 fatti interrogati dal banco sono scritti in inglese, e la riga della "
    "STESSA domanda in ITALIANO riporta i risultati ottenuti interrogando quei "
    "16 fatti inglesi con domande in italiano: 8 fatti ritrovati e "
    "sovrapposizione 2.7 per cento."
)
TAGLIATA = (
    "Il banco stampa: fatti INGLESI nel banco: 16; la STESSA domanda in "
    "ITALIANO n=16 trovati 8 = 50.0% sovr 2.7%."
)

BRACCI = [
    ("A  source INTERA (la tabella a tre righe)", TABELLA),
    ("B  INTERA + riga che LEGA (la mia cura)", TABELLA + LEGAME),
    ("C  TAGLIATA alla riga che sostiene (ws2)", TAGLIATA),
]

from verimem.cli import main   # noqa: E402 - dopo HIPPO_DATA_DIR

print("store temporaneo: %s\n" % _tmp)
esiti = []
for i, (eti, src) in enumerate(BRACCI):
    buf = io.StringIO()
    vero_out, vero_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = buf
    sys.argv = ["verimem", "save", CLAIM,
                "--topic", "banco/taglio-source-%d" % i, "--source", src]
    try:
        main()
    except SystemExit:
        pass
    except Exception as e:                     # noqa: BLE001
        buf.write("ERRORE %s" % e)
    finally:
        sys.stdout, sys.stderr = vero_out, vero_err
    testo = buf.getvalue()
    stato = "QUARANTINATO" if "quarantined id=" in testo else (
        "ammesso" if "admitted id=" in testo else "?")
    mg = re.search(r"grounding_score=([0-9.]+)", testo)
    esiti.append((eti, stato, mg.group(1) if mg else None, len(src)))

print("%-44s %-14s %11s %s" % ("braccio", "esito", "grounding", "len(source)"))
for eti, stato, g, ln in esiti:
    print("%-44s %-14s %11s %d"
          % (eti, stato, ("%.2f" % float(g)) if g else "NON GIUDICATO", ln))

print("\nSe C e' ammesso: la cura di @ws2 regge su un caso indipendente dal suo,")
print("e costa MENO della mia (togliere invece di aggiungere).")
print("Se C cade e B passa: le due cure NON sono intercambiabili - serve")
print("ENUNCIARE il legame, non solo isolare la riga.")
print("Se il grounding e' NON GIUDICATO: il moat non ha girato e il banco non")
print("misura quello che dice - non concludere nulla.")
