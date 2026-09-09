"""`tools_extra.py` (47): filesystem, shell, rete, vision, desktop — cioè **le
capacità che possono fare danno**, e le guardie che ci stanno davanti.

⛔ **Quello che NON faccio, e lo dico prima**: non muovo il mouse, non premo
tasti, non scatto schermate del desktop di Aurelio, non accendo la shell
(`HIPPO_ENABLE_SHELL` resta spento e lo verifico), non chiamo LLM di visione,
non accendo la webcam, e non esco in rete verso l'esterno. Provo le **guardie**
— che sono pure — e i casi che devono essere **RIFIUTATI**: un rifiuto si misura
senza fare la cosa pericolosa.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-tx-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENABLE_SHELL", None)
os.environ.pop("HIPPO_ENABLE_DESKTOP", None)
from verimem import tools_extra as TX  # noqa: E402

print("=== _enabled: gli interruttori delle capacita' pericolose")
for nome in ("HIPPO_ENABLE_SHELL", "HIPPO_ENABLE_DESKTOP", "HIPPO_ENABLE_FS"):
    print(f"  _enabled({nome!r:22}, False) -> {TX._enabled(nome, False)}")
os.environ["HIPPO_PROVA_FLAG"] = "1"
print("  con la variabile a '1':", TX._enabled("HIPPO_PROVA_FLAG", False))
os.environ["HIPPO_PROVA_FLAG"] = "0"
print("  con la variabile a '0':", TX._enabled("HIPPO_PROVA_FLAG", True))
os.environ.pop("HIPPO_PROVA_FLAG", None)

print("\n=== _fs_roots: «STRICT — solo la data dir del progetto»")
radici = TX._fs_roots()
print("  radici permesse:", [str(r) for r in radici][:4])
print("  >>> la HOME dell'utente NON e' una radice:",
      not any(str(r).rstrip("\\/") == str(pathlib.Path.home()).rstrip("\\/")
              for r in radici))

print("\n=== _strip_editor_backup_suffixes: «.env~ deve valere come .env»")
for n in (".env~", ".env.bak", ".env.backup", ".env.swp", "id_rsa~",
          "normale.txt", ".env"):
    print(f"  {n!r:16} -> {TX._strip_editor_backup_suffixes(n)!r}")

print("\n=== _is_sensitive: i nomi che non si leggono")
casi = [pathlib.Path.home() / ".ssh" / "id_rsa",
        pathlib.Path.home() / ".ssh" / "id_rsa~",
        pathlib.Path.home() / ".aws" / "credentials",
        tmp / ".env",
        tmp / ".env.bak",
        tmp / "note.txt"]
for p in casi:
    print(f"  {str(p)[-40:]:42} -> sensibile: {TX._is_sensitive(p)}")

print("\n=== _is_within_any")
print("  dentro:", TX._is_within_any(tmp / "a" / "b.txt", [tmp]))
print("  fuori :", TX._is_within_any(pathlib.Path.home() / "segreto.txt", [tmp]))
print("  risalita con .. :",
      TX._is_within_any(tmp / ".." / ".." / "fuori.txt", [tmp]))

print("\n=== fs_read_file / fs_write_file / fs_list_dir / fs_search_files")
dentro = tmp / "dentro.txt"
dentro.write_text("il canone e' 5900 euro\n", encoding="utf-8")
print("  fs_read_file (dentro la radice):", str(TX.fs_read_file(str(dentro)))[:70])
print("  fs_read_file (FUORI, la HOME):",
      str(TX.fs_read_file(str(pathlib.Path.home() / "qualsiasi.txt")))[:90])
print("  fs_read_file (file sensibile .env):", end=" ")
(tmp / ".env").write_text("SECRET=1\n", encoding="utf-8")
print(str(TX.fs_read_file(str(tmp / ".env")))[:90])
print("  fs_read_file ('.env~', la variante del backup):",
      str(TX.fs_read_file(str(tmp / ".env~")))[:90])
print("  fs_write_file (dentro):", str(TX.fs_write_file(str(tmp / "nuovo.txt"), "ciao"))[:70])
print("  fs_write_file (FUORI):",
      str(TX.fs_write_file(str(pathlib.Path.home() / "mai.txt"), "x"))[:90])
print("  fs_list_dir (dentro):", str(TX.fs_list_dir(str(tmp)))[:80])
print("  fs_list_dir (FUORI):", str(TX.fs_list_dir(str(pathlib.Path.home())))[:90])
print("  fs_search_files('*.txt'):", str(TX.fs_search_files(str(tmp / "*.txt")))[:80])

print("\n=== shell_run: DEVE essere spenta (non la accendo)")
print("  HIPPO_ENABLE_SHELL nell'ambiente:", os.environ.get("HIPPO_ENABLE_SHELL"))
print("  shell_run('echo ciao') ->", str(TX.shell_run("echo ciao"))[:110])

print("\n=== le guardie SSRF (nessuna connessione: solo il giudizio)")
for ip in ("127.0.0.1", "::1", "10.0.0.5", "192.168.1.1", "172.16.0.1",
           "169.254.169.254", "224.0.0.1", "0.0.0.0", "8.8.8.8",
           "93.184.216.34", "non-un-ip"):
    print(f"  _ip_is_blocked({ip!r:18}) -> {TX._ip_is_blocked(ip)}")
print("  >>> 169.254.169.254 (metadati cloud) bloccato:",
      TX._ip_is_blocked("169.254.169.254"))
print("  >>> un IP pubblico NON e' bloccato:", not TX._ip_is_blocked("8.8.8.8"))
print("  _host_is_allowlisted('localhost'):", TX._host_is_allowlisted("localhost"))
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
print("  con OLLAMA_HOST=127.0.0.1: _host_is_allowlisted('127.0.0.1'):",
      TX._host_is_allowlisted("127.0.0.1"))
os.environ.pop("OLLAMA_HOST", None)
for h in ("localhost", "127.0.0.1", "169.254.169.254", "metadata.google.internal"):
    try:
        print(f"  _is_blocked_host({h!r:26}) -> {TX._is_blocked_host(h)}")
    except Exception as e:  # noqa: BLE001
        print(f"  _is_blocked_host({h!r:26}) -> {type(e).__name__}: {str(e)[:50]}")

print("\n=== web_fetch verso una destinazione BLOCCATA (non esce in rete)")
for url in ("http://127.0.0.1:8080/x", "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.1/"):
    print(f"  web_fetch({url[:38]!r:40}) -> {str(TX.web_fetch(url))[:80]}")

print("\n=== _strip_html + _Stripper: HTML→testo con il parser della libreria")
html = ("<html><head><style>body{color:red}</style><script>alert('x')</script></head>"
        "<body><h1>Titolo</h1><p>Il canone e' <b>5900</b> euro.</p></body></html>")
testo = TX._strip_html(html)
print("  testo:", repr(testo[:80]))
print("  >>> lo script NON finisce nel testo:", "alert" not in testo)
print("  >>> lo stile NON finisce nel testo:", "color:red" not in testo)

print("\n=== _parse_ddg su una pagina finta (nessuna rete)")
finta = ('<div class="result"><a class="result__a" href="https://esempio.it/uno">'
         'Titolo uno</a><a class="result__snippet">Riassunto uno</a></div>'
         '<div class="result"><a class="result__a" href="https://esempio.it/due">'
         'Titolo due</a><a class="result__snippet">Riassunto due</a></div>')
print("  _parse_ddg(finta, 5):", str(TX._parse_ddg(finta, 5))[:150])

print("\n=== _resolve_vision_model (nessuna chiamata al modello)")
for prov in ("anthropic", "ollama", "openai", "provider-inventato"):
    try:
        print(f"  _resolve_vision_model({prov!r:22}) -> {TX._resolve_vision_model(prov)}")
    except Exception as e:  # noqa: BLE001
        print(f"  _resolve_vision_model({prov!r:22}) -> {type(e).__name__}: {str(e)[:60]}")

print("\n=== _read_image_to_b64_and_media_type su un file che non e' un'immagine")
try:
    print(" ", str(TX._read_image_to_b64_and_media_type(str(dentro)))[:100])
except Exception as e:  # noqa: BLE001
    print(" ", type(e).__name__, str(e)[:100])

print("\n=== all_tools / extra_tools: cosa viene ESPOSTO all'agente")
try:
    ex = TX.extra_tools()
    print("  extra_tools():", len(ex), "->",
          [getattr(t, "name", t) for t in (ex.values() if isinstance(ex, dict) else ex)][:10])
except Exception as e:  # noqa: BLE001
    print("  extra_tools ->", type(e).__name__, str(e)[:80])
try:
    at = TX.all_tools()
    nomi = [getattr(t, "name", t) for t in (at.values() if isinstance(at, dict) else at)]
    print("  all_tools():", len(nomi), "->", nomi[:12])
    print("  >>> gli strumenti del desktop sono esposti?",
          [n for n in nomi if "desktop" in str(n)])
    print("  >>> la shell e' esposta?", [n for n in nomi if "shell" in str(n)])
except Exception as e:  # noqa: BLE001
    print("  all_tools ->", type(e).__name__, str(e)[:80])
