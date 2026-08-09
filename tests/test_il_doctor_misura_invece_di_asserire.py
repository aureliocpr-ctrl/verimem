"""Il doctor misura la causa, invece di asserirne una.

Catena documentata, 2026-08-05, e vale più del difetto:
1. `verimem doctor` scrive «the moat runs only on writes that carry a
   source, AND on the MCP channel the judge loads in the background:
   writes that arrive while it is warming are admitted unjudged».
2. ws5 legge quella riga e me la passa come misura.
3. Io la metto in due messaggi di commit e in un commento del codice.
4. ws5 la MISURA (4 thread simultanei, store vergine, canale SDK): tutti
   aspettano 42.60s e ricevono un verdetto — **0 NULL su 4** — e la
   ritira.
🔑 Nessuno aveva inventato niente: il prodotto asseriva un meccanismo
osservato UNA volta su UN canale (il commento nel sorgente lo dice:
«misurata il 2026-07-30»), e chi legge non ha modo di distinguere una
misura da una generalizzazione.

E c'è il seguito che rende la riga dannosa e non solo imprecisa. Le due
cause non pesano uguale, e il doctor le mette sullo stesso piano —
misurato sul corpus reale:

    fatti 8267 · giudicati 1790
    senza fonte dichiarata e senza verdetto:  6445
    CON fonte dichiarata e senza verdetto:      32

L'operatore che legge va a impostare `ENGRAM_GROUNDING_WRITE=1` per
inseguire 32 fatti mentre 6445 aspettano una fonte. Il conto che separa
le due popolazioni il doctor può FARLO — la colonna `source_signature`
è lì — quindi la cura non è ammorbidire la frase: è sostituire
l'asserzione con la misura, e ordinare il consiglio per grandezza.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory

_FONTE = "Company handbook: our head office is located in Milan, Italy."


def _check(nome: str) -> dict:
    from verimem.doctor import run_doctor
    return next(c for c in run_doctor() if c["name"] == nome)


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(tmp_path / "semantic" / "semantic.db")
    for i in range(6):
        m.add(f"the depot number {i} is in Turin", topic=f"hq/{i}")
    # uno solo con una fonte DICHIARATA e senza verdetto: la popolazione
    # che il messaggio confonde con l'altra
    r = m.add("the head office is in Milan", topic="hq/sede")
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET source_signature = ?, "
                    "grounding_score = NULL WHERE id = ?", ("sha:banco", r["id"]))
    return m


def test_riporta_lo_SCARTO_fra_le_due_cause(store):
    """Non «ci sono due cause» ma quante righe pesa ciascuna."""
    c = _check("moat-judge")
    testo = c["detail"]
    assert "6" in testo and "1" in testo
    assert "source" in testo.lower()
    # la popolazione discriminante ha un numero suo
    assert "declared a source" in testo.lower() or "with a source" in testo.lower()


def test_non_asserisce_il_meccanismo_del_warming(store):
    """La frase che ha innescato la catena non può tornare come
    asserzione. Se il warming va nominato, va nominato come una delle
    cause POSSIBILI della popolazione «fonte dichiarata, nessun
    verdetto», con la sua provenienza — non come proprietà del
    prodotto."""
    testo = (_check("moat-judge").get("detail") or "").lower()
    assert "are admitted unjudged" not in testo, testo
    if "warming" in testo:
        assert ("observed" in testo or "one" in testo or "possible" in testo
                or "may" in testo), (
            "se nomina il warming deve dire che e' un'ipotesi, non un fatto")


def test_il_consiglio_mette_PRIMA_la_causa_piu_grande(store):
    """Un consiglio che elenca due rimedi in ordine arbitrario manda
    l'operatore sul più piccolo: sul corpus reale sarebbe andato a
    inseguire 32 fatti lasciandone indietro 6445."""
    fix = (_check("moat-judge").get("fix") or "").lower()
    assert fix, "un WARN senza rimedio non e' un referto"
    i_source = fix.find("source")
    i_env = fix.find("engram_grounding_write")
    assert i_source >= 0
    if i_env >= 0:
        assert i_source < i_env, fix


def test_un_corpus_tutto_giudicato_non_allarma(tmp_path, monkeypatch):
    """La guardia contro il referto che grida sempre: se la copertura è
    alta il check non deve inventarsi un problema."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    m = Memory(tmp_path / "semantic" / "semantic.db")
    r = m.add("the head office is in Milan", topic="hq", source=_FONTE)
    with sqlite3.connect(m.semantic.db_path) as con:
        con.execute("UPDATE facts SET grounding_score = 99.0 WHERE id = ?",
                    (r["id"],))
    c = _check("moat-judge")
    assert c["status"] != "warn" or "6445" not in c["detail"]


def test_non_promette_un_avviso_che_le_scritture_senza_fonte_non_ricevono(
        tmp_path, monkeypatch):
    """Quarta istanza della stessa classe, e la più rassicurante — che è
    la peggiore specie.

    Senza giudice il doctor diceva «writes are admitted with an
    L4-skipped advisory (moat OFF)». Misurato, con giudice assente:

        add(testo)                      -> warnings []          ← NESSUN avviso
        add(testo, source="…")          -> warnings [L4-skipped]

    Cioè l'avviso esiste solo per le scritture che portano una fonte. Per
    tutte le altre — 6445 su 8267 sul corpus reale — il fatto entra in
    silenzio, e chi legge quella riga crede che il prodotto lo avvisi.
    """
    from verimem import doctor

    monkeypatch.setattr("verimem.local_grounding.local_ce_available",
                        lambda *a, **k: False)
    monkeypatch.setattr("verimem.llm._autodetect_provider",
                        lambda *a, **k: None)
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))

    c = next(x for x in doctor.run_doctor() if x["name"] == "moat-judge")
    testo = c["detail"].lower()
    assert "l4-skipped" in testo
    assert "source" in testo, (
        "l'avviso vale solo per le scritture CON fonte, e la riga deve dirlo: "
        + c["detail"])
    assert ("no advisory" in testo or "silently" in testo
            or "nothing to check" in testo), c["detail"]


def test_la_stessa_frase_su_entrambe_le_superfici(tmp_path):
    """`doctor` e `verimem warmup` dicevano la stessa cosa con due frasi
    scritte a mano: due copie divergono, ed è la prima delle tre classi
    che questo prodotto ripete. Una sola definizione, importata da
    entrambe."""
    import verimem.cli as _cli
    from verimem.doctor import AVVISO_SENZA_GIUDICE

    assert "source" in AVVISO_SENZA_GIUDICE.lower()
    sorgente = __import__("pathlib").Path(_cli.__file__).read_text(
        encoding="utf-8")
    assert "AVVISO_SENZA_GIUDICE" in sorgente, (
        "la CLI riscrive la frase invece di importarla")


def test_la_provenienza_legge_ramo_E_revisione_anche_da_un_worktree(
        tmp_path, monkeypatch):
    """Il caso che mi è sfuggito alla prima stesura, ed è il caso NORMALE
    qui: in un worktree `.git` è un file che punta altrove, e i ref non
    stanno in quella gitdir ma nel repo principale (file `commondir`).
    Leggendo solo la gitdir usciva il ramo senza revisione — metà
    risposta, e la metà mancante è quella che distingue due checkout
    fermi sullo stesso ramo.

    Banco deterministico: un finto worktree costruito a mano, così il
    test non dipende dal fatto che la suite girchi dentro un albero git.
    """
    from verimem import doctor

    principale = tmp_path / "repo" / ".git"
    (principale / "refs" / "heads" / "ws6").mkdir(parents=True)
    (principale / "refs" / "heads" / "ws6" / "control-room").write_text(
        "deadbeefcafebabe0123456789abcdef01234567\n", encoding="utf-8")
    wt = principale / "worktrees" / "albero"
    wt.mkdir(parents=True)
    (wt / "HEAD").write_text("ref: refs/heads/ws6/control-room\n",
                             encoding="utf-8")
    (wt / "commondir").write_text("../..\n", encoding="utf-8")

    pacchetto = tmp_path / "albero" / "verimem"
    pacchetto.mkdir(parents=True)
    (tmp_path / "albero" / ".git").write_text(f"gitdir: {wt}\n",
                                              encoding="utf-8")
    monkeypatch.setattr(doctor, "__file__", str(pacchetto / "doctor.py"))

    out = doctor._provenienza_del_codice()
    assert "ws6/control-room" in out, out
    assert "deadbeef" in out, "il ramo senza revisione e' meta' risposta: " + out


def test_dice_QUALE_codice_gira_non_solo_la_versione(store):
    """Cinque istanze lavorano sullo stesso repo da checkout diversi, e
    `verimem 0.7.0` è identico in tutti: la versione non distingue.

    Stanotte è costato tre volte — ws5 ha misurato il ramo di ws3
    credendolo il main, ws4 ha contato le tabelle nel file sbagliato, e
    ws1 ha dovuto fare `git merge-base` + `grep` per scoprire che il
    prodotto in esecuzione NON conteneva la cura appena verificata. Il
    doctor deve dire da quale albero sta girando il codice."""
    import verimem
    c = _check("version")
    testo = c["detail"]
    assert "verimem" in testo
    # il percorso del pacchetto: e' l'unica cosa che distingue due checkout
    radice = str(verimem.__file__).rsplit("verimem", 1)[0].rstrip("\\/")
    assert radice.split("\\")[-1].split("/")[-1] in testo, testo
