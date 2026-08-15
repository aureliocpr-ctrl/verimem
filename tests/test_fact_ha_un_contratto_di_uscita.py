"""Un fatto che esce dal prodotto porta con se' cio' che il prodotto sa di lui.

Misurato il 2026-07-30 su mcp_server.py — 13 punti costruiscono a mano il dict
di un fatto, e ognuno decide da solo quali campi metterci:

    proposition        13/13     (il campo del giorno uno)
    grounding_score     6/13
    asserted_at         2/13
    valid_until         1/13
    derives_from        1/13
    confidence_tier     0/13
    epistemic           0/13
    writer_principal    0/13
    last_verified_at    0/13

`Fact` ha 26 campi e nessun metodo di uscita, quindi ogni superficie riparte da
zero. Non e' che undici superfici hanno un bug: e' che non esiste un contratto,
e senza contratto la probabilita' di dimenticare un campo e' quella misurata —
sette punti su tredici hanno dimenticato il verdetto.

Il costo si vede sui campi appesi in coda al dataclass col tempo. Quattro sono
calcolati, persistiti e documentati col loro razionale, e NON ESCONO DA NESSUNA
SUPERFICIE: il tier di confidenza del giudice (v15), l'etichetta epistemica
proven/unbeaten/refuted (v14), l'identita' server-stamped di chi ha scritto
(anti-spoof, mai presa dagli argomenti del tool), e quando il fatto e' stato
verificato l'ultima volta. Il prodotto li calcola, li conserva, e nessun utente
puo' leggerli.

`test_ogni_campo_del_dataclass_e_deciso` e' l'invariante che chiude la classe:
il campo numero 27 non potra' nascere invisibile, perche' chi lo aggiunge dovra'
dire se esce o perche' no.
"""
from __future__ import annotations

import dataclasses
import pathlib
import re

import pytest

from verimem.semantic import Fact

#: Campi che di proposito NON escono, col motivo. Sta qui e non nel codice
#: perche' un'esclusione deve costare una riga di spiegazione a chi la fa.
NON_ESCONO = {
    "source_signature": "impronta interna anti-tamper, non dice nulla al lettore",
}


def test_un_fatto_sa_uscire():
    f = Fact(proposition="x", topic="t")
    p = f.as_payload()
    assert isinstance(p, dict) and p["proposition"] == "x"


def test_il_verdetto_c_e_sempre_anche_quando_manca():
    """Assente e null non sono la stessa cosa.

    Una chiave che manca si legge «questa superficie non espone il verdetto»;
    un null esplicito si legge «il moat non ha girato». Il prodotto vende
    esattamente quella distinzione, quindi il verdetto e' l'unico campo che
    esce anche vuoto.
    """
    p = Fact(proposition="x").as_payload()
    assert "grounding_score" in p and p["grounding_score"] is None
    q = Fact(proposition="x", grounding_score=99.9).as_payload()
    assert q["grounding_score"] == 99.9


def test_i_campi_vuoti_non_gonfiano_il_payload():
    """Ogni chiave inutile e' contesto rubato a chi legge dall'altra parte."""
    p = Fact(proposition="x").as_payload()
    assert "epistemic" not in p, "un campo mai valorizzato non deve uscire"
    assert "superseded_by" not in p
    q = Fact(proposition="x", epistemic={"kind": "proven"}).as_payload()
    assert q["epistemic"] == {"kind": "proven"}


def test_i_quattro_campi_invisibili_ora_escono():
    """I quattro che 0 superfici su 13 mostravano.

    ⚠️ `last_verified_at` ha una CONDIZIONE, ed è una decisione presa dopo
    che questo banco fu scritto (`fact_contract.verifica_sostenuta`,
    misurata il 2026-08-07): il campo si chiama come se registrasse una
    verifica e non lo fa — avanza su 2762 fatti, fino a 87 giorni dopo la
    scrittura, e **zero** di quelli hanno un `grounding_score`. Si muove
    dove un giudizio non c'è mai stato: un tocco, non un verdetto.
    ⇒ Esce **solo quando poggia su un verdetto**, e questo banco costruiva
    il fatto senza `grounding_score` — chiedeva quindi che uscisse anche
    quando è la data di un re-embedding. Il rosso era il banco.
    """
    f = Fact(proposition="x", confidence_tier="high", writer_principal="sdk:local",
             last_verified_at=1234.0, grounding_score=91.0,
             epistemic={"kind": "unbeaten"})
    p = f.as_payload()
    for campo in ("confidence_tier", "writer_principal", "last_verified_at",
                  "epistemic"):
        assert campo in p, f"{campo} continua a non uscire"


def test_last_verified_at_NON_esce_quando_nessun_verdetto_lo_sostiene():
    """L'altra popolazione, che è il motivo per cui la condizione esiste.

    Un banco che guarda solo il caso positivo direbbe «il campo esce» e
    resterebbe verde anche se la condizione sparisse — cioè se tornassimo a
    pubblicare come «ultima verifica» la data di una migrazione.
    """
    f = Fact(proposition="x", last_verified_at=1234.0)  # nessun grounding_score
    assert "last_verified_at" not in f.as_payload(), (
        "il campo esce senza un verdetto che lo sostenga: e' la data di un "
        "tocco pubblicata come se fosse una verifica"
    )


def test_ogni_campo_del_dataclass_e_deciso():
    """L'invariante che chiude la classe.

    Il campo numero 27 non puo' nascere invisibile: o esce, o e' in NON_ESCONO
    con scritto perche'. Senza questo, ogni campo aggiunto in futuro ripete la
    storia di confidence_tier — calcolato, persistito, e mai letto da nessuno.
    """
    pieno = Fact(
        proposition="x", topic="t", source_episodes=["e1"], superseded_by="s",
        superseded_at=1.0, superseded_reason="r", verified_by=["v"],
        source_signature="sig", trigger_keywords=["k"], applicable_when="w",
        worked_example="ex", lineage_to=["l"], writer_principal="p",
        # NON i default: il payload omette un campo che vale quanto il suo
        # default, perche' ripeterlo e' peso senza informazione. Costruirlo
        # col default renderebbe questo test un falso allarme sul contratto —
        # e infatti l'ha dato, la prima volta.
        writer_role="user",
        last_verified_at=2.0, valid_until=3.0, derives_from=["d"],
        grounding_score=50.0, confidence_tier="high", asserted_at=4.0,
        epistemic={"kind": "proven"},
        # il campo 28, aggiunto il 08/08 con la migrazione v17: la PORZIONE di
        # fonte che sostiene il fatto. Questo test l'ha preso il giorno dopo,
        # ed e' esattamente il suo mestiere — ma il difetto era QUI, non nel
        # prodotto: `fact_payload` lo espone gia' correttamente quando ha un
        # valore (misurato: Fact(grounding_span=...).as_payload() lo contiene).
        # Il banco lo omettiva, il campo restava al default, e il contratto lo
        # contava fra i dimenticati.
        # ⚠️ Chi aggiunge il campo 29 rompera' questo test allo stesso modo, ed
        # e' voluto: la lista si scrive a mano perche' NESSUN campo entri senza
        # che qualcuno decida se chi legge il fatto deve vederlo.
        grounding_span="480 pallet a scaffale",
    )
    esce = set(pieno.as_payload())
    tutti = {f.name for f in dataclasses.fields(Fact)}
    dimenticati = tutti - esce - set(NON_ESCONO)
    assert not dimenticati, (
        f"campi del dataclass che non escono e non sono dichiarati: "
        f"{sorted(dimenticati)}\naggiungili al payload, oppure a NON_ESCONO "
        f"scrivendo perche' non servono a chi legge.")
    assert not (set(NON_ESCONO) - tutti), (
        "NON_ESCONO nomina campi che il dataclass non ha piu'")


@pytest.mark.parametrize("campo,valore", [
    ("grounding_score", 88.5), ("confidence_tier", "borderline"),
    ("status", "quarantined"), ("verified_by", ["pytest:x_PASS"]),
])
def test_il_valore_non_viene_trasformato(campo, valore):
    """Il payload trasporta, non interpreta."""
    p = Fact(proposition="x", **{campo: valore}).as_payload()
    assert p[campo] == valore


def test_le_due_liste_dei_campi_non_si_contraddicono() -> None:
    """Cio' che una superficie SORVEGLIA non puo' essere cio' che un'altra ESCLUDE.

    DUE ELENCHI, IN DUE FILE, CHE NON SI SONO MAI PARLATI. Misurato il
    2026-08-15 con `git grep -l`: nessun file cita entrambi.

        NON_ESCONO   `verimem/fact_contract.py`   «questo campo NON esce da MCP»
        SOLO_MCP     `tests/test_la_garanzia_si_scriveva_e_non_si_rileggeva.py`
                     «questi campi devono uscire da MCP *e* dall'SDK»

    Oggi la loro intersezione e' vuota — **per fortuna, non per costruzione**.
    Il giorno in cui un campo sorvegliato entrasse in ``NON_ESCONO`` per una
    buona ragione, questo caso fallisce QUI, nel file che gia' possiede
    ``NON_ESCONO``, invece di lasciare la contraddizione in piedi.

    📌 AGGIORNATO IL 2026-08-15, e il motivo vale piu' della riga cambiata.
    Qui c'era scritto che il collaudo laggiu' **non sarebbe diventato rosso, si
    sarebbe spento**, perche' saltava quando il campo non usciva da MCP. Vero
    quando fu scritto; non piu': quello skip e' stato sostituito da un assert
    (`test_la_garanzia_si_scriveva_e_non_si_rileggeva.py`), misurato prima
    (8 passed, 0 skipped: non scattava mai) e falsificato dopo (dove saltava,
    ora e' rosso).

    ⇒ I due casi **non si sostituiscono**, e conviene dirlo perche' la
    tentazione di togliere questo e' reale ora che laggiu' suona: quello
    verifica il PRODOTTO — un campo di ``SOLO_MCP`` esce davvero da MCP —
    questo verifica i due ELENCHI, e li verifica *senza costruire un fatto*,
    quindi parla anche quando il prodotto non e' interrogabile. Togline uno e
    l'altro non copre il suo verso.

    ⚠️ PERIMETRO, dichiarato. Il verso opposto e' gia' coperto e non da questo
    caso: se il prodotto esclude un campo che l'elenco qui sopra non dichiara,
    ``test_ogni_campo_del_dataclass_esce_o_e_dichiarato`` lo trova fra i
    «dimenticati» e fallisce. Qui si copre il verso che nessuno guardava —
    **escludere un campo che UN ALTRO FILE sta sorvegliando**.
    """
    percorso = pathlib.Path(__file__).with_name(
        "test_la_garanzia_si_scriveva_e_non_si_rileggeva.py")
    if not percorso.exists():  # il file e' stato rinominato o tolto
        pytest.skip(f"{percorso.name} non esiste piu': aggiorna questo riferimento")

    testo = percorso.read_text(encoding="utf-8")
    trovato = re.search(r"^SOLO_MCP\s*=\s*\[([^\]]*)\]", testo, re.MULTILINE)
    assert trovato, (
        f"{percorso.name} non dichiara piu' SOLO_MCP nella forma attesa: "
        f"questo caso non puo' piu' leggerlo, e va aggiornato invece che tolto"
    )
    sorvegliati = set(re.findall(r'"([a-z_]+)"', trovato.group(1)))
    assert sorvegliati, "SOLO_MCP e' stato letto ma risulta vuoto: parsing da rivedere"

    contraddetti = sorvegliati & set(NON_ESCONO)
    assert not contraddetti, (
        f"campi insieme SORVEGLIATI e ESCLUSI: {sorted(contraddetti)}.\n"
        f"Un campo in SOLO_MCP deve uscire da MCP e dall'SDK; un campo in "
        f"NON_ESCONO non esce da MCP. Le due cose non stanno insieme: "
        f"decidete quale vale, perche' finche' restano entrambe il collaudo "
        f"che sorveglia la divergenza SALTA invece di fallire."
    )
