"""Genera l'inventario delle funzioni di cli.py / tui.py / doctor.py.

Solo LETTURA: nessun import del prodotto, nessun pytest, nessun modello — il
vincolo di Aurelio delle 12:37 («sto pure giocando non mi saturate tutto»).

Criterio di conteggio DICHIARATO: una riga che combacia con `^\\s*def ` o
`^\\s*async def `, a qualunque indentazione. Le funzioni annidate dentro il
corpo di un'altra ci sono; le lambda no.

La colonna «nominata nei test» si ricava leggendo tests/ UNA volta sola e
cercandoci il nome. Ha un limite che va scritto e non nascosto: per un nome raro
(`_stores_illeggibili`) è informativa, per uno comune (`main`, `run`, `add`) non
discrimina — quelle righe portano «nome troppo comune» invece di un conteggio
che sembrerebbe una misura.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RADICE = Path(r"C:\Users\aurel\Code\_ws7_tmp_main")
USCITA = RADICE / "docs" / "stato-reale" / "mappa"
FILE = ["cli", "tui", "doctor"]

_DEF = re.compile(r"^(\s*)(?:async\s+)?def\s+(\w+)\s*\(")
_CLASSE = re.compile(r"^class\s+(\w+)")
_DECOR = re.compile(r"@(\w+)\.command\(\s*(?:name\s*=\s*)?[\"']?([\w-]*)")
# nomi cosi' comuni che cercarli nei test non discrimina
COMUNI = {
    "main", "run", "add", "get", "set", "show", "list", "close", "start", "stop",
    "compose", "v", "_set", "wrapper", "inner", "callback", "key", "value",
    "on_mount", "cb", "fn", "f", "go", "now", "check",
}


def testi_dei_test() -> str:
    pezzi = []
    for f in sorted((RADICE / "tests").rglob("test_*.py")):
        try:
            pezzi.append(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    return "\n".join(pezzi)


def quante_volte(corpo: str, nome: str) -> int:
    return len(re.findall(rf"\b{re.escape(nome)}\b", corpo))


def genera(nome_file: str, corpo_test: str) -> tuple[int, int]:
    sorgente = (RADICE / "verimem" / f"{nome_file}.py").read_text(encoding="utf-8")
    righe = sorgente.splitlines()
    classe_corrente = ""
    comando_pendente = ""
    voci: list[dict] = []
    for n, riga in enumerate(righe, 1):
        mc = _CLASSE.match(riga)
        if mc:
            classe_corrente = mc.group(1)
            continue
        md = _DECOR.search(riga)
        if md:
            comando_pendente = md.group(2) or "(dal nome della funzione)"
            continue
        m = _DEF.match(riga)
        if not m:
            continue
        indent, nome = len(m.group(1)), m.group(2)
        if indent == 0:
            classe_corrente = ""
        # che cos'e'
        if comando_pendente:
            genere = f"comando Typer `{comando_pendente}`"
            comando_pendente = ""
        elif classe_corrente and indent > 0:
            genere = f"metodo di `{classe_corrente}`"
        elif indent > 0:
            genere = "funzione annidata"
        elif nome.startswith("_"):
            genere = "helper privato"
        else:
            genere = "funzione pubblica del modulo"
        # nei test
        if nome in COMUNI or len(nome) <= 3:
            nei_test = "— *nome troppo comune: cercarlo non discrimina*"
        else:
            q = quante_volte(corpo_test, nome)
            if q == 0:
                nei_test = "**nessuna occorrenza** in `tests/`"
            elif q > 50:
                # Un conteggio altissimo e' la firma di un nome comune, non di
                # una copertura: `status` da 2136 non e' questa funzione. Il
                # numero resta scritto — nascondere un dato vero sarebbe peggio —
                # ma con l'avvertenza accanto, perche' letto da solo inganna.
                nei_test = f"**{q}** occorrenze — *troppe per essere questa funzione: il nome è comune*"
            else:
                nei_test = f"**{q}** occorrenze in `tests/`"
        voci.append({"n": nome, "riga": n, "genere": genere, "test": nei_test})

    fuori = [
        f"# Inventario delle funzioni — `verimem/{nome_file}.py`",
        "",
        "> ws7 «Iris». Accompagna [CLI-claims.md](CLI-claims.md), che giudica la",
        "> superficie che l'utente tocca (comandi, opzioni, diagnosi). Questo file è",
        "> un **inventario**, non un giudizio: elenca ogni funzione e dice se un test",
        "> la nomina.",
        "",
        "⚠️ **Criterio di conteggio, dichiarato**: una riga che combacia con",
        "`^\\s*def ` o `^\\s*async def `, a qualunque indentazione — le funzioni",
        "annidate ci sono, le lambda no.",
        "",
        "⚠️ **La colonna «prova»**: `NON MISURATO oggi (macchina in uso)` — Aurelio,",
        "09/09 12:37, *«sto pure giocando non mi saturate tutto»*. Nessun pytest,",
        "nessuna CLI, nessun modello: questo file è scritto **leggendo**.",
        "",
        "⚠️ **La colonna «nei test» è un indizio, non una copertura**: conta le",
        "occorrenze del nome nei file `tests/`. Per un nome raro è informativa; per",
        "uno comune (`main`, `run`, `add`) non discrimina, e lì la riga lo dice",
        "invece di esibire un numero che sembrerebbe una misura.",
        "",
        f"**{len(voci)} funzioni.**",
        "",
        "| n | funzione | riga | che cos'è | nei test | prova |",
        "|---|---|---|---|---|---|",
    ]
    muti = 0
    for i, v in enumerate(voci, 1):
        if "nessuna occorrenza" in v["test"]:
            muti += 1
        fuori.append(
            f"| {i} | `{v['n']}` | {v['riga']} | {v['genere']} | {v['test']} | "
            f"NON MISURATO oggi (macchina in uso) |"
        )
    fuori += [
        "",
        f"**Nomi che non compaiono in nessun file di `tests/`: {muti} su {len(voci)}.**",
        "Non è una misura di copertura — un helper privato può essere esercitato",
        "attraverso il comando che lo chiama senza che il suo nome compaia mai. È",
        "l'indizio più economico disponibile senza eseguire niente.",
        "",
    ]
    (USCITA / f"{nome_file}.md").write_text("\n".join(fuori), encoding="utf-8")
    return len(voci), muti


def main() -> int:
    corpo = testi_dei_test()
    # controllo positivo: un nome che DEVE risultare presente nei test
    if quante_volte(corpo, "run_doctor") == 0:
        print("!! righello cieco: 'run_doctor' non compare nei test letti.")
        return 2
    # e la faccia negativa
    if quante_volte(corpo, "questa_funzione_non_esiste_davvero") != 0:
        print("!! righello compiacente.")
        return 2
    print("controllo positivo (2 facce): 'run_doctor' VISTO · inventato RIFIUTATO")
    tot = mut = 0
    for f in FILE:
        t, m = genera(f, corpo)
        print(f"{f}.md: {t} funzioni, {m} senza occorrenze nei test")
        tot += t
        mut += m
    print(f"TOTALE: {tot} funzioni, {mut} senza occorrenze nei test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
