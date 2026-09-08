"""D-1 dalla PORTA, non dal gate: le stesse 14 frasi passate da `Memory.add`.

PERCHE' ESISTE, dopo il banco in-process del 07/09 13:07
=======================================================
`ws7-d1-le-sette-forme-e-i-veri-composti.py` chiama `run_validation_gate`
direttamente e da' **7/7 fermate** sul braccio A. Il reperto originale
(LANT-175, 05/09) diceva l'opposto — le sette forme PASSANO — ma era misurato
**sul pacchetto pubblicato 0.7.6 e su tre porte**.

⚠️ **IL LIVELLO A CUI MISURI DECIDE IL VERDETTO.** Due spiegazioni, e il banco
in-process non puo' separarle:
    (a) una cura e' entrata fra il 05/09 e oggi;
    (b) il gate ferma, ma **la porta non usa quel verdetto** — cioe' il difetto
        non e' nel gate, e' nella giuntura fra gate e porta.
Questo banco toglie una variabile: **stesse frasi, stessa fonte, stesso albero,
ma passate da `Memory.add`** — la porta che un utente usa davvero.

COME SI LEGGE L'ESITO, e non e' `action`
----------------------------------------
Alla porta il verdetto si legge **dallo store**, come fa
`tests/test_all_write_channels_judge_a_source.py:165`:

    SELECT status, quarantined_by FROM facts WHERE id = ?

`status == 'quarantined'` ⇒ **fermato**: il fatto e' scritto ma tenuto fuori dal
recall di default. Qualunque altro stato ⇒ **passato**, cioe' servito come vero.

🔑 I TESTI NON SONO RISCRITTI: si importano dal banco in-process, cosi' le due
   misure non possono divergere su cosa hanno misurato. Se quel file cambia,
   cambia anche questo.

CONTROLLO POSITIVO, che deve poter smentirmi: la coda nuda da sola
   («E' verificata.») DEVE risultare `quarantined` anche da qui. Se non lo e',
   il banco esce NON MISURATO senza emettere numeri: alla porta il righello
   sarebbe scollegato e ogni «passata» sarebbe rumore.

⚠️ STORE: **temporaneo, nella scratchpad, mai quello di Aurelio.** Il banco
   crea la sua cartella e non tocca nient'altro.

    ENGRAM_ENCODE_SERVICE=0 python docs/stato-reale/banchi/ws7-d1-dalla-porta-sdk.py
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
if str(RADICE) not in sys.path[:1]:
    sys.path.insert(0, str(RADICE))


def _non_misurato(perche: str) -> None:
    print()
    print("=" * 68)
    print("NON MISURATO")
    print("=" * 68)
    print(f"  {perche}")
    print()
    print("  Il banco NON emette numeri: un verdetto senza il suo presupposto")
    print("  accusa (o assolve) il prodotto senza prova.")
    raise SystemExit(3)


def _casi():
    """I testi vengono dal banco in-process: una fonte sola, mai due copie."""
    f = Path(__file__).with_name("ws7-d1-le-sette-forme-e-i-veri-composti.py")
    if not f.exists():
        _non_misurato(f"il banco in-process non c'e': {f}")
    spec = importlib.util.spec_from_file_location("_d1", f)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception as exc:  # noqa: BLE001
        _non_misurato(f"import dei testi fallito: {type(exc).__name__}: {exc}")
    return m.BRACCIO_A, m.BRACCIO_B, m.CONTROLLO_POSITIVO, m.FONTE


def main() -> int:
    print("D-1 DALLA PORTA — le stesse 14 frasi passate da Memory.add")
    print("=" * 68)

    A, B, CP, FONTE = _casi()

    try:
        import verimem
        from verimem import Memory
    except Exception as exc:  # noqa: BLE001
        _non_misurato(f"import verimem fallito: {type(exc).__name__}: {exc}")

    tmp = Path(tempfile.mkdtemp(prefix="ws7_d1_porta_"))
    db = tmp / "store.db"
    print(f"albero misurato : {verimem.__file__}")
    print(f"versione        : {getattr(verimem, '__version__', 'ignota')}")
    print(f"store temporaneo: {db}")
    print()

    try:
        mem = Memory(str(db))
    except Exception as exc:  # noqa: BLE001
        _non_misurato(f"Memory() non si apre: {type(exc).__name__}: {exc}")

    def scrivi(testo: str, topic: str):
        """Ritorna (stato_nello_store, ricevuta). Lo stato e' il verdetto."""
        try:
            r = mem.add(testo, topic=topic, source=FONTE)
        except Exception as exc:  # noqa: BLE001
            _non_misurato(f"Memory.add ha sollevato {type(exc).__name__}: {exc}")
        fid = (r or {}).get("id") if isinstance(r, dict) else getattr(r, "id", None)
        if not fid:
            _non_misurato(f"la ricevuta non porta un id: {r!r}")
        try:
            with sqlite3.connect(str(db)) as cx:
                riga = cx.execute(
                    "SELECT status FROM facts WHERE id = ?", (fid,)
                ).fetchone()
        except Exception as exc:  # noqa: BLE001
            _non_misurato(f"lo store non si legge: {type(exc).__name__}: {exc}")
        if riga is None:
            return "assente", r
        return str(riga[0]), r

    # ── il controllo che puo' smentirmi, PRIMA di ogni altro numero ──────
    t0 = time.time()
    nome_cp, testo_cp = CP
    stato_cp, _ = scrivi(testo_cp, "ws7/d1-porta/cp")
    print(f"controllo positivo: {nome_cp}  ->  status={stato_cp}"
          f"   ({time.time() - t0:.1f} s, il giudice si carica qui)")
    if stato_cp != "quarantined":
        _non_misurato(
            f"il controllo positivo NON e' quarantined (status={stato_cp}): dalla "
            "porta il righello e' scollegato e nessun altro numero di questo "
            "banco vale."
        )
    print()

    print("BRACCIO A — self-claim in coda a un vero (DEVE fermare)")
    a_fermate = 0
    for nome, testo in A:
        stato, _ = scrivi(testo, "ws7/d1-porta/a")
        ok = stato == "quarantined"
        a_fermate += ok
        print(f"  {'FERMATA ' if ok else 'PASSATA '} {nome:24s} status={stato}")

    print()
    print("BRACCIO B — fatti composti VERI (DEVONO passare)")
    b_fermate = 0
    for nome, testo in B:
        stato, _ = scrivi(testo, "ws7/d1-porta/b")
        ko = stato == "quarantined"
        b_fermate += ko
        print(f"  {'FERMATO ' if ko else 'passato '} {nome:24s} status={stato}"
              + ("   ← FALSO POSITIVO" if ko else ""))

    print()
    print("=" * 68)
    print(f"DALLA PORTA:  A {a_fermate}/7 fermate   ·   B {b_fermate}/7 fermati")
    print("IN-PROCESS (07/09 13:07):  A 7/7 fermate   ·   B 1/7 fermati")
    #: ⚠️ 07/09 13:16 — QUI C'ERA UNA CONCLUSIONE PRECOMPILATA, e ha parlato
    #: prima della misura: alla prima esecuzione questo banco ha stampato «LA
    #: PORTA NON USA IL VERDETTO DEL GATE … il difetto e' nella GIUNTURA».
    #: L'A/B successivo l'ha smentita: chiamato dalla porta il gate `L1.15`
    #: **non lo emette proprio** (`layers=[]` nella ricevuta), e col flag
    #: `provenance_trusted=True` il banco in-process ferma ancora 7/7. Non e'
    #: una giuntura che scarta un verdetto: e' lo stesso gate che, con altri
    #: argomenti, decide altro. ⇒ **il banco stampa i numeri e la differenza,
    #: l'interpretazione la fa chi legge, dopo l'A/B.**
    if a_fermate < 7:
        print("⇒ 🔴 LA PORTA FERMA MENO DEL GATE chiamato a mano. Il banco NON")
        print("  dice perche': la causa si isola con un A/B sugli argomenti che")
        print("  la porta passa in piu' (client.py:735-748), una variabile per")
        print("  volta — vedi ws7-d1-quale-argomento-spegne-l1-15.py.")
    else:
        print("⇒ la porta ferma quanto il gate: la differenza col reperto del")
        print("  05/09 non sta negli argomenti della chiamata.")
    print(f"(store temporaneo lasciato in {tmp}: cancellabile)")
    return 0 if a_fermate == 7 and b_fermate == 0 else 1


if __name__ == "__main__":
    if os.environ.get("ENGRAM_ENCODE_SERVICE") not in ("0", None, ""):
        print("⚠️  ENGRAM_ENCODE_SERVICE non e' 0: rilancia con ENGRAM_ENCODE_SERVICE=0.")
    sys.exit(main())
