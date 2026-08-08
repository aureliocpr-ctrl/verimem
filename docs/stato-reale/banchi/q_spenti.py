import sys, os, inspect, importlib, pkgutil, re
sys.path.insert(0, "C:/Users/aurel/Code/HippoAgent")
VIETATE = ("load", "model", "judge", "encode", "embed", "daemon", "warm", "client", "connect",
           "spawn", "run", "start", "open", "index", "write", "save", "store", "delete", "main")
RX = re.compile(r'(?:getenv|environ\.get)\(\s*"((?:ENGRAM|HIPPO|VERIMEM)_[A-Z0-9_]+)"')
import verimem
risultati, errori, moduli = [], 0, 0
for mi in pkgutil.iter_modules(verimem.__path__):
    try:
        m = importlib.import_module("verimem." + mi.name)
    except Exception:
        continue
    moduli += 1
    for nome, fn in vars(m).items():
        if not (nome.startswith("_") and inspect.isfunction(fn)): continue
        if any(v in nome.lower() for v in VIETATE): continue
        try:
            sig = inspect.signature(fn)
            if any(p.default is inspect.Parameter.empty and
                   p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in sig.parameters.values()):
                continue
            src = inspect.getsource(fn)
        except Exception:
            continue
        flag = RX.search(src)
        if not flag: continue
        try:
            val = fn()
        except Exception as e:
            errori += 1; val = "ERR:" + type(e).__name__
        risultati.append((flag.group(1), mi.name + "." + nome, val))
print("MARK moduli importati: " + str(moduli) + "  predicati eseguiti: " + str(len(risultati)) + "  errori: " + str(errori))
print("MARK")
off = [r for r in risultati if r[2] is False or r[2] == 0 or r[2] == ""]
on = [r for r in risultati if r[2] is True]
altri = [r for r in risultati if r not in off and r not in on]
print("MARK === SPENTI ADESSO (predicato eseguito -> falso) : " + str(len(off)) + " ===")
for f, dove, v in sorted(off): print("MARK   OFF  " + f.ljust(38) + dove)
print("MARK === ACCESI : " + str(len(on)) + " ===")
for f, dove, v in sorted(on): print("MARK   ON   " + f.ljust(38) + dove)
print("MARK === VALORI (soglie/numeri) : " + str(len(altri)) + " ===")
for f, dove, v in sorted(altri): print("MARK   =    " + f.ljust(38) + str(v)[:22].ljust(24) + dove)
