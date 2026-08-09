"""Collaudo del pacchetto PUBBLICATO — l'unico artefatto che sia l'utente.

    python docs/stato-reale/banchi/ws1-collaudo-del-pacchetto-pubblicato.py 0.7.5

PERCHE' ESISTE. Stasera (09/08) sette istanze hanno collaudato la 0.7.5 e per
un'ora hanno misurato COSE DIVERSE senza saperlo: cinque wheel omonimi, quattro
costruiti da ws2 e uno da me con una `build/` sporca. Le conclusioni divergevano
e nessuna era sbagliata — cambiava l'artefatto. Poi ws8 e' andata a leggere
l'INDICE PyPI, che nessuno aveva guardato, e ha trovato in dieci minuti due cose
che a noi erano sfuggite in un giorno: il pin scoperto in tre punti, e un modulo
morto in circolazione da diciotto giorni.

🔑 La lezione che questo file mette in pratica: **l'unico artefatto che conta e'
quello che scarica l'utente**, e per guardarlo NON serve installarlo — basta
aprirlo. 1,7 MB e trenta secondi, contro 1 GB e dieci minuti di `pip install`.

NON sostituisce la prova di comportamento (installare ed eseguire il server):
dice cosa il pacchetto CONTIENE e cosa DICHIARA, non cosa fa. Il confine e'
dichiarato perche' stasera l'abbiamo confuso in tre.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile

ESITI: list[tuple[str, bool | None, str]] = []


def esito(nome: str, ok: bool | None, prova: str) -> None:
    ESITI.append((nome, ok, prova))
    segno = {True: "OK  ", False: "NO  ", None: "?   "}[ok]
    print(f"  {segno} {nome}\n         {prova}")


def main(versione: str) -> int:
    print("=" * 78)
    print(f"COLLAUDO DEL PACCHETTO PUBBLICATO — verimem {versione}")
    print("=" * 78)

    url_json = f"https://pypi.org/pypi/verimem/{versione}/json"
    try:
        d = json.load(urllib.request.urlopen(url_json, timeout=30))
    except Exception as e:                                    # noqa: BLE001
        print(f"\n⛔ {versione} non e' sull'indice PyPI ({type(e).__name__}).")
        print("   Se il tag e' appena partito, la CI ci mette qualche minuto.")
        return 2

    wheels = [u for u in d["urls"] if u["packagetype"] == "bdist_wheel"]
    sdists = [u for u in d["urls"] if u["packagetype"] == "sdist"]
    if not wheels:
        print("\n⛔ nessun wheel pubblicato per questa versione.")
        return 2

    w = wheels[0]
    raw = urllib.request.urlopen(w["url"], timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    nomi = z.namelist()
    meta = z.read([n for n in nomi if n.endswith("METADATA")][0]).decode(
        "utf-8", "replace")

    # ── L'ARTEFATTO, dichiarato in prima riga (regola di casa dal 08/08) ─────
    print(f"\n🔭 ARTEFATTO: {w['filename']}")
    print(f"   sha256 {hashlib.sha256(raw).hexdigest()[:32]} · {len(raw)} byte "
          f"· {len(nomi)} file")
    print(f"   caricato {w.get('upload_time_iso_8601', '?')}")
    print(f"   sdist pubblicato insieme: {'si' if sdists else 'NO'}\n")

    # ── ① la versione e' quella che dice di essere ──────────────────────────
    dichiarata = next((r.split(":", 1)[1].strip() for r in meta.splitlines()
                       if r.startswith("Version:")), "?")
    esito("la Version nel METADATA e' quella richiesta",
          dichiarata == versione, f"Version: {dichiarata}")

    # ── ② il tetto su mcp, in TUTTI i punti ─────────────────────────────────
    righe_mcp = [r for r in meta.splitlines()
                 if r.startswith("Requires-Dist:") and "mcp" in r.split()[1]]
    col_tetto = [r for r in righe_mcp if "<2" in r]
    esito("ogni Requires-Dist di mcp ha il tetto <2",
          bool(righe_mcp) and len(col_tetto) == len(righe_mcp),
          f"{len(col_tetto)}/{len(righe_mcp)} con tetto — " +
          " · ".join(r.split(":", 1)[1].strip() for r in righe_mcp[:3]))

    # ── ③ nessun modulo che il repository non ha ────────────────────────────
    # Il confronto col repo si fa da fuori (serve il checkout); qui si controlla
    # il caso noto: un file rimosso a giugno che sopravvive nelle build sporche.
    esito("il modulo morto rerank.py NON e' nel pacchetto",
          not any(n == "verimem/rerank.py" for n in nomi),
          f"moduli .py: {sum(1 for n in nomi if n.endswith('.py'))}")

    # ── ④ le instructions che ogni agente MCP ricevera' ─────────────────────
    try:
        guida = z.read("verimem/agent_guide.py").decode("utf-8", "replace")
    except KeyError:
        guida = ""
    # ⚠️ Ogni prova cerca la FRASE della cura, non una parola che le sta vicino.
    # Nel primo giro cercavo `VERIMEM_TOOL_NAMESPACE` e la 0.7.0 rispondeva OK:
    # il nome della variabile era gia' nel testo del 22/07 per altre ragioni,
    # mentre la riga che dice all'agente cosa farne e' del 08/08. Una stringa
    # che puo' esistere per due motivi diversi non e' una prova di nessuno dei
    # due — ed e' l'errore che questa casa ha pagato quattro volte in un giorno.
    promesse = {
        "dice di leggere i nomi che il client elenca davvero":
            "Read the names your client actually lists" in guida,
        "dice che recall NON si astiene": "DO NOT abstain" in guida,
        "dice che il namespace RINOMINA (never both)": "never both" in guida,
    }
    for k, v in promesse.items():
        esito(f"agent_guide: {k}", v, "nel wheel" if v else "ASSENTE dal wheel")

    # ── ⑤ il README che finisce sulla pagina PyPI ───────────────────────────
    esito("il README nel METADATA non contiene la riga ritirata il 09/08",
          "the CLI cannot delete at all" not in meta,
          "«the CLI cannot delete at all» assente" if
          "the CLI cannot delete at all" not in meta else "RIGA FALSA PRESENTE")
    esito("il README dichiara le porte di cancellazione",
          "facts_undo_log" in meta,
          "nomina facts_undo_log" if "facts_undo_log" in meta else "non ne parla")

    # ── ⑥ i numeri della pagina sono ancorati? (lezione ws6, 09/08) ─────────
    nudi = [l for l in meta.splitlines()
            if re.search(r"\b\d{3,}\b", l) and not re.search(r"20\d\d", l)
            and "|" not in l and not l.strip().startswith(("#", "```"))]
    esito("i numeri grossi della pagina portano un'ancora (data/SHA)",
          None,
          f"{len(nudi)} righe con numeri a 3+ cifre senza data accanto — "
          f"da leggere a mano, non e' un verdetto")

    print("\n" + "=" * 78)
    veri = sum(1 for _, ok, _ in ESITI if ok is True)
    falsi = sum(1 for _, ok, _ in ESITI if ok is False)
    aperti = sum(1 for _, ok, _ in ESITI if ok is None)
    print(f"VERE {veri} · FALSE {falsi} · DA LEGGERE {aperti}")
    print("Non misurato qui: che il server PARTA e risponda — serve installarlo.")
    return 1 if falsi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "0.7.5"))
