import sys
sys.path.insert(0, "C:/Users/aurel/Code/HippoAgent")
import verimem, verimem.mcp_server as S, os, glob
print("MARK verimem importato da: " + str(verimem.__file__))
print("MARK mcp_server importato da: " + str(S.__file__))
print("MARK versione: " + str(getattr(verimem, "__version__", "n/d")))
# il filtro esiste in QUALCHE forma nel pacchetto importato?
import subprocess
base = os.path.dirname(verimem.__file__)
hit = [p for p in glob.glob(base + "/**/*.py", recursive=True)
       if "HIPPO_EXPOSE_TOOLS" in open(p, encoding="utf-8", errors="replace").read()]
print("MARK file del PACCHETTO IMPORTATO che leggono HIPPO_EXPOSE_TOOLS: " + str(len(hit)))
for h in hit[:4]: print("MARK   " + h)
