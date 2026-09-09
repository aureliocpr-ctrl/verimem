"""Adegua le righe di una mappa al formato che il RIGHELLO DEL LEAD riconosce.

`scripts/mappa_completa.py` riconosce una riga quando la seconda colonna porta
`` `verimem/<file>.py:<riga>` `` seguito dal NOME QUALIFICATO fra backtick
(`Classe.metodo` o `funzione`). Le mie righe portavano il nome e la riga in
un'altra forma (`` `_fact_trust_line` (77) ``): il contenuto c'era, la forma no,
e il righello del lead contava **0 su 456**. Una misura che non ti riconosce non
è un'opinione sul tuo lavoro: è il numero che arriva ad Aurelio.

Tre modi di agganciare una riga, dal più forte al più debole, e ognuno è
dichiarato nell'output:
  1. nome + numero di riga nella cella      -> qualificato dalla riga esatta;
  2. solo il nome (senza numero)            -> qualificato se è univoco nel file;
  3. né l'uno né l'altro (le righe che misurano un RAMO: `gate_mode="reject"`,
     `ground=False`, …)                     -> il nome preso dal titolo della
     sezione (`## I RAMI di `Memory.add``), che è la funzione che quel ramo
     esercita davvero.
Le righe che restano senza aggancio vengono stampate: si guardano a mano.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

sorgente = pathlib.Path(sys.argv[1])
mappa = pathlib.Path(sys.argv[2])
rel = sys.argv[3]
scrivi = "--scrivi" in sys.argv

albero = ast.parse(sorgente.read_text(encoding="utf-8"))
per_riga: dict[int, str] = {}
per_nome: dict[str, list[tuple[str, int]]] = {}


def visita(nodo: ast.AST, prefisso: str) -> None:
    for figlio in ast.iter_child_nodes(nodo):
        if isinstance(figlio, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            qual = prefisso + figlio.name
            per_riga[figlio.lineno] = qual
            per_nome.setdefault(figlio.name, []).append((qual, figlio.lineno))
            visita(figlio, qual + ".")
        else:
            visita(figlio, prefisso)


visita(albero, "")
print(f"definizioni nel sorgente: {len(per_riga)}")

COPPIA = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`[^`|]{0,40}?\(?(?:[a-z_]+\.py:)?(\d{2,5})\)?")
# dentro una coppia di backtick, il primo identificatore: prende sia `nome`
# sia `nome(argomento=…)` — la seconda forma è quella che scrivo quando la riga
# misura una CHIAMATA e non solo la funzione.
SOLO_NOME = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)[^`]*`")


def risolvi(nome: str, num: int | None) -> tuple[str, int] | None:
    """Il qualificato per (nome, riga): prima la riga esatta, poi il nome."""
    if num is not None and num in per_riga:
        return per_riga[num], num
    cand = per_nome.get(nome.split(".")[-1]) or []
    if len(cand) == 1:
        return cand[0]
    if cand and num is not None:
        return min(cand, key=lambda c: abs(c[1] - num))
    return None


righe_out: list[str] = []
per_titolo = 0
agganciate = senza = 0
titolo_nomi: list[str] = []
for riga in mappa.read_text(encoding="utf-8").splitlines(keepends=True):
    if riga.startswith("#"):
        titolo_nomi = SOLO_NOME.findall(riga)
        righe_out.append(riga)
        continue
    if not riga.startswith("| ") or riga.startswith("|---") or riga.startswith("| # "):
        righe_out.append(riga)
        continue
    celle = riga.split("|")
    if len(celle) < 4:
        righe_out.append(riga)
        continue
    seconda = celle[2]
    if f"`{rel}:" in seconda:
        righe_out.append(riga)
        agganciate += 1
        continue
    trovati: list[tuple[str, int]] = []
    for nome, num in COPPIA.findall(seconda):
        r = risolvi(nome, int(num))
        if r:
            trovati.append(r)
    if not trovati:                                  # modo 2: solo il nome
        for nome in SOLO_NOME.findall(seconda):
            r = risolvi(nome, None)
            if r:
                trovati.append(r)
    if not trovati and titolo_nomi:                  # modo 3: dal titolo
        for nome in titolo_nomi:
            r = risolvi(nome, None)
            if r:
                trovati.append(r)
                per_titolo += 1
                break
    if trovati:
        visti: list[str] = []
        for qual, n in trovati:
            m = f"`{rel}:{n}` `{qual}`"
            if m not in visti:
                visti.append(m)
        celle[2] = " " + " · ".join(visti) + " —" + seconda
        righe_out.append("|".join(celle))
        agganciate += 1
    else:
        righe_out.append(riga)
        senza += 1
        print("  SENZA AGGANCIO:", seconda.strip()[:96])

print(f"agganciate {agganciate} (di cui {per_titolo} dal titolo della sezione) · senza {senza}")
if scrivi:
    mappa.write_text("".join(righe_out), encoding="utf-8")
    print("scritto:", mappa)
else:
    print("(prova secca: aggiungi --scrivi per applicare)")
