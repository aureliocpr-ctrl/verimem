"""Le liberate da `c857752e` tornano fermate dopo la cura del 2026-09-03?

    python docs/stato-reale/banchi/ws7-le-quindici-liberate-tornano-fermate.py <PADRE> <FIGLIO>

dove PADRE e FIGLIO sono due worktree:

    git worktree add --detach <PADRE>  ccab08b4
    git worktree add --detach <FIGLIO> c857752e

Il terzo braccio e' l'albero corrente: non serve un worktree, ed e' il punto —
si misura il codice che si sta per consegnare, non un commit gia' fatto.

⚡ NESSUN MODELLO: `ground_write=False`, la famiglia L1 e' lessicale.
⚠️ Store vivo in SOLA LETTURA (`mode=ro`).

━━ PERCHE' ESISTE, ED E' UN DEBITO MIO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il 2026-09-03 ho curato il rosso `33648de6` e ho consegnato dichiarando il
livello: «verificate le QUATTRO frasi della cella, NON tutte e 15 le liberate».
Quello e' un limite dichiarato, cioe' un DEBITO — e lo paga chi legge, che non
sa se le altre undici siano tornate a posto o no. Questo banco lo salda.

    braccio A   PADRE    `ccab08b4`  -> chi viene TRATTENUTO
    braccio B   FIGLIO   `c857752e`  -> di quelli, chi PASSA   (le liberate)
    braccio C   OGGI     l'albero    -> di quelle, chi torna FERMATA

━━ IL CONTROLLO POSITIVO, senza il quale il banco non vale ━━━━━━━━━━━━━━━━━━
Un banco che stampa «0 liberate» puo' dirlo perche' la cura funziona o perche'
non ha misurato niente. Percio' il braccio B DEVE trovarne almeno una: se ne
trova zero, il verdetto e' «non riproducibile» e il difetto e' del misuratore.
E il conteggio dei trattenuti dal padre deve essere > 0 per la stessa ragione.

━━ E LE DUE CLASSI NON SI CONFONDONO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Una liberata che torna fermata NON e' automaticamente un guadagno: la cura
`c857752e` esisteva per lasciar passare i fatti di TERZI veri (il verbale
d'ufficio, 6 su 7 fermati il 28/08). Percio' il banco stampa l'ELENCO, non solo
il conteggio: chi legge deve poter vedere QUALI frasi sono tornate fermate e
giudicare se erano self-claim o fatti veri. Un numero da solo qui mente in
entrambe le direzioni.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
#: quante proposizioni del corpus provare. L'A/B completo di ws3 ne conta
#: 17.428 in 356 s + 67 s; qui il default e' l'intero corpus e il limite si
#: passa da riga di comando solo per una prova rapida del banco stesso.
LIMITE = 0


def proposizioni(limite: int = 0) -> list[str]:
    """Le proposizioni del corpus vivo, in sola lettura.

    La colonna si CHIEDE allo schema invece di indovinarla: due store di questo
    progetto hanno nomi diversi, e un nome sbagliato qui darebbe zero righe
    senza errore — cioe' un banco verde che non ha misurato niente.
    """
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(facts)")]
        col = next((c for c in ("content", "proposition", "text", "fact")
                    if c in cols), None)
        if col is None:
            raise SystemExit(f"nessuna colonna testuale in facts: {cols}")
        sql = f"SELECT {col} FROM facts WHERE {col} IS NOT NULL AND {col} != ''"
        if limite:
            sql += f" LIMIT {int(limite)}"
        return [r[0] for r in con.execute(sql)]
    finally:
        con.close()


def verdetti(radice: Path, frasi: list[str]) -> list[tuple[str, str, list[str]]]:
    """Il gate DI QUELLA radice, in un processo a se'.

    Ripreso da `ws3-la-popolazione-che-la-garanzia-proteggeva.py`: un processo
    per commit (due versioni di `verimem` nello stesso interprete non si
    importano), i valori passati con ``repr()`` mai per interpolazione, e
    l'``assert`` sulla provenienza — che e' il controllo positivo del
    lanciatore: senza, `PYTHONPATH` fallisce in silenzio e si misura l'albero
    di oggi credendo di misurare il padre.
    """
    # ⚠️ LE FRASI PASSANO PER FILE, NON DENTRO `-c`. Il banco di ws3 le mette
    # nel codice con `repr()` e funziona benissimo con QUATTRO frasi; a 300 la
    # riga di comando supera il limite di Windows e si ottiene
    #     FileNotFoundError: [WinError 206] Nome del file o estensione troppo lunga
    # — un errore che parla di NOMI DI FILE mentre il guasto e' la LUNGHEZZA
    # DELL'ARGOMENTO, quindi manda a cercare nel posto sbagliato (misurato il
    # 2026-09-03 alle 20:26). ⇒ Un metodo provato su 4 casi non e' provato su
    # 17.428: la differenza non e' il tempo, e' che cambia il meccanismo.
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fh:
        json.dump(frasi, fh, ensure_ascii=False)
        percorso_frasi = fh.name
    r_radice, r_frasi_file = repr(str(radice)), repr(percorso_frasi)
    codice = (
        "import sys, json\n"
        "sys.path.insert(0, " + r_radice + ")\n"
        "import verimem\n"
        "assert " + r_radice + " in verimem.__file__, verimem.__file__\n"
        "from verimem.anti_confab_gate import run_validation_gate as g\n"
        "frasi = json.load(open(" + r_frasi_file + ", encoding='utf-8'))\n"
        "out = []\n"
        "for f in frasi:\n"
        "    try:\n"
        "        x = g(proposition=f, verified_by=[], topic=None, agent=None,"
        " source=None, ground_write=False)\n"
        "    except Exception:\n"
        "        continue\n"
        "    out.append((f, str(getattr(x, 'action', None)),"
        " [str((w or {}).get('layer') or '')"
        " for w in (getattr(x, 'warnings', None) or [])]))\n"
        "print(json.dumps(out, ensure_ascii=False))"
    )
    r = subprocess.run([sys.executable, "-c", codice], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       cwd=str(radice), timeout=3600)
    try:
        for riga in reversed(r.stdout.strip().splitlines()):
            if riga.startswith("["):
                return json.loads(riga)
        raise SystemExit(f"nessun esito da {radice}: {r.stderr.strip()[-400:]}")
    finally:
        Path(percorso_frasi).unlink(missing_ok=True)


def fermata(azione: str) -> bool:
    """Trattenuta = tutto cio' che NON e' un persist. Stessa definizione del
    banco C10 (`servito(e) = not stato.startswith('quarantin')`), scritta qui
    per esteso perche' un banco che eredita una definizione implicita e' un
    banco che misura la definizione di un altro."""
    return azione != "persist"


def main() -> None:
    if len(sys.argv) < 3:
        print("  uso: python <questo file> <worktree-PADRE> <worktree-FIGLIO>")
        print("  (il terzo braccio e' l'albero corrente)")
        raise SystemExit(2)
    padre, figlio = Path(sys.argv[1]), Path(sys.argv[2])
    limite = int(sys.argv[3]) if len(sys.argv) > 3 else LIMITE
    oggi = Path(__file__).resolve().parents[3]

    frasi = proposizioni(limite)
    print(f"  proposizioni dal corpus vivo   : {len(frasi)}")
    if not frasi:
        raise SystemExit("  zero proposizioni: il banco non ha misurato niente")

    print(f"  braccio A (padre)  {padre}")
    va = verdetti(padre, frasi)
    trattenute = [f for f, a, _ in va if fermata(a)]
    print(f"  trattenute dal PADRE           : {len(trattenute)}")
    if not trattenute:
        raise SystemExit("  CONTROLLO POSITIVO SPENTO: il padre non trattiene "
                         "niente. Verdetto: non riproducibile, difetto MIO.")

    print(f"  braccio B (figlio) {figlio}")
    vb = verdetti(figlio, trattenute)
    liberate = [f for f, a, _ in vb if not fermata(a)]
    print(f"  LIBERATE dal figlio            : {len(liberate)}")
    if not liberate:
        # ⚠️ E QUI IL BANCO DEVE DIRE QUALE DELLE DUE COSE E' SUCCESSA, perche'
        # «zero liberate» ha due cause opposte e la prima versione le
        # confondeva: le liberate note sono 15 su 17.428 (0,086%), quindi su un
        # campione da 300 se ne attendono 0,26 e lo ZERO E' IL RISULTATO
        # NORMALE. Su un campione piccolo il verdetto giusto e' «campione
        # insufficiente», non «difetto del misuratore»: dirlo male manda a
        # cercare un guasto che non c'e' (successo il 2026-09-03 alle 20:28,
        # su questo stesso banco, a me che l'avevo appena scritto).
        attese = len(frasi) * 15 / 17428
        if attese < 3:
            raise SystemExit(
                f"  CAMPIONE INSUFFICIENTE, non un guasto: su {len(frasi)} "
                f"proposizioni le liberate attese sono {attese:.2f} (15 su "
                f"17.428 nel corpus intero). Rilancia SENZA limite.")
        raise SystemExit("  CONTROLLO POSITIVO SPENTO: il campione basterebbe "
                         f"({attese:.1f} attese) e non ne trova nessuna. "
                         "Verdetto: non riproducibile, difetto MIO.")

    print(f"  braccio C (oggi)   {oggi}")
    vc = verdetti(oggi, liberate)
    tornate = [f for f, a, _ in vc if fermata(a)]
    restano = [f for f, a, _ in vc if not fermata(a)]

    print()
    print(f"  ⇒ TORNATE FERMATE dalla cura   : {len(tornate)} su {len(liberate)}")
    print(f"  ⇒ restano liberate             : {len(restano)}")
    print()
    print("  --- TORNATE FERMATE (giudicare una per una: self-claim o vero?) ---")
    for f in tornate:
        print(f"    FERMATA  {f[:110]}")
    print()
    print("  --- RESTANO LIBERATE ---")
    for f in restano:
        print(f"    passa    {f[:110]}")
    print()
    print(f"  REGIME  padre={padre.name} figlio={figlio.name} oggi=albero "
          f"· ground_write=False · store mode=ro")
    fuori = Path(__file__).with_suffix(".json")
    fuori.write_text(json.dumps(
        {"proposizioni": len(frasi), "trattenute_dal_padre": len(trattenute),
         "liberate_dal_figlio": len(liberate),
         "tornate_fermate": len(tornate), "restano_liberate": len(restano),
         "elenco_tornate": tornate, "elenco_restano": restano},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  scritto {fuori}")


if __name__ == "__main__":
    main()
