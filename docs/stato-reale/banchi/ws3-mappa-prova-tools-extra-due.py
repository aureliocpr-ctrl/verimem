"""Due correzioni al giro precedente, entrambe mie.

1. `_enabled(name)` antepone da sé `HIPPO_ENABLE_`: chiamarla con
   `_enabled("HIPPO_ENABLE_SHELL")` cerca `HIPPO_ENABLE_HIPPO_ENABLE_SHELL`.
   Il nome giusto è breve: `_enabled("shell")`. Rifatto, con anche il ramo
   `HIPPO_DISABLE_*` che il codice prevede.
2. Le operazioni sul filesystem rifiutavano **anche il caso buono**, perché la
   radice permessa è la data dir e il mio tmp ne era fuori: `ENGRAM_DATA_DIR`
   non isola, vince `HIPPO_DATA_DIR`. Rifatto puntando la data dir al tmp, così
   il controllo positivo può accendersi — e lo store di casa resta intoccato.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-tx2-"))
os.environ["HIPPO_DATA_DIR"] = str(tmp)
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ["VERIMEM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENABLE_SHELL", None)
from verimem import tools_extra as TX  # noqa: E402

print("=== _enabled col NOME BREVE (la funzione antepone HIPPO_ENABLE_)")
print("  _enabled('shell', False)  senza variabile:", TX._enabled("shell", False))
os.environ["HIPPO_ENABLE_SHELL"] = "1"
print("  con HIPPO_ENABLE_SHELL=1:", TX._enabled("shell", False))
os.environ["HIPPO_ENABLE_SHELL"] = "yes"
print("  con HIPPO_ENABLE_SHELL=yes:", TX._enabled("shell", False))
os.environ["HIPPO_ENABLE_SHELL"] = "0"
print("  con HIPPO_ENABLE_SHELL=0:", TX._enabled("shell", False))
os.environ.pop("HIPPO_ENABLE_SHELL", None)
os.environ["HIPPO_DISABLE_FS"] = "1"
print("  default True ma HIPPO_DISABLE_FS=1:", TX._enabled("fs", True),
      "(il freno vince sul default)")
os.environ.pop("HIPPO_DISABLE_FS", None)
print("  default True senza freni:", TX._enabled("fs", True))

print("\n=== _fs_roots con la data dir sul tmp")
radici = TX._fs_roots()
print("  radici:", [str(r) for r in radici])
print("  il tmp e' fra le radici:", any(str(tmp) in str(r) for r in radici))

print("\n=== fs_*: ora il CASO BUONO puo' accendersi")
dentro = tmp / "dentro.txt"
dentro.write_text("il canone e' 5900 euro\n", encoding="utf-8")
r = TX.fs_read_file(str(dentro))
print("  fs_read_file(dentro):", "ok=" + str(r.ok), repr(str(r.output)[:40]))
print("  fs_read_file(FUORI):", str(TX.fs_read_file(
    str(pathlib.Path.home() / "qualsiasi.txt")))[:80])
(tmp / ".env").write_text("SECRET=1\n", encoding="utf-8")
print("  fs_read_file('.env' DENTRO la radice ma sensibile):",
      str(TX.fs_read_file(str(tmp / ".env")))[:88])
(tmp / ".env~").write_text("SECRET=1\n", encoding="utf-8")
print("  fs_read_file('.env~' la variante di backup):",
      str(TX.fs_read_file(str(tmp / ".env~")))[:88])
w = TX.fs_write_file(str(tmp / "nuovo.txt"), "ciao")
print("  fs_write_file(dentro):", "ok=" + str(w.ok), str(w.output)[:40])
print("  fs_write_file(append=True):",
      "ok=" + str(TX.fs_write_file(str(tmp / "nuovo.txt"), " ancora", True).ok))
print("  contenuto finale:", repr((tmp / "nuovo.txt").read_text(encoding="utf-8")))
ld = TX.fs_list_dir(str(tmp))
print("  fs_list_dir(dentro):", "ok=" + str(ld.ok), str(ld.output)[:70])
sf = TX.fs_search_files("*.txt")
print("  fs_search_files('*.txt') [relativo]:", "ok=" + str(sf.ok), str(sf.output)[:70])
sf2 = TX.fs_search_files("*.txt", "canone")
print("  fs_search_files('*.txt', contains='canone'):", "ok=" + str(sf2.ok),
      str(sf2.output)[:70])
sf3 = TX.fs_search_files("*.txt", "parola-che-non-c-e")
print("  fs_search_files(contains=parola assente):", "ok=" + str(sf3.ok),
      repr(str(sf3.output)[:40]))
print("  fs_read_file con max_bytes=5:", repr(str(TX.fs_read_file(str(dentro), 5).output)))

print("\n=== gli strumenti esposti all'agente")
for nome in ("extra_tools", "all_tools"):
    try:
        t = getattr(TX, nome)()
        nomi = [getattr(x, "name", x) for x in (t.values() if isinstance(t, dict) else t)]
        print(f"  {nome}(): {len(nomi)} -> {nomi}")
    except Exception as e:  # noqa: BLE001
        print(f"  {nome} -> {type(e).__name__}: {str(e)[:80]}")

print("\n=== _init_pyautogui_safety e gli strumenti del desktop: NON li eseguo")
print("  (nessun click, nessun tasto, nessuna schermata: e' il desktop di Aurelio)")
print("  _init_pyautogui_safety esiste:", hasattr(TX, "_init_pyautogui_safety"))
for n in ("desktop_click", "desktop_type", "desktop_key", "desktop_screenshot"):
    print(f"  {n} esiste: {hasattr(TX, n)}")
