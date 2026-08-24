"""Il purge non è rotto: è SELETTIVO, e la selezione non è documentata.

Estende il finding GDPR di ws4 (24/08, `2a91ef6f`): con `VERIMEM_AUDIT_LOG=1`
un dato cancellato con `purge_history=True` sopravvive in
`adjudications.proposition`. Il suo sweep sui FILE era completo — «ogni colonna
di ogni tabella di ogni file nella data dir» — ma il caso di prova metteva il
segreto in **un campo solo**, la proposizione.

🔑 LO SWEEP HA PIÙ ASSI. Uno esaustivo sui contenitori non compensa un caso
incompleto sui contenuti: `trust_ledger` non conserva la proposizione, conserva
il **topic**, e per questo non compariva nel referto.

═══ ESITO 24/08 21:02 — db temporaneo, segreti finti, nessun corpus toccato ═══

    PROPOSIZIONE  prima 2 → dopo 1   adjudications.proposition
    TOPIC         prima 3 → dopo 2   adjudications.topic + trust_ledger.topic
    VERIFIED_BY   prima 1 → dopo 0   cancellato
    SOURCE        prima 1 → dopo 0   cancellato  (via facts.grounding_span)

⇒ Almeno TRE colonne su DUE tabelle in DUE file. E le due popolazioni contano
quanto il difetto: `source` e `verified_by` vengono puliti davvero, quindi la
frase giusta non è «il purge non funziona» ma «il purge sceglie, e la scelta
non è scritta da nessuna parte».

⚠️ IL TOPIC È IL CAMPO PEGGIORE, per una ragione che il prodotto GIÀ SA. Il
commento dell'injection screen in `semantic.py` dice che «anche il TOPIC è
caller-controlled e viene ritornato verbatim dal recall» — ed è per questo che
lo scansiona contro le iniezioni. ⇒ Il gate sa che il topic è testo dell'utente
quando deve DIFENDERSI, e lo dimentica quando deve CANCELLARE. E la gente ci
mette nomi: `clienti/mario-rossi`.

⛔ IL CONTROLLO POSITIVO NON È UN ORNAMENTO, ed è il motivo per cui ogni riga
stampa il PRIMA. La prima stesura misurava solo il dopo, dava `0` sulla SOURCE
e stavo per consegnare «la source è salva»: il fatto era `quarantined` e non
toccava nemmeno la tabella degli adjudications. **Uno zero da "non c'era mai" è
indistinguibile da uno zero da "è stato cancellato".**
"""
from __future__ import annotations

import glob
import os
import pathlib
import sqlite3
import sys
import tempfile


def _occorrenze(data_dir: str, segreto: str) -> tuple[int, list[str]]:
    """Ogni colonna di ogni tabella di ogni .db sotto la data dir."""
    totale, dove = 0, []
    for f in glob.glob(os.path.join(data_dir, "**", "*.db"), recursive=True):
        try:
            c = sqlite3.connect("file:%s?mode=ro" % f.replace("\\", "/"), uri=True)
        except Exception:
            continue
        try:
            tabelle = [r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            for tab in tabelle:
                try:
                    cols = [x[1] for x in c.execute("PRAGMA table_info(%s)" % tab)]
                except Exception:
                    continue
                for col in cols:
                    try:
                        n = c.execute(
                            "SELECT COUNT(*) FROM %s WHERE CAST(%s AS TEXT) LIKE ?"
                            % (tab, col), ("%" + segreto + "%",)).fetchone()[0]
                    except Exception:
                        continue
                    if n:
                        totale += n
                        dove.append("%s:%s.%s" % (pathlib.Path(f).name, tab, col))
        finally:
            c.close()
    return totale, sorted(set(dove))


def main() -> None:
    d = tempfile.mkdtemp()
    os.environ["HIPPO_DATA_DIR"] = d
    os.environ["VERIMEM_AUDIT_LOG"] = "1"
    from verimem import Memory                      # noqa: PLC0415

    m = Memory(path=os.path.join(d, "s.db"))
    print("data dir temporanea:", d)
    print("VERIMEM_AUDIT_LOG=1  ·  segreti FINTI  ·  nessun corpus toccato\n")

    casi = [
        ("PROPOSIZIONE", dict(
            proposition="Il codice pratica del cliente e QQPROP7777.",
            topic="clienti/x", source="Modulo firmato dal cliente."), "QQPROP7777"),
        ("TOPIC", dict(
            proposition="Il cliente ha completato la registrazione.",
            topic="clienti/TOPICPII5150",
            source="Modulo firmato dal cliente."), "TOPICPII5150"),
        ("VERIFIED_BY", dict(
            proposition="Il cliente ha completato la registrazione ieri.",
            topic="clienti/x", source="Modulo firmato dal cliente.",
            verified_by=["operatore:VBYPII6161"]), "VBYPII6161"),
        ("SOURCE", dict(
            proposition="Il cliente ha completato la registrazione oggi.",
            topic="clienti/x",
            source="Modulo firmato: pratica ZZSRC9999, cliente registrato."),
         "ZZSRC9999"),
    ]

    esiti = []
    for nome, kw, segreto in casi:
        prop = kw.pop("proposition")
        r = m.add(prop, **kw)
        prima, dove_prima = _occorrenze(d, segreto)
        m.delete(r.get("id"), purge_history=True)
        dopo, dove_dopo = _occorrenze(d, segreto)
        if not prima:
            print("⛔ %s: IL BANCO NON MISURA — il segreto non era in nessun "
                  "campo PRIMA del purge, quindi lo zero DOPO non significa "
                  "niente." % nome)
            esiti.append((nome, "NON MISURATO", "", ""))
            continue
        verdetto = "SOPRAVVIVE" if dopo else "cancellato"
        esiti.append((nome, verdetto, prima, dopo))
        print("%-13s prima %d %-58s" % (nome, prima, dove_prima))
        print("%-13s dopo  %d %-58s  <- %s"
              % ("", dopo, dove_dopo, verdetto))
        print()

    print("=== SINTESI ===")
    for nome, verdetto, prima, dopo in esiti:
        print("  %-13s %s  (%s -> %s)" % (nome, verdetto, prima, dopo))
    vivi = [n for n, v, _, _ in esiti if v == "SOPRAVVIVE"]
    print("\ncampi che SOPRAVVIVONO al purge: %s" % (vivi or "nessuno"))
    if not any(v == "NON MISURATO" for _, v, _, _ in esiti):
        print("(ogni riga ha il suo controllo positivo: PRIMA > 0)")
    sys.exit(0)


if __name__ == "__main__":
    main()
