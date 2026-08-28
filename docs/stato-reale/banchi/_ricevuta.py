"""Lettore di ricevuta condiviso SDK/MCP che **fallisce forte**.

Nato da tre errori nella stessa notte (29/08), tutti della stessa forma —
**ho letto una chiave che non c'era e ho preso il vuoto per una misura**:

    ① ``receipt["layers"]``            -> la chiave NON ESISTE
    ② ``ricevuta_mcp["warnings"]``     -> la ricevuta MCP espone
                                          ``anti_confab_warnings``
    ③ ``verified_by != ''``            -> conta 15245 su 15245, perche' il
                                          valore e' ``'[]'``, che e' una
                                          stringa NON VUOTA

Il presidio «*stampa le chiavi prima di contare*» era gia' stato scritto dopo
①, e **non mi ha protetto** da ② — perche' era rimasto un **ricordo** invece di
diventare un **controllo dentro il banco**. Questo file e' quel controllo.

🔑 **La ragione per cui alza invece di tornare lista vuota**: un banco che
restituisce ``[]`` per una chiave sbagliata e' **indistinguibile** da un banco
che misura zero. E' la classe «*un'assenza di misura letta come misura
perfetta*»: nei miei tre banchi W2-27 la colonna MCP era vuota **per
costruzione**, e ci ho letto sopra un racconto.

⚠️ E il danno peggiore non e' stato il falso: e' stata l'**astensione**. Due
volte ho dichiarato «banco inerte, NESSUN VERDETTO» — che sembrava onesta — su
uno strumento che era **cieco da un lato**. Un'astensione costruita su uno
strumento cieco non e' onesta: e' lo stesso errore con il cappello modesto.

    from _ricevuta import strati, quarantinata   # noqa: ERA401
"""

from __future__ import annotations

#: Le chiavi note che trasportano gli strati, **per porta**. L'SDK usa
#: ``warnings``; la porta MCP usa ``anti_confab_warnings``. Se ne comparisse una
#: terza, il banco deve ROMPERSI qui e non tacere.
CHIAVI_STRATI = ("warnings", "anti_confab_warnings")


class RicevutaIlleggibile(KeyError):
    """Nessuna chiave-strati nota: il banco NON puo' concludere niente."""


def strati(ricevuta: dict, *, dove: str) -> list[str]:
    """Gli strati della ricevuta, da qualunque porta venga.

    ``dove`` nomina la porta ("SDK" / "MCP") e finisce nel messaggio: senza,
    un fallimento non dice **quale** delle due letture e' cieca.

    ALZA ``RicevutaIlleggibile`` se **nessuna** chiave nota e' presente —
    invece di tornare ``[]``, che il banco non saprebbe distinguere da «zero
    strati misurati».
    """
    if not isinstance(ricevuta, dict):
        raise RicevutaIlleggibile(
            f"[{dove}] la ricevuta non e' un dict ma {type(ricevuta).__name__} "
            f"-> {ricevuta!r:.80}")
    presenti = [k for k in CHIAVI_STRATI if k in ricevuta]
    if not presenti:
        raise RicevutaIlleggibile(
            f"[{dove}] nessuna chiave-strati nota. Cercavo {CHIAVI_STRATI!r}. "
            f"CHIAVI VISTE: {sorted(ricevuta)!r}")
    fuori: list[str] = []
    for k in presenti:
        for w in (ricevuta.get(k) or []):
            if isinstance(w, dict) and w.get("layer"):
                fuori.append(str(w["layer"]))
    return fuori


def quarantinata(ricevuta: dict, *, dove: str) -> bool:
    """Il verdetto, letto da ``status``, che entrambe le porte espongono."""
    if "status" not in ricevuta:
        raise RicevutaIlleggibile(
            f"[{dove}] nessuno `status`. CHIAVI VISTE: {sorted(ricevuta)!r}")
    return str(ricevuta.get("status")) == "quarantined"


def spiega(ricevuta: dict, *, dove: str) -> str:
    """Una riga che dice **da quale chiave** viene il dato: senza, la tabella
    non e' verificabile da chi la legge."""
    presenti = [k for k in CHIAVI_STRATI if k in ricevuta]
    return (f"[{dove}] chiave-strati usata: {presenti or 'NESSUNA'} · "
            f"{len(sorted(ricevuta))} chiavi in ricevuta")
