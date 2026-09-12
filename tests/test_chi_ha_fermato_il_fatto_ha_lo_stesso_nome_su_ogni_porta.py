"""T77 — «chi ha fermato il fatto» deve avere lo STESSO nome su ogni porta.

IL DIFETTO, letto nel codice (RED scritto prima della cura)
------------------------------------------------------------
`client.chi_ha_quarantinato(moat, warnings, *, agito)` nomina il layer vero, e
`'gate'` e' l'ULTIMA riga — «nessun layer bloccante in mano», non un'etichetta
di comodo. La funzione e' UNA per disegno, e il suo docstring dichiara perche':
*«una regola con due copie diverge, e questa e' gia' la seconda porta»*.

Il buco non e' nella funzione: e' nell'ARGOMENTO che una porta le passa.

    SDK   client.py   _hit_layers = _layers if action == "downgrade" else ["store-screen"]
    CLI   cli.py      agito      = ([]      if gate.action == "downgrade" else ["store-screen"])
                                    ^^ qui l'SDK ha i layer bloccanti

Stessa forma, stesso ramo, stesso `else`: cambia solo cosa c'e' nel ramo
`downgrade`. Sulla riga di comando `agito` non contiene MAI i layer, quindi il
ciclo non trova niente e la funzione cade sull'ultima riga.

PERCHE' NESSUNO L'AVEVA VISTO — e decide la forma di questo banco
------------------------------------------------------------------
La precedenza di `chi_ha_quarantinato` ha rami che **non passano da `agito`**:

    store-screen   dal marcatore        uguale sulle due porte
    moat failed    dai warnings         uguale sulle due porte
    L1             dai warnings         uguale sulle due porte
    ------------------------------------------------------------
    L3 · L4.1 · SOURCE_TRUST · L4-skipped   DA `agito`   <- solo qui diverge
    nessuno                                 'gate'

⇒ **Sui casi piu' comuni le due porte concordano**, ed e' la ragione per cui il
difetto e' rimasto invisibile: si vede solo quando a fermare e' un layer che
arriva dalla lista degli agito.

Da qui i DUE bracci qui sotto, a una variabile sola: uno che passa dai warning
(**deve concordare**, ed e' il controllo positivo del banco) e uno che passa
dagli agito (**oggi diverge**). Senza il primo, un campo che scrivesse sempre
la stessa parola passerebbe questo test.

⚠️ REGIME: la porta CLI si misura in SOTTOPROCESSO, che e' l'unico modo di
attraversarla davvero — e che NON eredita gli stub del `conftest`. Ogni braccio
usa una `HIPPO_DATA_DIR` sua, e i due lati leggono la stessa colonna.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

#: I rami che NON passano da `agito`: se il caso «divergente» finisce qui, il
#: banco non ha armato la trappola e deve dirlo invece di passare.
_NON_PASSANO_DA_AGITO = ("store-screen", "moat", "L1")


def _quarantined_by(db_path: Path, fid: str) -> str | None:
    """La colonna, letta in sola lettura. ``None`` se il fatto non c'e'."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        r = conn.execute(
            "SELECT quarantined_by, status FROM facts WHERE id = ?", (fid,)
        ).fetchone()
        return None if r is None else ((r[0] or ""), r[1])
    finally:
        conn.close()


def _dalla_riga_di_comando(tmp: Path, claim: str, source: str | None):
    """Scrive dalla porta CLI, in sottoprocesso, e rende (stato, chi, output).

    Rende ``chi = None`` quando il fatto non e' stato quarantinato: chi chiama
    lo distingue da «quarantinato senza autore», che e' un'altra cosa.
    """
    env = os.environ.copy()
    env["HIPPO_DATA_DIR"] = str(tmp)
    env["HIPPO_OFFLINE"] = "1"
    for v in [k for k in env if k.startswith(("VERIMEM_", "ENGRAM_", "HIPPO_"))]:
        if v not in ("HIPPO_DATA_DIR", "HIPPO_OFFLINE"):
            env.pop(v, None)

    cmd = [sys.executable, "-m", "verimem.cli", "facts", "add",
           "--proposition", claim, "--topic", "t/porte", "--validate", "full"]
    if source:
        cmd += ["--source", source]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                          timeout=600)
    return proc


def _dall_sdk(tmp: Path, claim: str, source: str | None):
    """Lo STESSO claim dalla porta SDK, nello stesso processo."""
    from verimem.client import Memory
    mem = Memory(str(tmp / "sdk.db"))
    ricevuta = mem.add(claim, topic="t/porte", source=source, validate="full")
    return mem, ricevuta


def _chi_dalla_cli(dir_cli: Path) -> tuple[str | None, list[str]]:
    """L'autore dell'ULTIMO fatto quarantinato lasciato dal sottoprocesso.

    La porta CLI sceglie da se' dove mettere lo store dentro `HIPPO_DATA_DIR`:
    si cercano i `.db` invece di indovinare il nome. Rende anche l'elenco di
    quelli visti, perche' un `None` con la lista vuota e' un altro difetto
    (il comando non ha scritto) rispetto a un `None` con i file presenti.
    """
    visti = sorted(dir_cli.rglob("*.db"))
    for p in visti:
        conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        try:
            r = conn.execute(
                "SELECT quarantined_by FROM facts WHERE status = 'quarantined' "
                "ORDER BY rowid DESC LIMIT 1").fetchone()
        except sqlite3.DatabaseError:
            r = None
        finally:
            conn.close()
        if r is not None:
            return (r[0] or ""), [q.name for q in visti]
    return None, [q.name for q in visti]


def test_un_caso_che_NON_passa_dagli_agito_da_lo_stesso_nome_sulle_due_porte(
        tmp_path) -> None:
    """CONTROLLO POSITIVO — e va letto PRIMA dell'altro.

    Un'auto-affermazione senza fonte viene fermata da `L1`, che
    `chi_ha_quarantinato` legge dai WARNING e non dagli agito. Le due porte
    devono dire la stessa cosa, ed e' cio' che rende non vuoto il confronto
    nell'altra cella: se anche qui divergessero, il banco starebbe misurando
    due ambienti diversi invece di una differenza di codice.

    Se questa cella cade, NON leggere l'altra: prima si aggiusta il banco.
    """
    claim = "Ho verificato personalmente che la migrazione e' riuscita."

    proc = _dalla_riga_di_comando(tmp_path / "cli", claim, None)
    mem, ricevuta = _dall_sdk(tmp_path / "sdk", claim, None)

    sid = ricevuta.get("id") or ricevuta.get("fact_id") or ""
    lato_sdk = _quarantined_by(Path(mem.semantic.db_path), sid) if sid else None

    assert lato_sdk is not None and lato_sdk[1] in ("quarantined", "rejected"), (
        f"CONTROLLO POSITIVO SPENTO: l'auto-affermazione senza fonte NON e' "
        f"stata fermata dall'SDK (letto {lato_sdk!r}). Senza una quarantena "
        f"non c'e' nessun «chi» da confrontare, e questo banco non ha "
        f"verificato niente. Riformula il claim invece di rilassare l'assert.\n"
        f"    uscita CLI: rc={proc.returncode} out={proc.stdout[-400:]!r}")

    chi_sdk = lato_sdk[0]
    chi_cli, db_visti = _chi_dalla_cli(tmp_path / "cli")

    assert chi_cli is not None, (
        f"la porta CLI non ha lasciato un fatto quarantinato: il confronto "
        f"non e' possibile e l'altra cella non e' interpretabile.\n"
        f"    rc={proc.returncode}  db visti={db_visti!r}\n"
        f"    out={proc.stdout[-500:]!r}\n    err={proc.stderr[-500:]!r}")

    assert chi_cli == chi_sdk, (
        f"LE DUE PORTE DIVERGONO GIA' SU UN RAMO CHE NON PASSA DAGLI AGITO "
        f"(SDK {chi_sdk!r} · CLI {chi_cli!r}): allora il banco sta misurando "
        f"due AMBIENTI diversi, non una differenza di codice, e il verdetto "
        f"dell'altra cella non vale. Si aggiusta questo prima di leggere "
        f"quello.")


def test_un_caso_che_PASSA_dagli_agito_deve_dare_lo_stesso_nome_e_oggi_NO(
        tmp_path) -> None:
    """IL RED. Stesso claim, stessa fonte, due porte, due nomi diversi.

    La promessa che l'utente capisce, e che non dipende da come e' fatto un
    campo: **chi ha fermato il mio fatto ha lo stesso nome, comunque io lo
    abbia scritto.** Oggi due porte su tre dicono il layer e la riga di comando
    dice `gate`.

    ⚠️ GUARDIA CONTRO IL VUOTO: se il layer che l'SDK riporta e' uno di quelli
    che NON passano dagli agito, la trappola non si e' armata e la cella lo
    DICE invece di passare — sarebbe un verde ottenuto misurando il ramo
    sbagliato.
    """
    fonte = ("verbale: la coda aveva 500 elementi\n"
             "rettifica: la coda aveva 540 elementi\n")
    claim = "La coda ha 540 elementi (rettifica del fatto 7c1a9e02)."

    proc = _dalla_riga_di_comando(tmp_path / "cli", claim, fonte)
    mem, ricevuta = _dall_sdk(tmp_path / "sdk", claim, fonte)

    sid = ricevuta.get("id") or ricevuta.get("fact_id") or ""
    lato_sdk = _quarantined_by(Path(mem.semantic.db_path), sid) if sid else None
    strati = [str(w.get("layer", "?"))
              for w in (ricevuta.get("warnings") or []) if isinstance(w, dict)]

    assert lato_sdk is not None and lato_sdk[1] in ("quarantined", "rejected"), (
        f"CONTROLLO POSITIVO SPENTO: dall'SDK questo caso NON e' stato "
        f"fermato (letto {lato_sdk!r}, layer {strati!r}), quindi non c'e' "
        f"nessun «chi» da confrontare fra le due porte e questa cella non ha "
        f"misurato niente.\n"
        f"    uscita CLI: rc={proc.returncode} out={proc.stdout[-400:]!r}")

    chi_sdk = lato_sdk[0]
    assert chi_sdk not in _NON_PASSANO_DA_AGITO, (
        f"TRAPPOLA NON ARMATA: l'SDK ha risposto {chi_sdk!r}, che e' un ramo "
        f"che NON passa da `agito` — su quei rami le due porte concordano gia' "
        f"e un verde qui non direbbe niente sul difetto. Serve un caso fermato "
        f"da un layer della lista agito (L3 · L4.1 · SOURCE_TRUST · "
        f"L4-skipped). Layer visti: {strati!r}."
    )

    chi_cli, db_visti = _chi_dalla_cli(tmp_path / "cli")

    assert chi_cli is not None, (
        f"la porta CLI non ha lasciato un fatto quarantinato da leggere: "
        f"rc={proc.returncode}  db visti={db_visti!r}\n"
        f"    out={proc.stdout[-600:]!r}\n    err={proc.stderr[-600:]!r}")

    assert chi_cli == chi_sdk, (
        f"LO STESSO CLAIM LASCIA DUE NOMI DIVERSI:\n"
        f"    porta SDK -> {chi_sdk!r}   (layer visti: {strati!r})\n"
        f"    porta CLI -> {chi_cli!r}\n"
        f"  La riga di comando passa `agito=[]` nel ramo `downgrade` dove "
        f"l'SDK passa i layer bloccanti, quindi `chi_ha_quarantinato` cade "
        f"sull'ultima riga e scrive l'etichetta generica. Chi legge domani un "
        f"fatto scritto da qui non puo' sapere chi lo ha fermato — e "
        f"un'etichetta generica si legge come un'assenza."
    )
