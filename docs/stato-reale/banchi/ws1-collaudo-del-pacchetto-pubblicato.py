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
import tarfile
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

    # ── L'SDIST, APERTO E NON SOLO CONTATO ──────────────────────────────────
    # ⚠️ QUI C'ERA `sdist pubblicato insieme: si` E BASTA. Il banco lo VEDEVA,
    # lo contava, lo STAMPAVA — e non lo apriva mai. Chi leggeva quella riga
    # concludeva che fosse stato controllato: l'ho scritta io e per due giorni
    # l'ho letta come una spunta.
    # 🔑 IL PUNTO CIECO NON E' L'ASSENZA, E' LA MENZIONE. Un banco che TACE su
    # un artefatto lascia la domanda aperta; uno che lo NOMINA senza aprirlo la
    # chiude con una risposta che non ha.
    # 📌 Il costo l'ha misurato ws7 il 12/08 (`5fffa44a921ffdd5`): sul wheel le
    # righe con identificativi interni sono andate da 86 a ZERO, sull'sdist da
    # 208 a 814 — e i due artefatti escono dallo STESSO `twine upload`. Abbiamo
    # ripulito benissimo l'artefatto che tutti guardavano, e questo banco
    # guardava lì insieme a tutti.
    # ⚠️ L'sdist e' un `.tar.gz`, il wheel uno `.zip`: l'archivio si apre in due
    # modi diversi e il tipo va CHIESTO, non assunto.
    sdist_nomi: list[str] = []
    if sdists:
        s = sdists[0]
        s_raw = urllib.request.urlopen(s["url"], timeout=120).read()
        with tarfile.open(fileobj=io.BytesIO(s_raw), mode="r:gz") as t:
            sdist_nomi = t.getnames()
        print(f"🔭 SDIST: {s['filename']}")
        print(f"   sha256 {hashlib.sha256(s_raw).hexdigest()[:32]} · "
              f"{len(s_raw)} byte · {len(sdist_nomi)} voci")
    else:
        print("🔭 SDIST: NON pubblicato per questa versione")
    print()

    # ── ① la versione e' quella che dice di essere ──────────────────────────
    dichiarata = next((r.split(":", 1)[1].strip() for r in meta.splitlines()
                       if r.startswith("Version:")), "?")
    esito("la Version nel METADATA e' quella richiesta",
          dichiarata == versione, f"Version: {dichiarata}")

    # ── ①-bis LA SUPERFICIE IN PIU' DELL'SDIST, dichiarata e non contata ────
    # La domanda non e' «quante righe interne ha l'sdist» — quella l'ha misurata
    # ws7 e non si rifa'. E' un'altra: **cosa viene pubblicato che il wheel non
    # contiene**, cioe' la superficie che esce da `twine upload` e che nessun
    # banco guardava. Non e' un verdetto: e' l'elenco che rende la domanda
    # ponibile, ed e' il motivo per cui questo blocco stampa CATEGORIE e non un
    # totale.
    # 📌 Le categorie si dichiarano TUTTE, anche a zero (presidio di ws7 del
    # 12/08 in `060e1ac9c7891fa0`: uno zero che esiste solo come assenza di riga
    # non e' citabile — e un fatto che non si puo' citare non entra in memoria).
    if sdist_nomi:
        def _categoria(nome: str) -> str:
            """La cartella di primo livello DENTRO l'sdist.

            ⚠️ La tarball ha un prefisso comune (`verimem-0.7.0/`) e una voce
            per la radice stessa, che NON contiene `/`: dare per scontato che
            ogni nome sia divisibile fa esplodere il conteggio sulla prima riga.
            """
            pezzi = nome.split("/")
            if len(pezzi) < 2 or not pezzi[1]:
                return "(radice)"
            return pezzi[1] if len(pezzi) > 2 else "(radice)"

        conta: dict[str, int] = {}
        for n in sdist_nomi:
            conta[_categoria(n)] = conta.get(_categoria(n), 0) + 1
        nel_wheel = {"verimem", "engram", "hippoagent", "(radice)"}
        extra = {c: k for c, k in sorted(conta.items())
                 if c not in nel_wheel and k}
        esito("l'sdist non pubblica cartelle che il wheel non ha", not extra,
              "in piu' rispetto al wheel: "
              + (" · ".join(f"{c} {k}" for c, k in sorted(extra.items())[:6])
                 if extra else "nessuna"))

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
    # ⚠️ «MORTO» E' UNA DATA, NON UNA PROPRIETA'. `rerank.py` e' stato tolto da
    # main il 30/07 e il wheel 0.7.0 e' del 22/07: la' dentro era ancora vivo.
    # Un NO su un wheel piu' VECCHIO della rimozione non e' un difetto di quel
    # rilascio — e' l'arretrato di chi non ha ancora ripubblicato. Le due cose
    # portano ad azioni opposte (correggere il pacchetto / pubblicarne uno nuovo)
    # e il referto deve permettere di distinguerle senza aprire `git log`.
    c_e = any(n == "verimem/rerank.py" for n in nomi)
    esito("rerank.py (ritirato da main il 30/07) NON e' nel pacchetto",
          not c_e,
          f"moduli .py: {sum(1 for n in nomi if n.endswith('.py'))}"
          + (" — se il wheel e' anteriore al 30/07 questo e' ARRETRATO,"
             " non un difetto del rilascio" if c_e else ""))

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
    # ⚠️ LA PROVA DICE QUALE DEI DUE MANCA, e non e' pedanteria: la prima
    # versione stampava «ASSENTE dal wheel» per una FRASE mancante, e io — che
    # questo file l'ho scritto — leggendo il mio referto ho concluso che mancasse
    # il MODULO, e stavo per dirlo sul canale. `verimem/agent_guide.py` e' nel
    # wheel 0.7.0: sono le tre frasi (cure dell'08/08) a non esserci.
    # 🔑 Un referto che confonde IL CONTENITORE col CONTENUTO fa diagnosticare la
    # cosa sbagliata a chiunque lo legga, autore compreso.
    dov_e = "verimem/agent_guide.py nel wheel" if guida else "manca il MODULO"
    for k, v in promesse.items():
        esito(f"agent_guide: {k}", v,
              "la frase c'e'" if v else f"la FRASE non c'e' ({dov_e})")

    # ── ④-bis la superficie di governo, entrata il 09/08 a merge tardivo ────
    # Sta qui perche' e' il caso in cui il pacchetto puo' restare indietro
    # rispetto al repository SENZA che nulla lo segnali: il 09/08 il wheel
    # collaudato aveva 384 moduli e main ne aveva gia' 419.
    governo = ("retirement_log", "tier_inventory", "residual_copies", "text_cut")
    mancanti = [m for m in governo if f"verimem/{m}.py" not in nomi]
    esito("la superficie di governo e' nel pacchetto",
          not mancanti,
          "tutti e quattro presenti" if not mancanti
          else f"MANCANO: {mancanti} — il wheel e' piu' vecchio del merge")

    # ── ⑤ il README che finisce sulla pagina PyPI ───────────────────────────
    esito("il README nel METADATA non contiene la riga ritirata il 09/08",
          "the CLI cannot delete at all" not in meta,
          "«the CLI cannot delete at all» assente" if
          "the CLI cannot delete at all" not in meta else "RIGA FALSA PRESENTE")
    esito("il README dichiara le porte di cancellazione",
          "facts_undo_log" in meta,
          "nomina facts_undo_log" if "facts_undo_log" in meta else "non ne parla")

    # ── ⑥ i numeri della pagina sono ancorati? (lezione ws6, 09/08) ─────────
    nudi = [riga for riga in meta.splitlines()
            if re.search(r"\b\d{3,}\b", riga) and not re.search(r"20\d\d", riga)
            and "|" not in riga and not riga.strip().startswith(("#", "```"))]
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
