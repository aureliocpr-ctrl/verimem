r"""Un client «senza torch» esiste davvero? Chi tira dentro la libreria, e a quale passo.

@lead-audit propone la combinazione che conta per «8 agenti»: UN daemon con torch e il
giudice, e CLIENT che non importano torch. Predizione sua: privata del client <=60 MB,
daemon ~2,4 GB ⇒ 8 agenti ~2,9 GB contro ~19 GB.

⚠️ **Ma quella predizione ha un presupposto non verificato**: che un client POSSA non
importare torch. Se il server MCP di un agente lo tira dentro per l'embedding o per il
recall, il «client leggero» non esiste finche' non si sposta anche quello — e il pavimento
da spostare nel daemon e' un altro, piu' grande.

⇒ Questo banco misura **chi** importa torch e **a quale passo**. Costa quattro import,
non un daemon.

📌 **PREDIZIONE, scritta prima di eseguire**::

    `import verimem`              predico NO torch   (il codice dichiara «imports
                                                      transformers lazily»)
    `import verimem.mcp_server`   predico SI' torch  (l'embedder del recall)
    una scrittura SENZA fonte     predico SI' torch  (l'embedding del fatto)
    un recall                     predico SI' torch

⇒ Se ho ragione, il «client senza torch» **non esiste oggi** su nessuna superficie utile,
e la combinazione T4.1+T4.2 richiede prima di spostare **l'embedder**, non solo il
giudice. ⇒ Se ho torto e il client resta pulito fino al giudizio, la predizione del piano
regge e la strada e' libera.

I PASSI, ognuno misurato subito dopo l'import, nello stesso processo::

    ①  interprete nudo
    ②  import verimem
    ③  import verimem.mcp_server
    ④  una scrittura SENZA fonte (nessun giudice coinvolto)
    ⑤  un recall

🔑 **Il segnale non e' la memoria, e' `sys.modules`**: la RAM dice quanto costa, non CHI
l'ha chiesto. Si guarda se `torch` compare fra i moduli caricati, e **quale import ce
l'ha messo** — cosi' chi legge sa dove intervenire, non solo che c'e' un problema.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-chi-importa-torch-nel-client.py <venv>
"""
import os
import subprocess
import sys

if os.environ.get("_WS5_PULITO") != "1":
    # il filtro DENTRO lo script: uno nel comando puo' saltare (tre misure falsate oggi)
    if len(sys.argv) < 2:
        print("uso: python %s <venv>" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        print("  🔴 venv assente: %s" % venv)
        raise SystemExit(1)
    import tempfile
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env.update({"_WS5_PULITO": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "HIPPO_DATA_DIR": tempfile.mkdtemp(prefix="ws5_torch_")})
    raise SystemExit(subprocess.run([py, "-u", os.path.abspath(__file__)] + sys.argv[1:],
                                    env=env).returncode)

import ctypes
import ctypes.wintypes as wt
import time


class _PMCEX(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


def mem():
    c = _PMCEX(); c.cb = ctypes.sizeof(_PMCEX)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    h = ctypes.windll.kernel32.GetCurrentProcess()
    fn = ctypes.windll.kernel32.K32GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMCEX), wt.DWORD]
    fn.restype = wt.BOOL
    if not fn(h, ctypes.byref(c), c.cb):
        raise OSError("GetProcessMemoryInfo err=%d" % ctypes.windll.kernel32.GetLastError())
    return c.WorkingSetSize / 1048576.0, c.PrivateUsage / 1048576.0


def stato():
    """(torch caricato?, transformers caricato?, quanti moduli)"""
    return ("torch" in sys.modules, "transformers" in sys.modules, len(sys.modules))


righe = []


_MODULI_AL_PASSO = []


def passo(nome, fn):
    t = time.time()
    esito = ""
    try:
        esito = fn() or ""
    except Exception as e:
        esito = "errore %s: %s" % (type(e).__name__, str(e)[:40])
    tc, tr, n = stato()
    r, p = mem()
    _MODULI_AL_PASSO.append(list(sys.modules))
    righe.append((nome, tc, tr, n, r, p, time.time() - t, esito))


passo("① interprete nudo", lambda: "")
passo("② import verimem", lambda: __import__("verimem") and "")
passo("③ import verimem.mcp_server",
      lambda: __import__("verimem.mcp_server", fromlist=["x"]) and "")


def _scrivi_senza_fonte():
    from verimem.anti_confab_gate import run_validation_gate
    g = run_validation_gate(proposition="Il deploy di ieri e' andato a buon fine.",
                            verified_by=None, topic=None, agent=None)
    return "action=%s" % getattr(g, "action", "?")


passo("④ gate SENZA fonte", _scrivi_senza_fonte)

# CHI sono i moduli che entrano al passo piu' caro: senza questo si sa CHE pesa,
# non COSA spostare.
_prima = set(_MODULI_AL_PASSO[1])       # dopo `import verimem`
_dopo = set(_MODULI_AL_PASSO[2])        # dopo `import verimem.mcp_server`
#: ⚠️ i moduli si filtrano, o l'elenco NON fa riconoscere il colpevole: la prima
#: versione stampava i primi 24 in ordine alfabetico e mostrava `_ast`, `_bisect`,
#: `_blake2`... cioe' la stdlib in C. Chi legge deve vedere COSA spostare, non che
#: Python ha dei moduli interni.
_tutti = {m.split(".")[0] for m in (_dopo - _prima)}
_stdlib = set(getattr(sys, "stdlib_module_names", ()))
_nuovi = sorted(m for m in _tutti
                if not m.startswith("_") and m not in _stdlib)

print("  %-28s %-7s %-8s %7s %9s %11s %s"
      % ("passo", "torch", "transf.", "moduli", "RSS MB", "privata MB", "durata"))
print("  " + "-" * 88)
for nome, tc, tr, n, r, p, d, esito in righe:
    print("  %-28s %-7s %-8s %7d %9.1f %11.1f %6.1fs %s"
          % (nome, "SI" if tc else "no", "SI" if tr else "no", n, r, p, d, esito[:22]))

# quando entra torch: il primo passo che lo mostra
primo = next((i for i, x in enumerate(righe) if x[1]), None)
print("\n=== IL CLIENT PUO' RESTARE SENZA TORCH? ===")
max_priv = max(x[5] for x in righe)
if primo is None:
    print("  ✅ torch NON entra in nessun passo: la mia predizione («il server MCP lo")
    print("     importa per l'embedder») e' FALSIFICATA.")
    # (!) E QUI IL VERDETTO NON PUO' FERMARSI. La prima versione diceva «allora un
    # client <=60 MB e' raggiungibile» guardando SOLO `torch` in sys.modules — e
    # stampava, nella riga sopra, 682 MB di privata. Un verdetto che legge un campo
    # e ignora quello accanto e' il difetto che questi banchi esistono per trovare.
    max_rss = max(x[4] for x in righe)
    if max_priv > 60 or max_rss > 60:
        print("")
        print("  🔴 MA IL CLIENT PESA GIA' QUALCOSA SENZA TORCH, e i due righelli")
        print("     danno due verdetti diversi — vanno letti INSIEME:")
        print("       RSS     %7.1f MB   (quanto sta in RAM fisica)   -> fattore %.1f"
              % (max_rss, max_rss / 60))
        print("       privata %7.1f MB   (quanto il sistema riserva)  -> fattore %.1f"
              % (max_priv, max_priv / 60))
        print("     ⇒ contro i «<=60 MB» del piano: la predizione manca di poco")
        print("       sull'RSS e di molto sulla privata. Su 8 client fa %.1f GB"
              % (8 * max_rss / 1024))
        print("       di RAM fisica contro %.1f GB di commit." % (8 * max_priv / 1024))
        print("     ⇒ E la causa NON e' torch: spostare il giudice nel daemon non")
        print("       basta, il pavimento del client e' un altro e va nominato.")
        print("")
        print("  moduli top-level che entrano al passo piu' caro (%d nuovi):" % len(_nuovi))
        print("     %s" % ", ".join(_nuovi[:24]))
        if len(_nuovi) > 24:
            print("     ...e altri %d" % (len(_nuovi) - 24))
    else:
        print("  🟢 e il client resta sotto i 60 MB: la predizione regge.")
else:
    nome = righe[primo][0]
    prima = righe[primo - 1][5] if primo else 0.0
    dopo = righe[primo][5]
    print("  🔴 TORCH ENTRA A «%s»: la privata passa da %.1f a %.1f MB (+%.1f)."
          % (nome, prima, dopo, dopo - prima))
    print("  ⇒ Un client «senza torch» NON esiste oggi su questa superficie: prima del")
    print("     giudice va spostato CIO' CHE LO IMPORTA a quel passo. La predizione")
    print("     «client <=60 MB» vale solo dopo quello spostamento, non prima.")
