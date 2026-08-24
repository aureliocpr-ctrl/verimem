"""«empty proposition» diceva cosa MANCA, non cosa era stato BUTTATO.

Misurato alla porta MCP il 24/08, ed è costato un banco intero a chi l'ha
trovato — cioè a me::

    hippo_remember({"content": "..."})  ->  {'error': 'empty proposition'}

Il nome giusto è `proposition`. Lo schema del tool non dichiara
`additionalProperties`, quindi per JSON Schema `content` **passa la
validazione** e viene ignorato in silenzio. Chi legge la risposta va a
cercare perché la sua proposizione sia vuota, e la verità è che non l'ha mai
passata: il mio banco sui conteggi ha misurato uno store vuoto per un'ora
senza accorgersene, e i suoi «0 elementi» sembravano un risultato pulito.

⇒ È la classe della serata — **il messaggio manda a cercare nel posto
sbagliato** — sulla superficie più esposta del prodotto, quella che legge un
agente.

⛔ SI NOMINANO SOLO LE CHIAVI, MAI I VALORI, e il presidio lo verifica. Un
messaggio d'errore che riecheggia il contenuto diventa l'ennesimo posto dove
finisce un dato che poi va cancellato — è il fronte GDPR aperto lo stesso
giorno da ws4, e sarebbe grottesco aprirne un altro mentre quello è aperto.

📌 Il messaggio nasceva in DUE punti (`mcp_server.py` ~7526 e ~12769) con la
stessa stringa: qui diventa una funzione sola, come per i verdetti L3.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile

import pytest


def _chiama(nome: str, argomenti: dict) -> dict:
    os.environ.setdefault("HIPPO_DATA_DIR", tempfile.mkdtemp())
    import verimem.mcp_server as m
    r = asyncio.run(m.call_tool(nome, argomenti))
    assert r, "il tool non ha risposto"
    return json.loads(r[0].text)


SEGRETO = "ZZVALORE7788"


def test_dice_QUALE_chiave_ha_ignorato():
    """IL CUORE: un nome sbagliato deve essere nominato, non ingoiato."""
    d = _chiama("hippo_remember", {"content": "Il magazzino ha 4200 metri quadrati."})
    err = str(d.get("error") or "")
    assert "content" in err, (
        f"la chiave ignorata non compare nel messaggio: {err!r}. Chi ha "
        f"sbagliato nome va a cercare perché la sua proposizione sia vuota")
    assert "proposition" in err, (
        f"il messaggio non dice dove va il testo: {err!r}")


def test_nomina_TUTTE_le_chiavi_sconosciute():
    """Una sola non basta: chi sbaglia nome spesso ne sbaglia più di uno."""
    d = _chiama("hippo_remember", {"text": "x", "body": "y"})
    err = str(d.get("error") or "")
    for k in ("text", "body"):
        assert k in err, f"`{k}` non compare fra le chiavi ignorate: {err!r}"


def test_una_proposizione_DAVVERO_vuota_non_accusa_nessuno():
    """⚖️ L'ALTRA POPOLAZIONE, e senza di essa la cura è un falso allarme
    perpetuo: chi passa il nome GIUSTO ma il testo vuoto non ha ignorato
    niente, e il messaggio non deve elencare chiavi."""
    d = _chiama("hippo_remember", {"proposition": "   ", "topic": "t"})
    err = str(d.get("error") or "")
    assert "empty proposition" in err
    assert "IGNORED" not in err, (
        f"nessuna chiave era sconosciuta, ma il messaggio ne accusa: {err!r}")


def test_il_messaggio_non_riecheggia_MAI_i_valori():
    """⛔ GDPR: le chiavi sì, i valori no.

    Un errore che ripete il contenuto diventa un altro posto dove finisce un
    dato che poi va cancellato — e in questo prodotto il purge è già
    SELETTIVO (proposizione e topic sopravvivono in `adjudications`).
    """
    d = _chiama("hippo_remember", {"contenuto_sbagliato": SEGRETO})
    err = str(d.get("error") or "")
    assert "contenuto_sbagliato" in err, "la chiave deve essere nominata"
    assert SEGRETO not in err, (
        f"il VALORE è finito nel messaggio d'errore: {err!r}")


def test_la_scrittura_GIUSTA_funziona_ancora():
    """Il controllo che la cura non abbia rotto il caso normale."""
    d = _chiama("hippo_remember", {
        "proposition": "Il magazzino centrale ha 4200 metri quadrati.",
        "topic": "t",
        "source": "Planimetria: magazzino centrale, 4200 metri quadrati."})
    assert not d.get("error"), f"una scrittura valida è stata rifiutata: {d!r}"
    assert d.get("id"), f"la scrittura non ha prodotto un id: {d!r}"


def test_il_messaggio_nasce_in_UN_solo_posto():
    """I due punti che lo emettevano avevano la stessa stringa cablata due
    volte. Due copie ri-divergono: è successo stasera sui verdetti L3."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "verimem"
           / "mcp_server.py").read_text(encoding="utf-8", errors="replace")
    cablati = src.count('_err("empty proposition")')
    assert cablati == 0, (
        f"il messaggio è di nuovo cablato in {cablati} punti invece di "
        f"passare da `_err_proposizione_vuota`")
    assert src.count("_err_proposizione_vuota") >= 3, (
        "la funzione unica non è usata da entrambe le porte")


@pytest.mark.parametrize("chiave", ["topic", "source", "verified_by"])
def test_le_chiavi_LEGITTIME_non_vengono_accusate(chiave):
    """⚖️ Il controllo negativo sull'elenco: un parametro valido passato
    insieme a una proposizione vuota non è «non riconosciuto»."""
    d = _chiama("hippo_remember", {"proposition": "", chiave: "x"})
    err = str(d.get("error") or "")
    assert f"'{chiave}'" not in err, (
        f"`{chiave}` è un parametro legittimo ma il messaggio lo accusa: {err!r}")
