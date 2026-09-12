"""Lo strumento che diagnostica gli stalli non deve diventare il prossimo guaio.

Trovato il 2026-07-31 aprendo per la prima volta `~/.engram/hang-traces/` —
la cartella esisteva da mesi e nessuno l'aveva mai guardata::

    300 file, 34 MB in totale
    hang-1785412814-29092-hippo_health.txt   24.211.732 byte

Ventiquattro megabyte per UN solo stallo. La causa è
``dump_traceback_later(budget_s, repeat=True)``: rida' l'intero dump di tutti i
thread ogni ``budget_s`` secondi finché la chiamata non finisce. Su una chiamata
appesa dieci minuti con budget 30s sono venti dump — e dal secondo in poi è lo
stesso stack, cioè zero informazione in più a costo pieno.

I trace SONO preziosi: è da lì che è uscita la causa vera degli stalli di oggi
(gli import dentro la richiesta, non i modelli). Proprio per questo lo strumento
deve poter restare acceso senza che nessuno debba ricordarsi di svuotare la
cartella.

Due tetti, e nessuno dei due tocca il primo dump — quello che contiene la
diagnosi:

* per-file: oltre il tetto si smette di ridumpare e si scrive PERCHE', così chi
  legge sa che il file è troncato di proposito e non corrotto;
* per-cartella: i trace più vecchi si potano, tenendo i più recenti.
"""
from __future__ import annotations

import time

from verimem import _hang_watchdog as w


def test_il_primo_dump_non_si_tocca_mai(tmp_path, monkeypatch):
    """Il tetto non deve costare la diagnosi: un file sotto la soglia resta
    intero, ed è quello che serve a capire dove si è bloccato."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    with w.hang_trace("prova_veloce", 30.0):
        pass
    assert list(tmp_path.glob("hang-*.txt")) == [], (
        "una chiamata VELOCE ha lasciato un file: il header-only va rimosso")


def test_un_file_che_cresce_troppo_smette_e_lo_dichiara(tmp_path, monkeypatch):
    """Il caso misurato, in piccolo: budget minuscolo perché il watchdog
    ridumpi più volte, e tetto minuscolo perché scatti."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    monkeypatch.setattr(w, "_MAX_FILE_BYTES", 4096)
    # ⚠️ DA T68 QUESTA CELLA MISURA IL TAGLIO ALLA CHIUSURA, non il tetto
    # durante la chiamata: il sorvegliante non annulla piu' il dump (lo annulla
    # solo chi lo ha armato), quindi mentre la chiamata e' appesa NULLA ferma
    # la crescita. Il commento di prima descriveva un meccanismo rimosso, ed e'
    # il caso peggiore: verde per una strada diversa da quella che racconta.
    # Si continua ad avviare il sorvegliante perche' e' la configurazione di
    # produzione, e perche' proprio in quella il fallback alla chiusura veniva
    # SALTATO — il difetto curato insieme a questo, cella qui sotto.
    # 📌 Il file cresce eccome, mentre la chiamata e' appesa: quello che questa
    # cella misura e' che alla fine la coda viene TAGLIATA e quel che resta
    # sta dentro il tetto.
    w.avvia_il_sorvegliante()
    with w.hang_trace("prova_lenta", 0.05):
        time.sleep(1.2)
    file = list(tmp_path.glob("hang-*.txt"))
    assert file, "nessun trace scritto per una chiamata oltre budget"
    testo = file[0].read_text(encoding="utf-8", errors="replace")
    # LA SOGLIA ERA MUTA: 200 000 contro un tetto di 4096 e' un gioco di 48
    # volte, e non distingueva "fermato al tetto" da "cresciuto e poi tagliato".
    # Da quando la chiusura TAGLIA la coda, il file che resta deve stare dentro
    # il tetto piu' la nota, e la cella puo' chiedere proprio quello.
    dimensione = file[0].stat().st_size
    assert dimensione <= w._MAX_FILE_BYTES + 2000, (
        f"il file finale e' di {dimensione} byte contro un tetto di "
        f"{w._MAX_FILE_BYTES}: la coda non e' stata tagliata alla chiusura")
    assert "tetto" in testo.lower() or "troncato" in testo.lower(), (
        "il file è stato troncato senza dire perché: chi legge non distingue "
        f"un tetto da un file corrotto\n{testo[-300:]}")


def test_i_trace_vecchi_si_potano(tmp_path, monkeypatch):
    """300 file accumulati in mesi: chi accende una diagnostica non deve
    ricordarsi di spegnerla."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    monkeypatch.setattr(w, "_MAX_FILES", 5)
    for i in range(12):
        p = tmp_path / f"hang-{1000+i}-1-vecchio.txt"
        p.write_text("x" * 500, encoding="utf-8")
    w._pota_i_vecchi()
    rimasti = sorted(p.name for p in tmp_path.glob("hang-*.txt"))
    assert len(rimasti) == 5, rimasti
    assert rimasti[-1] == "hang-1011-1-vecchio.txt", (
        f"potati i più RECENTI invece dei più vecchi: {rimasti}")


def test_la_potatura_non_tocca_cio_che_non_e_un_trace(tmp_path, monkeypatch):
    """La cartella è dell'utente: si tocca solo ciò che questo modulo scrive."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    monkeypatch.setattr(w, "_MAX_FILES", 1)
    (tmp_path / "note-di-aurelio.txt").write_text("mie", encoding="utf-8")
    (tmp_path / "hang-1-1-a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "hang-2-1-b.txt").write_text("x", encoding="utf-8")
    w._pota_i_vecchi()
    assert (tmp_path / "note-di-aurelio.txt").exists()


def test_potare_non_puo_far_fallire_una_chiamata(tmp_path, monkeypatch):
    """Il contratto del modulo è «observability ONLY, never raises»: una
    cartella non scrivibile deve costare il trace, mai la chiamata."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path / "che-non-esiste")
    monkeypatch.setattr(w, "_MAX_FILES", 1)
    w._pota_i_vecchi()          # non deve sollevare
    with w.hang_trace("prova", 30.0):
        pass


def test_senza_sorvegliante_il_tetto_si_applica_alla_chiusura(tmp_path, monkeypatch):
    """Il DEGRADO DICHIARATO: fuori dal server nessuno avvia il sorvegliante.

    Il tetto non si applica piu' durante la chiamata — il file cresce — ma non
    sparisce: alla chiusura il watchdog lo rileva e lo SCRIVE nel file, cosi'
    chi legge un trace enorme sa perche' e' enorme.

    ⚠️ ISOLAMENTO OBBLIGATORIO: il sorvegliante e' UNICO E GLOBALE. Se un altro
    test lo ha avviato prima, questa cella misurerebbe il caso opposto e
    passerebbe (o cadrebbe) a seconda dell'ordine dei test. Percio' lo si
    azzera esplicitamente invece di sperare.
    """
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    monkeypatch.setattr(w, "_MAX_FILE_BYTES", 4096)
    # ISOLAMENTO VERO: azzerare la variabile NON ferma il thread che un test
    # precedente ha avviato — misurato il 06/09, questa cella cadeva proprio
    # per quello. Si prende il riferimento PRIMA, lo si ferma, e lo si
    # aspetta; il finally rimette l'evento com'era per i test successivi.
    vivo = w._sorvegliante_unico
    monkeypatch.setattr(w, "_sorvegliante_unico", None)
    w._ferma_il_sorvegliante.set()
    if vivo is not None and vivo.is_alive():
        vivo.join(timeout=5.0)
    try:

        with w.hang_trace("senza_sorvegliante", 0.05):
            time.sleep(1.2)

        file = list(tmp_path.glob("hang-*.txt"))
        assert file, "nessun trace scritto per una chiamata oltre budget"
        testo = file[0].read_text(encoding="utf-8", errors="replace")
        assert "CHIUSURA" in testo, (
            "senza sorvegliante il tetto non e' stato nemmeno DICHIARATO alla "
            "chiusura: chi legge un trace enorme non sa perche' lo e'. "
            + testo[-300:])

        # ATTENZIONE, e non e' pignoleria: azzerare `_sorvegliante_unico` NON ferma
        # un thread che un test precedente abbia gia' avviato — quello continua a
        # guardare `_da_sorvegliare` e potrebbe applicare il tetto DURANTE la
        # chiamata. In quel caso la nota qui sopra ci sarebbe lo stesso e questa
        # cella passerebbe PER LA RAGIONE SBAGLIATA. Se compare anche la nota del
        # sorvegliante, il banco lo dice invece di far finta di aver misurato.
        assert "raggiunto: i dump successivi" not in testo, (
            "nel trace c'e' ANCHE la nota del sorvegliante: un thread avviato da "
            "un altro test era ancora vivo, quindi questa cella non ha misurato il "
            "fallback ma il caso opposto. Il verde non vale.\n"
            + testo[-400:])
    finally:
        w._ferma_il_sorvegliante.clear()


def test_col_sorvegliante_vivo_il_tetto_si_applica_lo_stesso_alla_chiusura(
        tmp_path, monkeypatch):
    """IL DIFETTO CHE T68 AVEVA APERTO NEL PRODOTTO, e che questa cella chiude.

    Il fallback alla chiusura girava SOLO se il sorvegliante non era vivo, e il
    presupposto era: "se e' vivo, il tetto lo ha gia' applicato lui durante la
    chiamata". Da quando il dump ha un proprietario quel presupposto e' CADUTO:
    il sorvegliante dichiara ma non disarma piu'. Quindi nel server MCP - che il
    sorvegliante lo avvia - il tetto non si applicava piu' IN NESSUNO DEI DUE
    RAMI, e il caso misurato che doveva prevenire era un file da 24.211.732 byte.

    ⚠️ E' il costo dichiarato nella PR di T68, rivelatosi piu' grande di come
    l'avevo scritto: avevo dichiarato la crescita DURANTE la chiamata, non che
    saltasse anche la chiusura.

    Nessuna corsa e nessuna finestra da centrare: il sorvegliante qui e' un
    FINTO sempre-vivo che non cicla e non scrive. La cella misura una cosa sola:
    quale ramo prende la chiusura quando `is_alive()` risponde di si'.
    """
    class _SorveglianteFintoSempreVivo:
        """Non cicla e non scrive niente: serve solo a rispondere `True`."""

        def is_alive(self) -> bool:
            return True

    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    # 1 byte: qualunque file scritto sfonda. Qui non si misura la soglia, si
    # misura QUALE RAMO si prende, e una soglia larga renderebbe la cella muta.
    monkeypatch.setattr(w, "_MAX_FILE_BYTES", 1)
    # ISOLAMENTO, come nella cella qui sopra: sostituire la variabile NON ferma
    # il thread vero che un altro test abbia avviato, e quello scriverebbe la
    # SUA nota nel mio file. Si prende il riferimento prima, si ferma, si aspetta.
    vivo = w._sorvegliante_unico
    monkeypatch.setattr(w, "_sorvegliante_unico", _SorveglianteFintoSempreVivo())
    w._ferma_il_sorvegliante.set()
    if vivo is not None and vivo.is_alive():
        vivo.join(timeout=5.0)
    try:
        with w.hang_trace("col_sorvegliante", 0.05):
            time.sleep(0.3)

        file = list(tmp_path.glob("hang-*.txt"))
        assert file, "nessun trace scritto per una chiamata oltre budget"
        testo = file[0].read_text(encoding="utf-8", errors="replace")
        assert "rilevato alla CHIUSURA" in testo, (
            "col sorvegliante vivo la chiusura NON ha applicato il tetto: e' il "
            "ramo che prende il server MCP, dove il file cresce e nessuno lo "
            "dichiara. Coda del trace: " + testo[-300:])
        # CONTROLLO ROVESCIATO: se avesse scritto il sorvegliante vero, questa
        # cella misurerebbe il caso opposto e passerebbe lo stesso.
        assert "raggiunto: i dump successivi" not in testo, (
            "ha scritto il sorvegliante, non la chiusura: un thread vero era "
            "ancora vivo, quindi questa cella non ha misurato il fallback. "
            "Coda del trace: " + testo[-400:])
    finally:
        w._ferma_il_sorvegliante.clear()
