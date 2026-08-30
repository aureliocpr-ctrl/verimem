"""«pass llm= to Memory» non dice DOVE, e chi legge `doctor` e' spesso alla CLI.

IL REPERTO, letto nel sorgente il 2026-08-30 e verificato alla porta. Sei punti
fra `doctor` e `cli` offrivano lo stesso rimedio::

    cli.py:606      "pass llm= to Memory for the llm judge."
    doctor.py:679   "the moat runs only when you pass llm=... to Memory"
    doctor.py:680   "or pass llm= to Memory"
    doctor.py:745   "the moat runs only when you pass llm=... to Memory"
    doctor.py:748   "pass llm= to Memory"
    doctor.py:755   "or pass llm= to Memory"

⚠️ `Memory(llm=...)` esiste **solo nell'SDK Python** (`client.py:376`). Un
chiamante della **CLI** non ha un modo di iniettarlo (`--use-llm` esiste, ma e'
di `facts archive-narration`, un comando di manutenzione, non del percorso di
scrittura); un chiamante **MCP** nemmeno — li' il giudice llm viene dall'agente
costruito dal SERVER (`mcp_server.py:12936`), cioe' e' una scelta
dell'**operatore**, non del chiamante.

⇒ **Chi esegue `verimem doctor` lo esegue dalla CLI**, e leggeva un rimedio che
su quella porta non puo' applicare. Il testo non era falso: era **incompleto nel
punto in cui serviva**, ed e' la stessa forma dell'`AVVISO_SENZA_GIUDICE`, che
il file 63 righe piu' su descrive cosi': *«diceva il vero e diceva TROPPO
POCO»*.

🔑 LA CURA SEGUE IL PATTERN CHE IL PRODOTTO HA GIA': **una frase sola**. Il
commento di `cli.py:600` lo dichiara — *«la frase NON si riscrive qui: e' la
stessa del doctor, e due copie divergono (misurato: quella scritta a mano
prometteva un avviso che le scritture senza fonte non ricevono mai)»*. Sei copie
erano sei occasioni di divergere: ora c'e' `RIMEDIO_LLM` accanto ad
`AVVISO_SENZA_GIUDICE`.

⚠️ COSA E' LETTO E COSA E' MISURATO, distinto: che l'SDK abbia `llm=` e la CLI
no e' **letto** nel sorgente (e' una disponibilita' di API, non un
comportamento). Che il testo esca dalla porta con la qualificazione e'
**misurato**, eseguendo `run_doctor()` con il modello reso assente.
"""

from __future__ import annotations

import inspect

from verimem import cli as _cli
from verimem import doctor as _doctor


def test_la_frase_del_rimedio_esiste_una_volta_sola():
    """La fonte unica, come `AVVISO_SENZA_GIUDICE`."""
    assert isinstance(_doctor.RIMEDIO_LLM, str) and _doctor.RIMEDIO_LLM


def test_il_rimedio_nomina_la_porta_su_cui_e_eseguibile():
    """IL CUORE: senza la porta, il rimedio non e' azionabile da chi lo legge."""
    testo = _doctor.RIMEDIO_LLM
    assert "SDK" in testo, testo
    assert "CLI" in testo and "MCP" in testo, testo


def test_il_rimedio_distingue_il_chiamante_dall_operatore():
    """Su MCP l'llm si puo' avere: lo configura l'OPERATORE, non il chiamante.
    Dire solo «non si puo'» sarebbe l'errore opposto."""
    testo = _doctor.RIMEDIO_LLM
    assert "OPERATOR" in testo or "operator" in testo, testo


def test_nessuna_copia_sparsa_della_frase():
    """⚠️ IL PRESIDIO CHE VALE: sei copie erano sei occasioni di divergere, e il
    file accanto dichiara di aver gia' pagato quella divergenza una volta."""
    sorgenti = {
        "doctor.py": inspect.getsource(_doctor),
        "cli.py": inspect.getsource(_cli),
    }
    for nome, testo in sorgenti.items():
        senza_costante = testo.replace(_doctor.RIMEDIO_LLM, "")
        # ⚠️ SI CONTA IL CODICE, NON I COMMENTI: la cronaca del difetto CITA
        #    la frase vecchia, ed e' giusto che lo faccia. Alla prima stesura
        #    questo test contava anche quella citazione e diventava rosso su
        #    se stesso — il difetto era nel misuratore, non nel modulo.
        codice = "\n".join(r for r in senza_costante.splitlines()
                           if not r.lstrip().startswith("#"))
        residue = codice.count("pass llm= to Memory")
        assert residue == 0, (
            f"{nome} ha ancora {residue} copie a mano del rimedio: "
            f"e' esattamente cio' che il commento di cli.py:600 dice di non fare")


def test_alla_porta_chi_nomina_llm_nomina_anche_la_porta(monkeypatch, tmp_path):
    """MISURATO, non letto — e l'asserzione vale su OGNI ramo.

    ⚠️ LA PRIMA STESURA PRETENDEVA LA STRINGA DA UN RAMO CHE IN QUEL REGIME
    NON VIENE PERCORSO: senza alcun provider llm, `doctor` sceglie il ramo
    che dice solo «togli la cartella e rilancia warmup» — ed e' GIUSTO che
    non suggerisca un giudice llm quando non ce n'e' nessuno. Il difetto
    era nel misuratore: pretendeva un ramo invece di presidiare la regola.
    La regola presidiata qui vale ovunque: **se il testo nomina `llm=`,
    deve nominare anche la porta su cui e' eseguibile.**
    """
    vuota = tmp_path / "senza-giudice"
    vuota.mkdir()
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(vuota))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    righe = [c for c in _doctor.run_doctor() if c.get("name") == "moat-judge"]
    assert righe, "doctor non emette piu' la riga moat-judge: parser da rivedere"
    for campo in ("detail", "fix"):
        testo = str(righe[0].get(campo, ""))
        if "llm=" not in testo:
            continue
        assert "SDK" in testo and "MCP" in testo, (
            f"il campo {campo} nomina `llm=` senza dire su quale porta: {testo}")
