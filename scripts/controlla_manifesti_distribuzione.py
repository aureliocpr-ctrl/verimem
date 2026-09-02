"""I manifesti di distribuzione dicono il vero? — server.json e marketplace.json.

═══ PERCHE' ESISTE ═══
Questi due file non li esegue nessuno: li legge un registry, una volta, e se
sono sbagliati la pubblicazione fallisce lontano da qui — o peggio riesce e
pubblica un nome che non e' nostro. Sono esattamente il tipo di file che
«sembra a posto» finche' non lo guarda un estraneo. Questo banco e' quell'estraneo.

═══ CONTRO CHE COSA CONTROLLA ═══
Schema MCP 2025-12-11 (i `required` letti dallo schema, non dalla prosa):
  ServerDetail  ->  name, description, version
  Package       ->  registryType, identifier, transport
`name`: pattern ^[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+$, min 3, max 200, reverse-DNS
        con ESATTAMENTE una barra.
`registryType`: npm | pypi | nuget | cargo | oci | mcpb
Marketplace Claude Code: name (kebab-case), owner{name}, plugins[]{name, source}.

═══ IL CONTROLLO CHE CONTA DAVVERO ═══
Per un pacchetto PyPI la PROVA DI PROPRIETA' e' la stringa `mcp-name: <nome>`
nel README (che diventa la description su PyPI), e quel nome DEVE combaciare con
`name` in server.json. Due file che si scrivono da soli divergono: qui il banco
li obbliga a dire la stessa cosa, e se il README non porta ancora la riga lo
dichiara come MANCANTE invece di tacere.

    rifallo con:  python scripts/controlla_manifesti_distribuzione.py
    negativo:     python scripts/controlla_manifesti_distribuzione.py --falsifica
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
SERVER = RADICE / "server.json"
MARKET = RADICE / ".claude-plugin" / "marketplace.json"
README = RADICE / "README.md"

NOME_RE = re.compile(r"^[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REGISTRY_TYPES = {"npm", "pypi", "nuget", "cargo", "oci", "mcpb"}


def esito(ok: bool, testo: str, dettaglio: str = "") -> bool:
    print(f"  {'OK  ' if ok else '🔴  '}{testo}{('  — ' + dettaglio) if dettaglio else ''}")
    return ok


def carica(p: Path) -> dict | None:
    if not p.exists():
        esito(False, f"{p.relative_to(RADICE)} ASSENTE")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        esito(False, f"{p.relative_to(RADICE)} non e' JSON valido", str(e)[:60])
        return None


def controlla_server(d: dict, nome_atteso: str | None = None) -> bool:
    ok = True
    print("\n  === server.json — schema MCP 2025-12-11 ===")
    for campo in ("name", "description", "version"):
        ok &= esito(campo in d and str(d[campo]).strip() != "",
                    f"ServerDetail.{campo} presente e non vuoto")
    nome = str(d.get("name", ""))
    ok &= esito(bool(NOME_RE.match(nome)), "name rispetta il pattern reverse-DNS", nome)
    ok &= esito(nome.count("/") == 1, "name ha esattamente una barra")
    ok &= esito(3 <= len(nome) <= 200, f"lunghezza di name fra 3 e 200 ({len(nome)})")

    pacchetti = d.get("packages") or []
    ok &= esito(bool(pacchetti), "packages non vuoto")
    for i, p in enumerate(pacchetti):
        for campo in ("registryType", "identifier", "transport"):
            ok &= esito(campo in p, f"packages[{i}].{campo} presente")
        rt = p.get("registryType")
        ok &= esito(rt in REGISTRY_TYPES, f"packages[{i}].registryType e' un valore noto", str(rt))
        # La versione del pacchetto e quella del server devono coincidere: se
        # divergono, il registry pubblica un puntatore a un artefatto che non e'
        # quello dichiarato — e nessuno se ne accorge finche' qualcuno installa.
        if "version" in p:
            ok &= esito(p["version"] == d.get("version"),
                        f"packages[{i}].version == ServerDetail.version",
                        f"{p.get('version')} vs {d.get('version')}")
    if nome_atteso is not None:
        ok &= esito(nome == nome_atteso, "name combacia con quello atteso dal test",
                    f"{nome} vs {nome_atteso}")
    return ok


def controlla_marketplace(d: dict) -> bool:
    ok = True
    print("\n  === .claude-plugin/marketplace.json ===")
    nome = str(d.get("name", ""))
    ok &= esito(bool(KEBAB_RE.match(nome)), "name in kebab-case", nome)
    owner = d.get("owner")
    ok &= esito(isinstance(owner, dict) and bool(owner.get("name")),
                "owner e' un oggetto con name")
    plugins = d.get("plugins") or []
    ok &= esito(bool(plugins), "plugins non vuoto")
    for i, p in enumerate(plugins):
        ok &= esito(bool(p.get("name")), f"plugins[{i}].name presente")
        ok &= esito(bool(p.get("source")), f"plugins[{i}].source presente")
    return ok


def controlla_prova_pypi(nome_server: str) -> bool:
    """La riga che dimostra al registry che il pacchetto PyPI e' nostro."""
    print("\n  === prova di proprieta' PyPI: `mcp-name` nel README ===")
    if not README.exists():
        return esito(False, "README.md assente")
    testo = README.read_text(encoding="utf-8", errors="replace")
    trovati = re.findall(r"mcp-name:\s*([^\s<>]+)", testo)
    if not trovati:
        return esito(False, "nessuna riga `mcp-name:` nel README",
                     "va aggiunta PRIMA della release: il README diventa la description su PyPI")
    ok = esito(True, f"riga `mcp-name:` presente ({len(trovati)} occorrenza/e)")
    for t in trovati:
        ok &= esito(t == nome_server, "il nome nel README combacia con server.json",
                    f"{t} vs {nome_server}")
    return ok


def main() -> int:
    falsifica = "--falsifica" in sys.argv
    print("=" * 74)
    print("  MANIFESTI DI DISTRIBUZIONE — server.json · marketplace.json · README")
    if falsifica:
        print("  ⚠️ MODO FALSIFICA: il nome atteso e' alterato, il banco DEVE fallire.")
    print("=" * 74)

    s = carica(SERVER)
    m = carica(MARKET)
    if s is None or m is None:
        print("\n  ⛔ manifesti mancanti o illeggibili: nessun verdetto.")
        return 2

    atteso = "io.github.QUALCUNALTRO/verimem" if falsifica else None
    ok = controlla_server(s, atteso)
    ok &= controlla_marketplace(m)
    # La prova PyPI si controlla sempre, ma NON fa fallire il banco finche' la
    # riga non e' stata aggiunta: e' un lavoro sul README, che ha un altro
    # proprietario. Il banco la dichiara MANCANTE e lo dice a voce alta.
    prova = controlla_prova_pypi(str(s.get("name", "")))
    if not prova:
        print("\n  ⚠️ La prova di proprieta' NON e' ancora in piedi: la pubblicazione")
        print("     sul registry fallirebbe la verifica del namespace. Non fa fallire")
        print("     questo banco perche' il README non e' un manifesto — ma senza")
        print("     quella riga i due file qui sopra non servono a niente.")

    print()
    if ok:
        print("  ✔ i manifesti sono coerenti con lo schema.")
        return 0
    print("  🔴 almeno un controllo e' fallito: vedi le righe con 🔴.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
