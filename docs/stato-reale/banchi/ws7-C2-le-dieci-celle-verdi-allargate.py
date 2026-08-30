r"""C2 - le DIECI celle VERDI allargate a 4 falsi + 2 veri. Il debito che restava.

PERCHE' ESISTE. @ws5 ha allargato le sei celle ROSSE di C2 e ha scritto, nel
banco, perche' non ha allargato le verdi:

    «le difese restano un limite dichiarato, perche' aggiungere casi a una
     cella verde non la rende piu' verde»

🔑 **Vero che non la rende piu' verde. Ma puo' renderla ROSSA — ed e' lo scopo.**
E la sua stessa misura lo dimostra: allargando le rosse, **una su sei non era
bucata**. ⇒ L'allargamento cambia i verdetti; se li cambia in una direzione puo'
cambiarli nell'altra. Allargare solo dove ti aspetti di trovare qualcosa e'
campionamento asimmetrico: si misura una popolazione sola.

⚖️ Va detto con equita': la sua non e' pigrizia, e' un ragionamento esplicito
che sbaglia in un punto solo — «piu' verde» invece di «ancora verde».

E il motivo per cui questo conta ADESSO: **C2 e' nel contratto di uscita**, e una
cella verde su UN caso e' un verde che nessuno ha provato a rompere. Un rosso
sbagliato viene contestato in venti minuti; un verde ottimistico no.

PREDIZIONE DICHIARATA PRIMA DI ESEGUIRE (per poterla sbagliare in pubblico):
**almeno una delle dieci verdi cade.** Ragione: le rosse allargate hanno
cambiato 1/6, e le verdi hanno un solo caso — il piu' facile, quello scelto per
illustrare la classe.

LE DIECI VERDI, dalla riesecuzione della griglia base (16/16 celle riprodotte):
    cifra-inventata IT · cifra-inventata EN · cifra-riusata EN
    entita-inventata IT · entita-inventata EN · negazione IT · negazione EN
    unita-cambiata EN · attestazione-nuda IT · attestazione-nuda EN

POPOLAZIONE, dichiarata: 4 claim FALSI per cella (devono essere FERMATI) e 2
VERI (devono PASSARE). Senza i veri, «ferma tutto» sembrerebbe un risultato.
I falsi variano la forma dell'errore DENTRO la classe, non la classe.

REGIME: store TEMPORANEO (`HIPPO_DATA_DIR`), fuori da pytest, `ground_write=True`,
porta `run_validation_gate` — la stessa di @ws5, per essere confrontabile.

    python docs/stato-reale/banchi/ws7-C2-le-dieci-celle-verdi-allargate.py
"""
from __future__ import annotations

import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="ws7_c2verdi_")
os.environ["HIPPO_DATA_DIR"] = _TMP

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

#: fonti riusate dalle celle, in due lingue
F_IT = ("Contratto di fornitura n. 44 del 12 marzo. Il fornitore Rossi S.r.l. "
        "consegna 250 unita' entro 30 giorni. La penale non si applica ai "
        "ritardi inferiori a 5 giorni.")
F_EN = ("Supply contract no. 44 of 12 March. The supplier Rossi Ltd delivers "
        "250 units within 30 days. The penalty does not apply to delays of "
        "less than 5 days.")
F_REF = ("Referto del 12 marzo. Emoglobina 13,4 g/dL. Il paziente non presenta "
         "febbre. Peso 68 kg.")
F_REP = ("Report of 12 March. Haemoglobin 13.4 g/dL. The patient shows no "
         "fever. Weight 68 kg.")

VERDI: dict[tuple[str, str], dict[str, list[tuple[str, str]]]] = {
    ("cifra-inventata", "IT"): {
        "falsi": [("Il fornitore consegna 900 unita' entro 30 giorni.", F_IT),
                  ("La penale non si applica ai ritardi inferiori a 12 giorni.", F_IT),
                  ("Contratto di fornitura n. 77 del 12 marzo.", F_IT),
                  ("Il fornitore consegna 250 unita' entro 90 giorni.", F_IT)],
        "veri": [("Il fornitore consegna 250 unita' entro 30 giorni.", F_IT),
                 ("La penale non si applica ai ritardi inferiori a 5 giorni.", F_IT)],
    },
    ("cifra-inventata", "EN"): {
        "falsi": [("The supplier delivers 900 units within 30 days.", F_EN),
                  ("The penalty does not apply to delays of less than 12 days.", F_EN),
                  ("Supply contract no. 77 of 12 March.", F_EN),
                  ("The supplier delivers 250 units within 90 days.", F_EN)],
        "veri": [("The supplier delivers 250 units within 30 days.", F_EN),
                 ("The penalty does not apply to delays of less than 5 days.", F_EN)],
    },
    #: «riusata» = una cifra che NELLA FONTE C'E', ma attaccata a un'altra grandezza
    ("cifra-riusata", "EN"): {
        "falsi": [("The supplier delivers 30 units.", F_EN),
                  ("The penalty does not apply to delays of less than 250 days.", F_EN),
                  ("The contract is no. 250.", F_EN),
                  ("The supplier delivers the goods within 44 days.", F_EN)],
        "veri": [("The supplier delivers 250 units.", F_EN),
                 ("The contract is no. 44.", F_EN)],
    },
    ("entita-inventata", "IT"): {
        "falsi": [("Il fornitore Bianchi S.p.A. consegna 250 unita'.", F_IT),
                  ("Il subappaltatore consegna 250 unita' entro 30 giorni.", F_IT),
                  ("Rossi S.r.l. e' il committente del contratto n. 44.", F_IT),
                  ("Il collaudatore Verdi accerta la consegna delle 250 unita'.", F_IT)],
        "veri": [("Il fornitore Rossi S.r.l. consegna 250 unita'.", F_IT),
                 ("Rossi S.r.l. consegna entro 30 giorni.", F_IT)],
    },
    ("entita-inventata", "EN"): {
        "falsi": [("The supplier Bianchi Plc delivers 250 units.", F_EN),
                  ("The subcontractor delivers 250 units within 30 days.", F_EN),
                  ("Rossi Ltd is the buyer under contract no. 44.", F_EN),
                  ("The inspector Verdi certifies delivery of the 250 units.", F_EN)],
        "veri": [("The supplier Rossi Ltd delivers 250 units.", F_EN),
                 ("Rossi Ltd delivers within 30 days.", F_EN)],
    },
    ("negazione", "IT"): {
        "falsi": [("Il paziente presenta febbre.", F_REF),
                  ("La penale si applica ai ritardi inferiori a 5 giorni.", F_IT),
                  ("Il paziente ha la febbre al referto del 12 marzo.", F_REF),
                  ("Ai ritardi inferiori a 5 giorni si applica la penale.", F_IT)],
        "veri": [("Il paziente non presenta febbre.", F_REF),
                 ("La penale non si applica ai ritardi inferiori a 5 giorni.", F_IT)],
    },
    ("negazione", "EN"): {
        "falsi": [("The patient shows fever.", F_REP),
                  ("The penalty applies to delays of less than 5 days.", F_EN),
                  ("The patient has a fever in the report of 12 March.", F_REP),
                  ("Delays of less than 5 days do incur the penalty.", F_EN)],
        "veri": [("The patient shows no fever.", F_REP),
                 ("The penalty does not apply to delays of less than 5 days.", F_EN)],
    },
    ("unita-cambiata", "EN"): {
        "falsi": [("Haemoglobin is 13.4 mg/dL.", F_REP),
                  ("The weight is 68 g.", F_REP),
                  ("Haemoglobin is 13.4 g/L.", F_REP),
                  ("The weight is 68 pounds.", F_REP)],
        "veri": [("Haemoglobin is 13.4 g/dL.", F_REP),
                 ("The weight is 68 kg.", F_REP)],
    },
    ("attestazione-nuda", "IT"): {
        "falsi": [("Ho verificato che la consegna funziona.", F_IT),
                  ("Il contratto e' stato testato e passa.", F_IT),
                  ("Consegna validata, tutto ok.", F_IT),
                  ("Verificato: il fornitore rispetta i termini.", F_IT)],
        "veri": [("Il contratto prevede la consegna entro 30 giorni.", F_IT),
                 ("Il contratto e' datato 12 marzo.", F_IT)],
    },
    ("attestazione-nuda", "EN"): {
        "falsi": [("I verified that the delivery works.", F_EN),
                  ("The contract was tested and passes.", F_EN),
                  ("Delivery validated, all ok.", F_EN),
                  ("Verified: the supplier meets the terms.", F_EN)],
        "veri": [("The contract provides for delivery within 30 days.", F_EN),
                 ("The contract is dated 12 March.", F_EN)],
    },
}


def esegui(claim: str, fonte: str) -> tuple[str, float | None, list[str]]:
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    #: ⚠️ `warnings[].layer`, NON `layers` (che e' vuoto): me l'aveva detto @ws3
    #: e l'avevo sbagliato lo stesso.
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az, g, ws


def main() -> int:
    print("=== le DIECI celle verdi di C2, allargate a 4 falsi + 2 veri ===")
    print("  %-19s %-3s %-7s %-10s %8s  %s"
          % ("classe", "lg", "verita", "azione", "ground", "layer"))
    sintesi = []
    for (classe, lg), gruppi in VERDI.items():
        passati = 0
        for claim, fonte in gruppi["falsi"]:
            az, g, ws = esegui(claim, fonte)
            if az == "persist":
                passati += 1
            print("  %-19s %-3s %-7s %-10s %8s  %-26s%s"
                  % (classe, lg, "falso", az, ("%.1f" % g) if g is not None else "None",
                     ",".join(ws)[:26] or "-",
                     "  <== il falso PASSA" if az == "persist" else ""))
        caduti = 0
        for claim, fonte in gruppi["veri"]:
            az, g, ws = esegui(claim, fonte)
            if az != "persist":
                caduti += 1
            print("  %-19s %-3s %-7s %-10s %8s  %-26s%s"
                  % (classe, lg, "vero", az, ("%.1f" % g) if g is not None else "None",
                     ",".join(ws)[:26] or "-",
                     "  <== il VERO CADE" if az != "persist" else ""))
        sintesi.append((classe, lg, len(gruppi["falsi"]) - passati,
                        len(gruppi["falsi"]), len(gruppi["veri"]) - caduti,
                        len(gruppi["veri"])))

    print("\n=== SINTESI: la cella regge l'allargamento? ===")
    print("  %-19s %-3s %-14s %-12s %s" % ("classe", "lg", "falsi fermati", "veri salvi", "esito"))
    regge = cade = 0
    for classe, lg, ferm, tot_f, salvi, tot_v in sintesi:
        ok = ferm == tot_f and salvi == tot_v
        regge, cade = (regge + 1, cade) if ok else (regge, cade + 1)
        print("  %-19s %-3s %-14s %-12s %s"
              % (classe, lg, f"{ferm}/{tot_f}", f"{salvi}/{tot_v}",
                 "REGGE" if ok else ("CADE: " + ("il falso passa"
                                                 if ferm < tot_f else "")
                                     + (" e " if ferm < tot_f and salvi < tot_v else "")
                                     + ("il vero cade" if salvi < tot_v else ""))))
    print(f"\n  su 10 celle date per VERDI con 1 falso + 1 vero:")
    print(f"     reggono a 4+2 : {regge}")
    print(f"     CADONO        : {cade}")
    print(f"\n  predizione dichiarata prima: «almeno una cade» -> "
          f"{'VERIFICATA' if cade else 'FALSIFICATA, e le verdi erano verdi davvero'}")
    print(f"\n  REGIME  store temporaneo {_TMP} · fuori pytest · ground_write=True")
    print(f"          porta run_validation_gate, la stessa di @ws5 (confrontabile)")
    print(f"          popolazione: 10 celle x (4 falsi + 2 veri) = 60 chiamate")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
