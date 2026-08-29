r"""I quattro verbali veri caduti si salvano con la cura che il prodotto gia' ha?

Segue `ws5-quale-parola-fa-cadere-un-verbale-vero.py`, dove a variabile singola
**4 claim VERI su 10 cadono cambiando un verbo** (`completato`, `approvato`,
`validato`, `verificato`) e sulla stessa fonte **un falso passa** (`sospeso`,
98.64). Diagnosi: **il presidio anti-autocertificazione legge il verbo, non chi
parla** - e qui a parlare e' una commissione, non l'agente.

⇒ LA DOMANDA: la porta ha gia' i campi per dire **chi parla**
(`writer_role`, `provenance_trusted`, `claimant`). **Bastano?**

I CINQUE REGIMI, sugli stessi identici claim:
    base                                          (come il banco precedente)
    writer_role='external_content'                (il valore che la RICEVUTA consiglia)
    provenance_trusted=True
    writer_role + provenance_trusted              (la coppia intera)
    claimant='la commissione di collaudo'         (dire chi ha attestato)

⚠️⚠️ **I FALSI VIAGGIANO IN OGNI REGIME, E SONO IL CUORE DEL BANCO.** Una cura
che salva i veri **facendo passare anche i falsi** non e' una cura: e' un
interruttore che spegne il gate. ⇒ Un regime vale solo se **alza i veri salvi
SENZA alzare i falsi passati**, e le due colonne stanno una accanto all'altra.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: una fonte sola; 4 veri + 3 falsi; misuro `run_validation_gate`
direttamente - **sull'SDK il `Client` aggiunge campi propri** (`client.py:539`
passa `provenance_trusted`) e **su MCP `external_content` e' RIFIUTATO dallo
schema**, quindi un regime verde qui **non e' detto sia raggiungibile da tutte
le porte**.

ESITO - **la cura esiste, funziona, non spegne il gate. Ma serve LA COPPIA, e
la ricevuta ne consiglia META'**::

    regime                         VERI salvi   FALSI fermati  layer che restano
    base                           0/4          2/3            L1.15 x2, L1.13 x1, L4-relazione x1, L1.16 x1
    writer_role=external_content   0/4          2/3            (identici al base)
    provenance_trusted=True        0/4          2/3            (identici al base)
    writer_role + provenance       4/4          2/3            -
    claimant=la commissione        0/4          2/3            (identici al base)

🟢 **LA CURA C'E' ED E' PULITA**: `writer_role='external_content'` **insieme a**
`provenance_trusted=True` salva **4 verbali veri su 4** e **non tocca i falsi**
(2/3 fermati in tutti e cinque i regimi, identico al base). ⇒ Non e' un
interruttore che spegne il gate: e' un instradamento di provenienza che toglie
il presidio anti-autocertificazione **dove il soggetto non e' l'agente**.

🔴 **MA NESSUNO DEI DUE CAMPI, DA SOLO, FA QUALCOSA: 0/4 e 0/4.** I layer che
restano sono **gli stessi identici del base**. ⇒ **La cura e' la coppia**, e
questo ha una conseguenza sgradevole: **la ricevuta consiglia
`writer_role='external_content'` - meta' della cura.** Chi segue l'advice alla
lettera su questa porta ottiene **zero**: stessi quattro veri caduti, stessi
layer.
📌 Da' il numero al mio reperto del 28/08 («*l'advice della ricevuta e' corretto
ma insufficiente*», `b562fc21`): **insufficiente vuol dire 0 su 4.** Sull'SDK
funziona perche' il `Client` aggiunge `provenance_trusted` per conto suo
(`client.py:539`) - **la meta' che l'advice non nomina**. Su **MCP** il valore
`external_content` e' **rifiutato dallo schema**, e `provenance_trusted` non
arriva mai: li' la cura non e' ottenibile ne' intera ne' a meta'.

🔴 **E `claimant` NON E' COLLEGATO: 0/4.** Il campo per dire **chi ha attestato**
esiste nella firma della porta, lo passo con «*la commissione di collaudo*», e i
layer restano **identici al base**. ⇒ Stessa classe del difetto [C] che ho
chiuso ieri: **il presidio esiste e non e' collegato a cio' che dovrebbe
decidere.** Qui il gate ha in mano il dato che gli serve - il soggetto e' un
terzo - e non lo usa.

⚖️ **LIMITE CHE NON POSSO TOGLIERE DA QUI**: il regime verde e' misurato su
`run_validation_gate`. **Verde qui non vuol dire raggiungibile da tutte le
porte.**

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ ALTRI PUNTI DEBOLI: una fonte sola; 4 veri + 3 falsi; `sospeso` passa in
**tutti** i regimi (era gia' cosi' nel base: la cura non lo peggiora e non lo
cura).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-cura-che-esiste-salva-i-quattro-verbi.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

FONTE = ("Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo "
         "e la linea e' stata approvata dalla commissione.")
CLAIM = "Il collaudo della linea 3 e' stato %s il 12 marzo."

CADUTI = ["completato", "approvato", "validato", "verificato"]   # VERI, caduti nel base
FALSI = ["respinto", "rinviato", "sospeso"]                      # la fonte li contraddice

REGIMI = [
    ("base", {}),
    ("writer_role=external_content", {"writer_role": "external_content"}),
    ("provenance_trusted=True", {"provenance_trusted": True}),
    ("writer_role + provenance", {"writer_role": "external_content",
                                  "provenance_trusted": True}),
    ("claimant=la commissione", {"claimant": "la commissione di collaudo"}),
]


def _gate(claim, extra):
    try:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=FONTE, grounding_llm=None,
                                ground_write=True, **extra)
    except Exception as e:  # noqa: BLE001 - il banco deve dire COSA e' successo
        return "ERRORE:" + type(e).__name__, None, []
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
          if isinstance(w, dict)]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az, g, [x for x in ws if x not in NON_DETERMINISTICI]


def main():
    print("  %-30s %-14s %-16s %s"
          % ("regime", "VERI salvi", "FALSI fermati", "layer che restano sui veri"))
    print("  " + "-" * 96)
    base_veri = None
    for nome, extra in REGIMI:
        salvi, layer = 0, {}
        for v in CADUTI:
            az, _g, det = _gate(CLAIM % v, extra)
            if az.startswith("ERRORE"):
                layer[az] = layer.get(az, 0) + 1
            elif az == "persist":
                salvi += 1
            else:
                for d in det:
                    layer[d] = layer.get(d, 0) + 1
        fermati = 0
        for f in FALSI:
            az, _g, _d = _gate(CLAIM % f, extra)
            if az != "persist" and not az.startswith("ERRORE"):
                fermati += 1
        if base_veri is None:
            base_veri = salvi
        print("  %-30s %-14s %-16s %s"
              % (nome, "%d/%d" % (salvi, len(CADUTI)), "%d/%d" % (fermati, len(FALSI)),
                 ", ".join("%s x%d" % (k, v) for k, v in sorted(layer.items(),
                                                                key=lambda kv: -kv[1])) or "-"))

    print("\n=== COME SI LEGGE ===")
    print("  Un regime CURA solo se alza i VERI salvi SENZA abbassare i FALSI fermati.")
    print("  Se li alza entrambi nella stessa direzione, non e' una cura: e' un")
    print("  interruttore che spegne il gate - e i falsi lo dicono subito.")
    print("  ⚠️ Verde qui != raggiungibile da tutte le porte: su MCP il valore")
    print("     external_content e' RIFIUTATO dallo schema (mio reperto, 28/08).")


main()
