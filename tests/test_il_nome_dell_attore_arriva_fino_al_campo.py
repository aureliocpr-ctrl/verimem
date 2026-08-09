"""Il guardiano c'era e sorvegliava un piano piu' in alto del necessario.

`test_il_ritiro_non_diceva_chi_e_stato.py` verifica `cli._principale()` — la
FUNZIONE che decide chi la CLI dice di essere. Ma nessun test verificava che
quel valore **atterri in `facts.writer_principal`** quando qualcuno salva
davvero. Fra la funzione e il campo c'e' un filo (`save_checkpoint(...,
principal=_principale())`) e nessuno lo sorvegliava: scollegarlo lasciava
**tutti i test verdi** mentre ogni scrittura tornava anonima.

🔑 E' la lezione del LIVELLO, che ci e' costata cinque ritiri il 07/08:
*regex interna < funzione pubblica < porta che il prodotto usa*, e ogni salto
puo' ribaltare il verdetto. Qui il salto e' proprio quello che serve, perche'
il campo lo legge chi indaga un ritiro, non chi legge il codice.

Perche' importa adesso: il 09/08 eravamo otto istanze e i 137 fatti scritti in
serata dicevano **tutti** `cli:local` — otto autori, un nome solo. Con
`VERIMEM_ACTOR` impostato il campo diventa `porta/attore`, e la porta RESTA
(ws4 Paragone ha misurato la copertura del moat PER PORTA: CLI 99,2% contro
MCP 69,5%, quindi sostituirla spegnerebbe una misura viva).

⚠️ Cio' che questo banco NON copre, dichiarato: **l'SDK nudo**. Misurato su
store isolato, `Memory(path=db).add(...)` scrive `sdk:local` e l'attore
sparisce, perche' `Memory.__init__` fa `principal or "sdk:local"` senza
guardare l'ambiente. Quel comportamento e' fuori da questo file: qui si
sorveglia la porta CLI, che e' quella che il gruppo usa per salvare.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()

TESTO = "The depot in Rovigo holds 300 pallets."
FONTE = "Warehouse register, Rovigo site: 300 pallets in stock."


def _autore(corpus: Path, testo: str = TESTO) -> str | None:
    """Legge il campo dallo store che ha davvero ricevuto la scrittura.

    Si cerca il file invece di comporne il percorso: i due resolver dei dati
    (`CONFIG.data_dir` congelato all'import, `_compat.data_dir()` letto a ogni
    chiamata) possono puntare a due posti diversi, e un banco che indovina il
    percorso misura il proprio indovinello.
    """
    for db in sorted(corpus.rglob("semantic.db")):
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as c:
            r = c.execute(
                "SELECT writer_principal FROM facts WHERE proposition = ?",
                (testo,)).fetchone()
            if r is not None:
                return r[0]
    return None


@pytest.fixture
def salvato_con_attore(isolated_corpus: Path, monkeypatch) -> Path:
    monkeypatch.setenv("VERIMEM_ACTOR", "ws7:lanterna")
    r = runner.invoke(app, ["save", TESTO, "--topic", "magazzino/rovigo",
                            "--source", FONTE])
    assert r.exit_code == 0, r.output
    return isolated_corpus


@pytest.fixture
def salvato_senza_attore(isolated_corpus: Path, monkeypatch) -> Path:
    monkeypatch.delenv("VERIMEM_ACTOR", raising=False)
    monkeypatch.delenv("ENGRAM_ACTOR", raising=False)
    r = runner.invoke(app, ["save", TESTO, "--topic", "magazzino/rovigo",
                            "--source", FONTE])
    assert r.exit_code == 0, r.output
    return isolated_corpus


class TestIlNomeArrivaFinoAlCampo:

    def test_il_fatto_e_stato_scritto(self, salvato_con_attore):
        """Se questo cade, i due sotto direbbero `None` per il motivo
        sbagliato — e un banco che fallisce per la ragione sbagliata e'
        peggio di uno che non esiste."""
        assert _autore(salvato_con_attore) is not None, (
            "la scrittura non e' arrivata in nessuno store sotto il corpus "
            "isolato: il banco non sta misurando cio' che crede")

    def test_l_attore_e_nel_campo(self, salvato_con_attore):
        assert _autore(salvato_con_attore) == "cli:local/ws7:lanterna", (
            "VERIMEM_ACTOR non arriva in facts.writer_principal: la CLI sa "
            "chi e' (cli._principale() lo dice) e la riga scritta non lo "
            "riporta — chi indaghera' quel fatto non sapra' chi lo ha scritto")

    def test_la_porta_NON_si_perde(self, salvato_con_attore):
        """Sostituire la porta con l'attore spegnerebbe la copertura del moat
        per porta, che e' una misura viva."""
        assert (_autore(salvato_con_attore) or "").startswith("cli:local"), (
            "l'attore ha MANGIATO la porta invece di aggiungersi")


class TestLaPopolazioneOpposta:
    """Senza il braccio B, «c'e' scritto ws7:lanterna» non dimostra che sia
    stata la variabile a metterlo."""

    def test_senza_attore_resta_solo_la_porta(self, salvato_senza_attore):
        assert _autore(salvato_senza_attore) == "cli:local", (
            "chi non dichiara un attore non deve cambiare comportamento: i "
            "ritiri gia' scritti restano leggibili come prima")
