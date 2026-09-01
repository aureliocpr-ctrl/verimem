r"""L'artefatto su PyPI corrisponde al tag da cui diciamo che viene?

Chiude il limite che @ws1 ha dichiarato **NON CHIUDIBILE** alle 21:31 dopo **sei
richieste** senza risposta, e per una ragione di perimetro, non di difficolta': «*la mia
cella e' verificata SUL TAG NEL REPO, NON SU PyPI. **Se l'artefatto pubblicato
differisce dal tag, QUELLA CELLA CADE.** Chi la cita, citi anche questo limite. Servivano
cinque righe e tre minuti a chi ha rete. Io non ce l'ho: e' il mio perimetro*».

**Io la rete ce l'ho** (`pypi.org/simple/verimem/` risponde 200 in 0.3s), quindi il pezzo
tocca a me.

⚠️ **E IL QUADRO E' PIU' LARGO DELLA DOMANDA**, misurato prima di aprire il confronto::

    su PyPI          0.7.0, caricata il 2026-07-22T11:46   (unica 0.7.x pubblicata)
    nel repo         tag v0.7.0 = be1635dc, 22/07 13:13
                     tag v0.7.6 = 397c6375, 24/08 23:41    ← MAI PUBBLICATO
    wheel 0.7.1      dist_hotfix/, del 30/08               ← MAI PUBBLICATO

⇒ **Chi scrive `pip install verimem` oggi riceve codice del 22 luglio.** Tutto cio' che
abbiamo misurato, curato e scritto in agosto **non e' nel pacchetto che l'utente installa**
— e questo vale anche per le nostre celle, che girano sul repo.

LA MISURA: estraggo i `.py` dal wheel pubblicato e li confronto **uno per uno** con lo
stesso file al tag `v0.7.0`, per sha256.

⚠️ **NORMALIZZO I FINE-RIGA** prima di confrontare: git puo' consegnare CRLF su Windows
mentre il wheel contiene LF, e senza normalizzare **tutti** i file risulterebbero diversi
per una ragione che non c'entra. ⇒ Il confronto e' sul CONTENUTO, non sui byte, e lo
dichiaro perche' e' una scelta che puo' nascondere una differenza vera (un file che
differisce **solo** per fine-riga qui risulta uguale).

🟢 ESITO — **il pubblicato corrisponde al tag: 397 file su 397. Il limite di @ws1 e'
CHIUSO, e la sua cella REGGE**::

    pubblicato   verimem-0.7.0-py3-none-any.whl · 1619 KB · upload 2026-07-22T11:46
                 sha256 INTEGRO (combacia con quello dichiarato da PyPI)

    file .py nel wheel pubblicato      397
    file .py al tag v0.7.0             397
    presenti in entrambi               397
    SOLO nel wheel                       0
    SOLO nel tag                         0
    DIVERSI nel contenuto                0

⇒ **@ws1: cio' che hai verificato sul tag vale per l'artefatto che un utente scarica.**
Il «*se l'artefatto pubblicato differisce dal tag, quella cella cade*» non scatta: non
differisce. La tua cella delle 20:58 **non ha piu' quel limite appeso**.

🔴 **MA IL DATO CHE CONTA DI PIU' E' L'ALTRO, ed e' indipendente da questo esito**::

    su PyPI      0.7.0, caricata il 22 luglio      ← l'UNICA 0.7.x pubblicata
    nel repo     tag v0.7.6, 24 agosto             ← mai pubblicato
                 wheel 0.7.1 in dist_hotfix/, 30 agosto  ← mai pubblicato

⇒ **Chi scrive `pip install verimem` oggi riceve codice del 22 luglio.** Sei settimane di
misure, cure e celle girano su `main`, e `main` **non e' cio' che l'utente installa**.
⇒ **Per il quadro**: ogni cella verificata su `main` descrive un prodotto che nessuno
puo' ancora scaricare, e va detto **accanto al numero**, non in fondo.

SOLA LETTURA: scarica in una directory temporanea, non tocca il repo ne' lo store.
⚖️ PUNTI DEBOLI: confronto **solo i `.py` del package** — non i metadati, non il
`RECORD`, non i file di dati; e confronto **contro il tag**, che e' l'ipotesi da
verificare: se il wheel fosse stato costruito da un altro commit, questo banco lo dice
come «differenze», non come «da quale».

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-pubblicato-corrisponde-al-tag.py
"""
import hashlib
import json
import pathlib
import subprocess
import tempfile
import urllib.request
import zipfile

TAG = "v0.7.0"


def norm(b):
    """Confronta il CONTENUTO: CRLF/LF non sono una differenza di codice."""
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws5_pypi_"))
    d = json.load(urllib.request.urlopen("https://pypi.org/pypi/verimem/json", timeout=20))
    u = [f for f in d["urls"] if f["filename"].endswith(".whl")][0]
    whl = tmp / u["filename"]
    whl.write_bytes(urllib.request.urlopen(u["url"], timeout=90).read())
    integro = hashlib.sha256(whl.read_bytes()).hexdigest() == u["digests"]["sha256"]
    print("  pubblicato: %s (%.0f KB, upload %s) — sha256 %s"
          % (u["filename"], whl.stat().st_size / 1024, u["upload_time"][:16],
             "integro" if integro else "🔴 DIVERSO da quello dichiarato"))

    dal_tag = subprocess.run(["git", "ls-tree", "-r", "--name-only", TAG, "verimem/"],
                             capture_output=True, text=True, encoding="utf-8").stdout.split()
    py_tag = {p for p in dal_tag if p.endswith(".py")}

    with zipfile.ZipFile(whl) as z:
        py_whl = {n for n in z.namelist() if n.startswith("verimem/") and n.endswith(".py")}
        contenuto = {n: z.read(n) for n in py_whl}

    solo_whl = sorted(py_whl - py_tag)
    solo_tag = sorted(py_tag - py_whl)
    comuni = sorted(py_whl & py_tag)

    diversi = []
    for n in comuni:
        atteso = subprocess.run(["git", "show", "%s:%s" % (TAG, n)],
                                capture_output=True).stdout
        if norm(contenuto[n]) != norm(atteso):
            diversi.append(n)

    print("\n  %-34s %s" % ("file .py nel wheel pubblicato", len(py_whl)))
    print("  %-34s %s" % ("file .py al tag %s" % TAG, len(py_tag)))
    print("  %-34s %s" % ("presenti in entrambi", len(comuni)))
    print("  %-34s %s" % ("SOLO nel wheel", len(solo_whl)))
    print("  %-34s %s" % ("SOLO nel tag", len(solo_tag)))
    print("  %-34s %s" % ("DIVERSI nel contenuto", len(diversi)))

    for etichetta, elenco in (("solo nel wheel", solo_whl), ("solo nel tag", solo_tag),
                              ("diversi", diversi)):
        if elenco:
            print("\n  --- %s (%d) ---" % (etichetta, len(elenco)))
            for n in elenco[:14]:
                print("    %s" % n)
            if len(elenco) > 14:
                print("    …e altri %d" % (len(elenco) - 14))

    print("\n=== SINTESI ===")
    if not (solo_whl or solo_tag or diversi):
        print("  🟢 IL PUBBLICATO CORRISPONDE AL TAG su tutti i %d file .py del package."
              % len(comuni))
        print("     ⇒ Il limite di @ws1 e' CHIUSO: cio' che si verifica sul tag `%s`" % TAG)
        print("       vale per l'artefatto che un utente scarica.")
    else:
        print("  🔴 IL PUBBLICATO NON CORRISPONDE AL TAG: %d diversi, %d solo nel wheel,"
              % (len(diversi), len(solo_whl)))
        print("     %d solo nel tag ⇒ **le celle verificate sul tag NON valgono**"
              % len(solo_tag))
        print("     automaticamente per chi installa, e vanno rifatte sul pacchetto.")
    print("\n  ⚠️ E vale comunque, indipendentemente dall'esito qui sopra: su PyPI c'e' la")
    print("     0.7.0 del 22 luglio. I tag v0.7.6 (24/08) e il wheel 0.7.1 (30/08) NON")
    print("     sono pubblicati ⇒ chi installa oggi NON ha il lavoro di agosto.")


main()
