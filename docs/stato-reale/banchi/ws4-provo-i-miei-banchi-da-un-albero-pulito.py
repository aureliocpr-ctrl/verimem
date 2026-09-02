# -*- coding: utf-8 -*-
"""IL CONTROLLO CIECO APPLICATO AI MIEI: eseguo i miei banchi da un WORKTREE
PULITO creato da origin/main, e conto gli EXIT.

Perche' un worktree pulito e non la mia copia: la mia copia ha lo scratchpad
della mia sessione, i file untracked, i dump a mano. Un worktree da origin/main
ha SOLO cio' che ho consegnato — che e' esattamente quello che vede chiunque
altro. «Banco versionato» non e' «banco riproducibile»: il secondo si prova solo
lanciandolo da un albero che contiene solo il consegnato.

I banchi che caricano modelli non li eseguo adesso: servono uno slot di
inferenza (disciplina delle 21:40, slot presi da @ws7 e @ws5). Li marco «in coda»
e lo dico — un banco non eseguito NON prende la riga «EXIT=0».
"""
import glob
import os
import subprocess
import sys

WT = os.environ.get("WS4_WORKTREE", os.getcwd())  # il repo in cui gira,
# oppure WS4_WORKTREE=<path> per provarne un altro
PESANTI = ("transformers", "run_validation_gate", "local_grounding",
           "AutoModel", "torch")

banchi = sorted(glob.glob(os.path.join(WT, "docs/stato-reale/banchi/ws4-*.py")))
print(f"  {len(banchi)} banchi, eseguiti da {WT}\n")
print(f"  {'banco':<52} {'esito':<10} nota")
esiti = {}
for b in banchi:
    nome = os.path.basename(b)
    testo = open(b, encoding="utf-8").read()
    if any(k in testo for k in PESANTI):
        esiti[nome] = ("in-coda", "carica un modello: serve uno slot")
        print(f"  {nome[:50]:<52} {'IN CODA':<10} carica un modello")
        continue
    r = subprocess.run([sys.executable, "-c",
                        "exec(open(r'%s', encoding='utf-8').read())" % b],
                       cwd=WT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    coda = (r.stderr or r.stdout or "").strip().splitlines()
    ultima = coda[-1][:60] if coda else ""
    esiti[nome] = (f"EXIT={r.returncode}", ultima)
    print(f"  {nome[:50]:<52} {('EXIT=' + str(r.returncode)):<10} {ultima}")

ok = sum(1 for v in esiti.values() if v[0] == "EXIT=0")
coda = sum(1 for v in esiti.values() if v[0] == "in-coda")
print(f"\n  EXIT=0: {ok}  ·  in coda per uno slot: {coda}"
      f"  ·  ROTTI: {len(esiti) - ok - coda}")
