"""Chi sbaglia un nome deve leggere IL PROPRIO nome, non quello riscritto.

Il dispatch normalizza gli alias prima di ogni altra cosa
(`mcp_server.py:7340-7347`): `verimem_x` e `engram_x` diventano `hippo_x`, e da
lì in poi il nome ricevuto non esiste più in nessuna variabile. Misurato alla
porta il 16/08::

    chiamato:  verimem_non_esiste_affatto
    risposta:  {"error": "unknown tool: hippo_non_esiste_affatto"}
    audit:     outcome=unknown_tool tool=hippo_non_esiste_affatto

⇒ L'utente non ha mai scritto `hippo_`. Va a cercare un tool che non ha
digitato, e per giunta legge un prefisso che la documentazione non usa più.

⚠️ La conseguenza peggiore non è il messaggio, è la **telemetria**: tre chiamate
riuscite con tre prefissi diversi hanno prodotto tre righe di audit
indistinguibili (`tool=hippo_health` per tutte e tre). Per decidere se il
default può passare a `verimem_*` servirebbe sapere quanti host lo usano già —
e il registro non può dirlo, perché il nome lo riscrive prima di scriverlo.

═══ PERCHÉ AGGIUNGE INVECE DI SOSTITUIRE ═══

Nel record di audit il campo `tool` resta il nome **canonico**: chi analizza per
`tool=hippo_health` continua a contare tutte le chiamate, alias inclusi. Il nome
ricevuto arriva in un campo NUOVO, e **solo quando differisce** — così una
chiamata canonica non paga un campo sempre uguale a `tool`.

Nel messaggio d'errore invece si sostituisce: lì l'unico nome utile è quello che
l'utente ha scritto.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from verimem import mcp_server as ms

#: (nome chiamato, nome canonico) — gli alias che il dispatch riscrive.
ALIAS = [
    ("verimem_non_esiste_affatto", "hippo_non_esiste_affatto"),
    ("engram_non_esiste_affatto", "hippo_non_esiste_affatto"),
]


def _chiama(nome: str) -> str:
    return asyncio.run(ms._call_tool_impl(nome, {}))[0].text


@pytest.mark.parametrize("chiamato,canonico", ALIAS,
                         ids=[c[0].split("_")[0] for c in ALIAS])
def test_l_errore_riporta_il_nome_che_ho_scritto(chiamato, canonico):
    testo = _chiama(chiamato)
    assert chiamato in testo, (
        f"ho chiamato «{chiamato}» e l'errore dice «{testo}»: nomina un tool "
        f"che non ho digitato, e mi manda a cercarlo")
    assert canonico not in testo, (
        f"l'errore per «{chiamato}» contiene ancora il nome riscritto "
        f"«{canonico}»: l'utente non l'ha mai scritto")


def test_il_nome_canonico_sbagliato_resta_se_stesso():
    """⚠️ LA POPOLAZIONE OPPOSTA. Senza questo, «riporta il nome chiamato» si
    soddisfa anche stampando sempre l'input grezzo, e non si vedrebbe se la
    normalizzazione smettesse di funzionare."""
    testo = _chiama("hippo_non_esiste_affatto")
    assert "hippo_non_esiste_affatto" in testo


def test_col_namespace_del_prodotto_l_errore_parla_la_stessa_lingua(monkeypatch):
    """⚠️ LA CONFIGURAZIONE IN CUI IL DIFETTO ERA PEGGIORE.

    `ENGRAM_TOOL_NAMESPACE=verimem` espone l'intera superficie come `verimem_*`
    (fase 2 del rename, `test_mcp_server.py:1381`). Lì un utente legge nomi
    `verimem_*` in `tools/list`, ne sbaglia uno, e prima di questa cura si
    sentiva rispondere `hippo_*`: un prefisso che in quella configurazione il
    prodotto non mostra da nessuna parte.
    """
    monkeypatch.setenv("ENGRAM_TOOL_NAMESPACE", "verimem")
    testo = _chiama("verimem_non_esiste_affatto")
    assert "verimem_non_esiste_affatto" in testo
    assert "hippo_" not in testo, (
        "col namespace del prodotto attivo, l'errore non deve nominare un "
        f"prefisso che tools/list non espone. Risposta: {testo}")


def test_l_audit_conserva_il_nome_ricevuto_quando_e_un_alias(tmp_path,
                                                             monkeypatch):
    dest = tmp_path / "audit.jsonl"
    monkeypatch.setattr(ms, "_audit_log_path", lambda: dest)
    _chiama("verimem_non_esiste_affatto")

    righe = [json.loads(r) for r in dest.read_text("utf-8").splitlines() if r]
    assert righe, "nessun record di audit scritto"
    rec = righe[-1]
    assert rec["tool"] == "hippo_non_esiste_affatto", (
        "il campo `tool` deve restare il nome CANONICO: chi analizza per "
        "tool=hippo_* deve continuare a contare anche le chiamate via alias")
    assert rec.get("requested_name") == "verimem_non_esiste_affatto", (
        "il nome ricevuto non è nel record: la telemetria non può dire "
        f"quanti host usano già l'alias. Record: {rec}")


def test_una_chiamata_canonica_non_porta_il_campo_in_piu(tmp_path, monkeypatch):
    """⚠️ Popolazione opposta del campo: se comparisse sempre, sarebbe un
    duplicato di `tool` su ogni riga del registro."""
    dest = tmp_path / "audit.jsonl"
    monkeypatch.setattr(ms, "_audit_log_path", lambda: dest)
    _chiama("hippo_non_esiste_affatto")

    righe = [json.loads(r) for r in dest.read_text("utf-8").splitlines() if r]
    assert righe, "nessun record di audit scritto"
    assert "requested_name" not in righe[-1], (
        "una chiamata col nome canonico non deve pagare un campo sempre "
        f"uguale a `tool`. Record: {righe[-1]}")
