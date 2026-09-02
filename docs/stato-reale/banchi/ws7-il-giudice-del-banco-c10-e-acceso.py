"""Il banco C10 gira col giudice acceso o spento? A/B nella stessa esecuzione.

PERCHE'. @ws2 il 02/09 alle 01:50 (W2-389) ha misurato che chiamando il gate
direttamente **il giudice non gira**: run_validation_gate ha
`ground_write: bool | None = None`, e con None legge l'ambiente
(`_grounding_write_on()` -> ENGRAM_GROUNDING_WRITE, vuota = False).
Il segnale per accorgersene: **grounding_score torna None**, non un numero basso.

CIO' CHE HO LETTO NEL CODICE, e che questo banco deve confermare o smentire:
  · client.py:460  `def add(..., ground: bool | None = None, ...)`   <- default None
  · client.py:582  `ground_write=ground or None`                     <- resta None
  · benchmark/c10_falsita_servite_vs_mem0.py:252
        `mem.add(claim, source=fonte, topic=...)`                    <- NON passa ground
  · su questa macchina ENGRAM_GROUNDING_WRITE non e' impostata
  ⇒ PREDIZIONE: il ramo A (come chiama il banco) da' grounding_score None.

⚠️ MA L'ARTEFATTO VERSIONATO DICE IL CONTRARIO: c10_heldout_intero.json ha
`moat_esclusivo=5` e `moat_con_layer_lessicale=68`, cioe' 73 veri persi
attribuiti al moat — che non puo' decidere se non gira. Quindi o la variabile
era impostata nella shell di chi l'ha eseguito, o la mia lettura sbaglia.
**Questo banco serve a non gridare prima di saperlo.**

IL CONTROLLO POSITIVO E' IL RAMO B: `ground=True` esplicito. Se anche B tornasse
None, il difetto sarebbe nel mio misuratore e non nel banco C10 — e il verdetto
sarebbe "inconcludente", non "spento".

REGIME: due Memory su due data dir temporanee, **stesso claim e stessa source**;
unica differenza il flag. Un solo processo, il modello del gate si carica una
volta (~758 MB). Nessuna rete.
"""
import os
import sys
import tempfile

#: isolo PRIMA di importare: HIPPO_DATA_DIR ha la precedenza sugli altri due alias
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_giudice_")

CLAIM = "The Eiffel Tower is located in Paris and was completed in 1889."
FONTE = ("The Eiffel Tower, completed in 1889, stands in Paris, France, "
         "and was designed by Gustave Eiffel for the World's Fair.")


def _prova(etichetta: str, ground) -> object:
    """Una scrittura in una data dir sua, e il grounding_score che ne esce."""
    from verimem import Memory

    os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix=f"ws7_{etichetta}_")
    mem = Memory()
    if ground is None:
        r = mem.add(CLAIM, source=FONTE, topic="ws7/giudice")   # come il C10
    else:
        r = mem.add(CLAIM, source=FONTE, topic="ws7/giudice", ground=ground)

    punteggio = (getattr(r, "grounding_score", None)
                 or (r.get("grounding_score") if isinstance(r, dict) else None))
    stato = (getattr(r, "status", None)
             or (r.get("status") if isinstance(r, dict) else None))
    return punteggio, stato


def main() -> int:
    var = os.environ.get("ENGRAM_GROUNDING_WRITE", "")
    print(f"  ENGRAM_GROUNDING_WRITE = {var!r}"
          f"   {'(impostata)' if var else '(NON impostata)'}\n")

    a_p, a_s = _prova("A_come_il_c10", None)
    print(f"  A  add(claim, source=...)             "
          f"grounding_score={a_p!r}  status={a_s!r}   <- come chiama il C10")

    b_p, b_s = _prova("B_ground_true", True)
    print(f"  B  add(claim, source=..., ground=True) "
          f"grounding_score={b_p!r}  status={b_s!r}   <- CONTROLLO POSITIVO\n")

    if b_p is None:
        print("  ⚠️ INCONCLUDENTE: nemmeno il controllo positivo ha un punteggio.")
        print("     Il difetto e' nel MIO misuratore, non nel banco C10.")
        return 2
    if a_p is None:
        print("  🔴 CONFERMATO: chiamando come fa il C10 il giudice NON gira.")
        print("     Il numero del C10 dipende da una variabile d'ambiente che")
        print("     il banco non imposta e il repro-pack non dichiara.")
        return 1
    print("  🟢 SMENTITO: anche senza ground il giudice gira. La mia lettura")
    print("     del codice sbagliava, e il banco C10 non e' esposto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
