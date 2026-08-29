"""IL MOAT ATTRAVERSA LA LINGUA? — la coppia MISTA, che nessuno ha misurato.

W7-50 ha contato che **79 su 390** dei quarantinati con span hanno **claim e
fonte in lingue diverse** (20,3%). Quel numero apre una domanda che il banco
NON misurava: **il moat regge quando la fonte e' in un'altra lingua?**

⚖️ **Perche' non e' un doppione del pezzo 2 di un'altra istanza**: quella misura
varia la lingua di **claim e fonte INSIEME** (IT/IT contro EN/EN) e conclude —
correttamente — che conta la **forma** della fonte, non la lingua. Qui varia la
lingua di **UNO SOLO DEI DUE**. Sono due assi diversi: il suo dice che il gate si
comporta uguale *dentro* ciascuna lingua, il mio chiede cosa succede *fra* le due.

LA GRIGLIA — 2 lingue del claim x 2 lingue della fonte x vero/falso = 8 celle.
La fonte EN e' la **traduzione fedele** di quella IT, **con gli stessi numeri**:
cosi' `L4.1` (valori non nella fonte) non scatta sui veri, e cio' che resta a
decidere e' il **moat**, che e' l'oggetto della misura.

ATTESA DICHIARATA PRIMA DI ESEGUIRE (e falsificabile):
  · CONCORDI vero  -> ALTO   (replica il pezzo 2: dev'essere cosi' o il mio
                              banco non e' confrontabile con il suo)
  · CONCORDI falso -> BASSO  (il gate lavora)
  · DISCORDI falso -> BASSO  ⚠️ se invece PASSA, e' un VARCO: il gate
                              ammetterebbe un falso solo perche' la fonte e' in
                              un'altra lingua. Sarebbe il reperto piu' grave.
  · DISCORDI vero  -> ??? E' LA DOMANDA. Se resta ALTO, il moat attraversa la
                              lingua e il 20,3% di W7-50 non e' un problema. Se
                              CROLLA, allora una fonte su cinque porta un falso
                              allarme sistematico, e la famiglia e' grande.

CONTROLLI CHE POSSONO FALLIRE:
 (1) se le concordi non riproducono il pattern noto (vero alto, falso basso),
     il banco non e' comparabile e lo dico invece di leggere le discordi.
 (2) i numeri del claim VERO devono comparire in ENTRAMBE le fonti alla lettera:
     lo verifico nel banco, altrimenti misuro `L4.1` credendo di misurare il moat.
 (3) stampo il layer che ferma, non solo il punteggio: «basso» e «fermato da chi»
     sono due informazioni diverse, e senza la seconda attribuirei al moat una
     decisione lessicale.

    python -u docs/stato-reale/banchi/il-moat-attraversa-la-lingua.py
"""

from __future__ import annotations

import re
import sys

FONTE_IT = (
    "Referto della sessione del 12 marzo. Il job windows ha impiegato 45 minuti "
    "e ha prodotto 22 test passati, 8 saltati e 3 falliti su 7 file. "
    "La suite security ha registrato 19 esiti positivi con durata media 6 minuti."
)
FONTE_EN = (
    "Session report of March 12. The windows job took 45 minutes "
    "and produced 22 passed tests, 8 skipped and 3 failed across 7 files. "
    "The security suite recorded 19 positive outcomes with an average duration of 6 minutes."
)

CLAIM = {
    ("it", "vero"): "Il job windows ha impiegato 45 minuti e ha prodotto 22 test passati.",
    ("en", "vero"): "The windows job took 45 minutes and produced 22 passed tests.",
    ("it", "falso"): "Il job windows ha impiegato 90 minuti e ha prodotto 40 test passati.",
    ("en", "falso"): "The windows job took 90 minutes and produced 40 passed tests.",
}
FONTI = {"it": FONTE_IT, "en": FONTE_EN}
NUM = re.compile(r"\d+")


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  -- CONTROLLO (2): i numeri dei claim VERI sono in ENTRAMBE le fonti?")
    fuori = []
    for (lg, tipo), c in CLAIM.items():
        if tipo != "vero":
            continue
        for n in NUM.findall(c):
            for nome, f in FONTI.items():
                if n not in f:
                    fuori.append((lg, n, nome))
    if fuori:
        print(f"     CADUTO - {fuori[:6]}: misurerei L4.1, non il moat.")
        return 1
    print("     retto - ogni cifra dei veri compare in entrambe le fonti")

    print("\n  == LA GRIGLIA  (claim x fonte x verita')")
    print(f"     {'claim':>6} {'fonte':>6} {'tipo':>6} {'score':>8}  {'esito':<11} layer")
    esiti = {}
    for tipo in ("vero", "falso"):
        for lc in ("it", "en"):
            for lf in ("it", "en"):
                g = run_validation_gate(
                    proposition=CLAIM[(lc, tipo)], verified_by=[], topic=None,
                    agent=None, source=FONTI[lf], ground_write=True)
                score = getattr(g, "grounding_score", None)
                azione = getattr(g, "action", None)
                ws = getattr(g, "warnings", None) or []
                layer = ",".join(sorted({str((w or {}).get("layer") or "?")
                                         for w in ws})) or "-"
                esiti[(lc, lf, tipo)] = (score, azione, layer)
                s = "n/d" if score is None else f"{score:.1f}"
                marca = "  " if lc == lf else " *"  # * = coppia MISTA
                print(f"    {marca}{lc:>5} {lf:>6} {tipo:>6} {s:>8}  {str(azione):<11} {layer}")

    def sc(lc, lf, tipo):
        v = esiti[(lc, lf, tipo)][0]
        return -1.0 if v is None else float(v)

    conc_vero = [sc("it", "it", "vero"), sc("en", "en", "vero")]
    conc_falso = [sc("it", "it", "falso"), sc("en", "en", "falso")]
    disc_vero = [sc("it", "en", "vero"), sc("en", "it", "vero")]
    disc_falso = [sc("it", "en", "falso"), sc("en", "it", "falso")]

    print("\n  -- CONTROLLO (1): le CONCORDI riproducono il pattern noto?")
    ok = min(conc_vero) >= 80.0 and max(conc_falso) < 80.0
    print(f"     concordi vero {conc_vero}   concordi falso {conc_falso}")
    if not ok:
        print("     CADUTO - le concordi non fanno vero-alto/falso-basso: questo")
        print("     banco non e' confrontabile, e NON leggo le discordi.")
        return 1
    print("     retto - vero alto e falso basso su entrambe le lingue")

    print("\n  == LA RISPOSTA — la coppia MISTA")
    print(f"     discordi VERO : {disc_vero}")
    print(f"     discordi FALSO: {disc_falso}")

    caduta = min(conc_vero) - min(disc_vero)
    if min(disc_vero) >= 80.0:
        print(f"     🟢 IL MOAT ATTRAVERSA LA LINGUA: i veri con fonte tradotta")
        print(f"        restano sopra 80 (caduta massima {caduta:.1f} punti).")
        print("        ⇒ Il 20,3% di W7-50 NON e' un problema di per se'.")
    elif min(disc_vero) < 40.0:
        print(f"     🔴 NON LA ATTRAVERSA: un fatto VERO con la fonte nell'altra")
        print(f"        lingua CROLLA sotto il cut (caduta {caduta:.1f} punti).")
        print("        ⇒ Una fonte su cinque porta un falso allarme sistematico.")
    else:
        print(f"     🟡 CADE IN BANDA: il vero con fonte tradotta finisce fra 40 e")
        print(f"        80 (caduta {caduta:.1f}) ⇒ ne' ammesso ne' rifiutato, cioe'")
        print("        consegnato alla band escalation, che W7-47 misura fragile.")

    if max(disc_falso) >= 80.0:
        print("     🚨🚨 E C'E' UN VARCO: un claim FALSO passa quando la fonte e'")
        print("        nell'altra lingua. E' piu' grave del falso allarme.")
    else:
        print("     ✅ Nessun varco: i falsi restano fermati anche in coppia mista.")

    # ── IL SECONDO REPERTO, che la griglia ha STAMPATO e il titolo non dice.
    #    Nelle due celle MISTE vere compare `L4.2` e nelle concordi no. Con due
    #    celle e' un'osservazione, non una misura: la porto a otto.
    print("\n  == IL SECONDO REPERTO: `L4.2` scatta solo sulle coppie MISTE?")
    print("     (avviso, non veto: l'azione resta `persist` — misurato in W7-35)")
    EXTRA = [
        ("La suite security ha registrato 19 esiti positivi.",
         "The security suite recorded 19 positive outcomes."),
        ("Il job windows ha prodotto 3 test falliti su 7 file.",
         "The windows job produced 3 failed tests across 7 files."),
        ("La durata media e' di 6 minuti e i test saltati sono 8.",
         "The average duration is 6 minutes and the skipped tests are 8."),
    ]
    misto_con, misto_tot, conc_con, conc_tot = 0, 0, 0, 0
    for it_c, en_c in EXTRA:
        for lc, c in (("it", it_c), ("en", en_c)):
            for lf in ("it", "en"):
                g = run_validation_gate(
                    proposition=c, verified_by=[], topic=None, agent=None,
                    source=FONTI[lf], ground_write=True)
                ws = getattr(g, "warnings", None) or []
                ha = any("4.2" in str((w or {}).get("layer") or "") for w in ws)
                if lc == lf:
                    conc_tot += 1
                    conc_con += 1 if ha else 0
                else:
                    misto_tot += 1
                    misto_con += 1 if ha else 0
    # le due celle vere della griglia entrano nel conteggio
    misto_tot += 2
    misto_con += sum(1 for k in (("it", "en", "vero"), ("en", "it", "vero"))
                     if "4.2" in esiti[k][2])
    conc_tot += 2
    conc_con += sum(1 for k in (("it", "it", "vero"), ("en", "en", "vero"))
                    if "4.2" in esiti[k][2])
    print(f"     coppie MISTE   con `L4.2`: {misto_con} su {misto_tot}")
    print(f"     coppie CONCORDI con `L4.2`: {conc_con} su {conc_tot}")
    if misto_con > conc_con and conc_con == 0:
        print("     🔑 SEPARAZIONE NETTA: il moat (semantica) attraversa la lingua,")
        print("        ma il layer che guarda il VICINATO del valore no — e mette")
        print("        un avviso su ogni fatto VERO la cui fonte e' tradotta.")
    elif misto_con == conc_con:
        print("     ⇒ NESSUNA separazione: `L4.2` non distingue le miste, e le due")
        print("     celle della griglia erano un caso. L'osservazione CADE.")
    else:
        print("     ⇒ Separazione PARZIALE: il numero e' questo, e non lo forzo")
        print("     in nessuna delle due direzioni.")

    print("\n  ⚠️ COSA NON DICE: una sola fonte, una sola coppia di lingue, forma")
    print("  di PROSA. Un'altra istanza ha misurato che la FORMA della fonte")
    print("  (tabellare contro prosa) sposta il verdetto: qui la tengo fissa, e")
    print("  quindi questo banco NON separa lingua e forma su tutte le celle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
