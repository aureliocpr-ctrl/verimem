"""RIGA 2 — la porta MCP non inventa fatti.

LA PROMESSA. Lista chiusa della 0.7.7, riga 2 (21/09 21:5x). Il README (quickstart MCP)
consegna a un client qualunque gli strumenti `verimem_*`, e la guida che il server manda
all'avvio dice che una scrittura passa dal cancello. Un fatto che nessuno ha scritto non
deve comparire nello store dell'utente.

COSA VEDEVA L'UTENTE (T184, misurato il 21/09 alla porta): `document_promote_chunk`
chiamato senza i suoi quattro campi obbligatori scriveva la proposizione «None» come
`model_claim` SERVIBILE, con citazione `file:None:None-None`. Uno strumento che pubblica
dei campi obbligatori li deve pretendere: chi lo chiama male riceve un rifiuto che nomina
il campo, non un fatto finto nella sua memoria.

LA PROVA. Si avvia `verimem mcp` come nel quickstart (`VERIMEM_TOOL_NAMESPACE=verimem`),
si chiede la lista degli strumenti, e OGNI strumento che dichiara `required` viene
chiamato con `{}`. Due misure, dal lato dell'utente: il numero dei fatti vivi nello store
(`Memory().count()`) prima e dopo, e l'elenco degli strumenti che hanno ACCETTATO la
chiamata vuota. Controllo positivo: la lista deve pubblicare almeno venti strumenti con
campi obbligatori, altrimenti la prova misurerebbe uno schema vuoto.

CHI LA CHIUDE: T184 (#123, «A tool that publishes required fields now enforces them») e
T191 (#126, fusa: la promozione rilegge il chunk dall'indice). Oggi: ROSSA (predizione).
"""
from __future__ import annotations

CONTA = "from verimem import Memory; print('CONTA', Memory().count())"


def _conta(utente) -> int:
    uscita = utente.python(CONTA)
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("CONTA ")]
    assert righe, f"conteggio non riuscito: {uscita.stderr[-600:]}"
    return int(righe[-1].split()[1])


def _rifiutata(risposta: dict) -> bool:
    return bool(risposta.get("errore_protocollo") or risposta.get("isError")
                or (isinstance(risposta, dict) and risposta.get("error")))


def test_riga_2_una_chiamata_senza_i_campi_obbligatori_non_scrive_un_fatto(utente):
    prima = _conta(utente)
    accettate: list[tuple[str, str]] = []
    with utente.mcp() as sessione:
        strumenti = sessione.strumenti()
        con_obbligatori = [s for s in strumenti
                           if ((s.get("inputSchema") or {}).get("required"))]
        assert len(con_obbligatori) >= 20, (
            f"CONTROLLO POSITIVO SPENTO: solo {len(con_obbligatori)} strumenti su "
            f"{len(strumenti)} pubblicano campi obbligatori")
        for s in con_obbligatori:
            try:
                risposta = sessione.chiama(s["name"], {}, tetto_s=60)
            except TimeoutError as exc:
                accettate.append((s["name"], f"nessun rifiuto in 60 s: {exc}"))
                continue
            if not _rifiutata(risposta):
                accettate.append((s["name"], str(risposta)[:160]))
    dopo = _conta(utente)

    assert dopo == prima, (
        f"{dopo - prima} fatti sono NATI nello store dell'utente da chiamate senza i "
        f"campi obbligatori; strumenti che le hanno accettate: {accettate[:10]}")
    assert not accettate, (
        f"{len(accettate)} strumenti su {len(con_obbligatori)} hanno accettato una "
        f"chiamata senza i campi che dichiarano obbligatori: {accettate[:12]}")
