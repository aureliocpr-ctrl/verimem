r"""IL CERCHIO DELLA VETRINA, rifatto: i NOSTRI referti contro le frasi del CLIENTE.

PERCHE' ESISTE. `LANT-40` (29/08 ~02:07) diceva «5 su 5 ammessi» sui miei referti
veri, e la cella prometteva: *«MESSO ACCANTO A LANT-32 CHIUDE IL CERCHIO DELLA
VETRINA, in due numeri»*. **I due numeri non ci sono: la cella e' fra le 21
troncate in scrittura** (`LANT-70`), e il taglio e' caduto esattamente li'.

E la regola che ho scritto io stamattina chiudendo quelle celle e' che **la
misura va RIFATTA prima di citarla**. Questo banco la rifa'.

L'IPOTESI DA FALSIFICARE, che i due numeri superstiti suggeriscono:

    LANT-32   frasi da VERBALE (cliente tipo)   8/10 fermate   80%
    LANT-32   frasi da NOSTRO REFERTO           0/6  fermate    0%
    LANT-40   referti veri, 5 casi              5/5 ammessi

    ⇒ **il gate e' tarato sulla popolazione di CHI LO SCRIVE, non su quella
       del CLIENTE**

COSA CAMBIA RISPETTO A `LANT-40`, e sono tre cose imparate oggi:

  ① **source CONGELATA**. `LANT-66`: `--source "$(comando)"` RIESEGUE il comando,
     e su un bersaglio che cresce il gate confronta la misura di prima con un
     output di adesso. Qui le fonti sono costanti nel file, catturate una volta.
  ② **niente numeri DECORATIVI nei claim**. `LANT-42` e la ripetizione di oggi:
     `00-ESAME.md` fa estrarre `00` a L4.1, una data fa estrarre il giorno. Un
     numero che non e' la grandezza misurata sporca il verdetto in entrambe le
     direzioni.
  ③ **ISOLATO contro SEQUENZA** (@ws8): ogni claim gira **due volte**, una in
     uno store nuovo e una dopo gli altri, perche' un esito che dipende
     dall'ordine non e' una proprieta' del claim.

DUE POPOLAZIONI, ed e' il punto della misura:
  A  REFERTI NOSTRI  - frasi come le scriviamo noi in `00-ESAME.md`, con la
     fonte che le sostiene (l'uscita di un banco). Devono PASSARE: sono vere.
  B  FRASI DA CLIENTE - lo stesso tipo di contenuto nella lingua di un verbale
     d'ufficio o di un referto professionale. **Anche queste sono VERE e
     sostenute dalla loro fonte**: se il gate le ferma, e' un falso allarme
     sull'utente che paga.

⚠️ Il confronto e' equo solo se le due popolazioni dicono **cose vere entrambe**.
Non metto claim falsi in B: misurerei un'altra cosa.

    python docs/stato-reale/banchi/ws7-il-cerchio-della-vetrina-rifatto.py
"""
from __future__ import annotations

import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="ws7_cerchio_")
os.environ["HIPPO_DATA_DIR"] = _TMP

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

#: fonte A - l'uscita di un banco, come la produciamo noi
F_BANCO = """  A  righe che cominciano con '|'  (grep grezzo)   =  849
  B  ID in prima colonna, tabella grande           =  258
  C1       forma Wn-n  (W7-1, W2-57)               =  160
  falsi positivi del vecchio: 0
  L4.2 FERMA (5): grounding 0.3, 5.4, 14.6, 70.5, 97.9
  L4.2 PASSA (4): grounding 98.1, 99.1, 99.5, 99.9"""

#: fonte B - un verbale d'ufficio, con gli STESSI fatti dentro
F_VERBALE = """Verbale di collaudo. Il collaudatore ha esaminato le righe della
tabella: 849 cominciano con la barra verticale, 258 recano un identificativo
nella prima colonna, 160 di queste nella forma con sigla e numero. Non e' stata
riscontrata alcuna falsa attribuzione. Il criterio di arresto ha operato su
cinque casi con punteggio da 0,3 a 97,9 e ha lasciato passare quattro casi con
punteggio da 98,1 a 99,9."""

#: A - come le scriviamo noi (referto tecnico)
NOSTRI = [
    "Le righe con un identificativo nella prima colonna sono 258.",
    "Gli identificativi nella forma con sigla e numero sono 160.",
    "I falsi positivi del righello vecchio sono 0.",
    "Il layer ferma con punteggio fino a 97.9 e lascia passare da 98.1 in su.",
    "Le righe che cominciano con la barra verticale sono 849.",
]

#: B - lo STESSO contenuto nella lingua di chi ci paga
CLIENTE = [
    "Il collaudatore ha accertato che le righe recanti identificativo "
    "ammontano a 258.",
    "Risultano 160 identificativi nella forma con sigla e numero, come da "
    "verbale.",
    "Non e' stata riscontrata alcuna falsa attribuzione a carico del criterio "
    "precedente.",
    "Il criterio di arresto ha operato fino a 97.9 e ha consentito il "
    "passaggio da 98.1.",
    "Le righe recanti la barra verticale in apertura ammontano a 849.",
]


def esegui(claim: str, fonte: str) -> tuple[str, float | None, list[str]]:
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    return (str(getattr(r, "action", None) or getattr(r, "decision", None) or "?"),
            getattr(r, "grounding_score", None), ws)


def main() -> int:
    print("  %-9s %-3s %-10s %8s  %s" % ("pop", "n", "azione", "ground", "layer"))
    esiti: dict[str, list[str]] = {"NOSTRI": [], "CLIENTE": []}
    for nome, claims, fonte in (("NOSTRI", NOSTRI, F_BANCO),
                                ("CLIENTE", CLIENTE, F_VERBALE)):
        for i, c in enumerate(claims, 1):
            az, g, ws = esegui(c, fonte)
            esiti[nome].append(az)
            print("  %-9s %-3d %-10s %8s  %-28s%s"
                  % (nome, i, az, ("%.1f" % g) if g is not None else "None",
                     ",".join(ws)[:28] or "-",
                     "  <== FERMATO, ed e' VERO" if az != "persist" else ""))

    #: ③ controllo isolato-contro-sequenza (@ws8): l'esito dipende dall'ordine?
    print("\n  --- controllo ISOLATO contro SEQUENZA (ogni claim in uno store nuovo) ---")
    diversi = 0
    for nome, claims, fonte in (("NOSTRI", NOSTRI, F_BANCO),
                                ("CLIENTE", CLIENTE, F_VERBALE)):
        for i, c in enumerate(claims):
            d = tempfile.mkdtemp(prefix="ws7_iso_")
            os.environ["HIPPO_DATA_DIR"] = d
            try:
                az, _, _ = esegui(c, fonte)
            finally:
                shutil.rmtree(d, ignore_errors=True)
            if az != esiti[nome][i]:
                diversi += 1
                print(f"     {nome} {i+1}: sequenza={esiti[nome][i]}  isolato={az}  <== DIPENDE DALL'ORDINE")
    print(f"     claim il cui esito cambia fra isolato e sequenza: {diversi} su "
          f"{len(NOSTRI) + len(CLIENTE)}")

    print("\n  === il cerchio, in due numeri ===")
    for nome in ("NOSTRI", "CLIENTE"):
        passati = sum(1 for a in esiti[nome] if a == "persist")
        print(f"     {nome:8}  ammessi {passati}/{len(esiti[nome])}"
              f"   fermati (falsi allarmi) {len(esiti[nome]) - passati}")
    dn = sum(1 for a in esiti["NOSTRI"] if a == "persist")
    dc = sum(1 for a in esiti["CLIENTE"] if a == "persist")
    print(f"\n  ⇒ ipotesi «il gate e' tarato su chi lo scrive»: "
          f"{'REGGE su questa popolazione' if dn > dc else ('FALSIFICATA: il cliente passa quanto noi o piu' if dc >= dn else '?')}")
    print(f"     divario: {dn - dc} claim su {len(NOSTRI)}")
    print(f"\n  REGIME  store temporaneo, fuori pytest, ground_write=True, "
          f"porta run_validation_gate")
    print(f"          fonti COSTANTI nel file (non rigenerate), nessun numero decorativo,")
    print(f"          10 claim tutti VERI e sostenuti dalla loro fonte, 2 popolazioni")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
