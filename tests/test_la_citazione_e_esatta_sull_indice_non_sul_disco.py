"""La citazione dei documenti promette l'INDICE, non il disco — e qui si prova.

PERCHE' QUESTO FILE ESISTE. Il contratto degli agenti diceva «exact citations»,
e la frase era vera quando i documenti indicizzati erano due in una cartella
stabile. E' diventata falsa quando ne sono stati indicizzati ventisette da una
directory temporanea: misurato il 2026-08-12 sul corpus reale, **538 chunk su
634 (84,9%) puntavano a file che non esistevano piu'**, mentre il testo del
chunk era presente per il **100%** di essi. Nessun test e' diventato rosso,
perche' nessun test collegava quella frase a un comportamento.

Da qui la regola che questo file applica: **una promessa scritta senza un test
che la verifichi e' un fatto senza fonte** — la regola del gate, applicata al
contratto invece che al database.

I tre test coprono le tre meta' della promessa riscritta:
  1. l'offset e' esatto SULL'INDICE          -> ``indexed_text[start:end] == text``
  2. il testo resta servito ANCHE SE il file sparisce (e' cio' che la promessa
     ora garantisce, ed e' il caso che ha generato tutto)
  3. il contratto NON promette piu' che il file si riapra

Il test 2 e' anche un GUARDIANO CONTRO LA CURA SBAGLIATA: la prima cura che mi
era venuta in mente era filtrare i risultati con ``Path(source_id).exists()``.
Con quel filtro, un documento indicizzato da una directory poi ripulita
sparirebbe dalla ricerca insieme al suo testo — cioe' perderemmo il 100% che
funziona per nascondere l'84,9% che non si riapre. Se qualcuno introduce quel
filtro, il test 2 diventa rosso.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from verimem.document_index import DocumentIndex


class FakeEmbedder:
    """Deterministic bag-of-words hashing embedder (32-dim, L2-normalized)."""

    DIM = 32

    def encode(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.DIM
            for tok in re.findall(r"[a-z0-9]+", (t or "").lower()):
                v[hash(tok) % self.DIM] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


_TESTO = (
    "Il magazzino di Rovigo contiene 480 pallet di merce varia. "
    "La consegna del lunedi' arriva alle sette del mattino. "
    "Il responsabile registra ogni movimento su un registro cartaceo. "
) * 4


def _indice(tmp_path) -> DocumentIndex:
    return DocumentIndex(db_path=tmp_path / "docidx.db", embedder=FakeEmbedder(),
                         chunk_size=200, overlap=40)


def test_l_offset_e_esatto_sul_testo_indicizzato(tmp_path) -> None:
    """``indexed_text[start:end] == text`` — la meta' della promessa che regge sempre."""
    doc = tmp_path / "magazzino.txt"
    doc.write_text(_TESTO, encoding="utf-8")
    ix = _indice(tmp_path)
    ix.index_file(doc)

    hits = ix.search("pallet magazzino", k=3)
    assert hits, "il documento indicizzato deve essere trovabile"
    for h in hits:
        assert _TESTO[h["start"]:h["end"]] == h["text"], (
            f"offset non esatto sull'indice: [{h['start']}:{h['end']}] "
            f"non corrisponde al testo del chunk"
        )


def test_il_testo_resta_servito_anche_se_il_file_sparisce(tmp_path) -> None:
    """La promessa riscritta: il TESTO e' sempre disponibile, il FILE puo' non esserlo.

    E' il caso reale — 27 documenti su 29 indicizzati da una scratchpad poi
    ripulita. Questo test diventa ROSSO se qualcuno filtra i risultati per
    esistenza del file: sarebbe perdere il 100% che funziona per nascondere
    l'84,9% che non si riapre.
    """
    doc = tmp_path / "sparira.txt"
    doc.write_text(_TESTO, encoding="utf-8")
    ix = _indice(tmp_path)
    ix.index_file(doc)

    prima = ix.search("pallet magazzino", k=3)
    assert prima, "precondizione: il documento e' trovabile finche' il file esiste"

    doc.unlink()
    assert not doc.exists(), "precondizione del caso reale: il file non c'e' piu'"

    dopo = ix.search("pallet magazzino", k=3)
    assert dopo, (
        "il chunk deve restare servito anche senza il file: il testo vive "
        "nell'indice, non sul disco"
    )
    assert [h["text"] for h in dopo] == [h["text"] for h in prima], (
        "sparito il file, il TESTO servito deve essere identico a prima"
    )
    assert all(h["text"].strip() for h in dopo), "il testo del chunk non puo' essere vuoto"
    # e la citazione continua a nominare il file: e' provenienza, non garanzia
    assert all(h["source_id"] for h in dopo)


def test_il_contratto_non_promette_piu_che_il_file_si_riapra() -> None:
    """Criterio B applicato alla lettera: la frase del contratto ha un test.

    Rosso se qualcuno rimette un «exact citations» nudo nella guida che ogni
    agente legge, senza dire su COSA la citazione e' esatta.
    """
    guida = Path(__file__).resolve().parents[1] / "verimem" / "agent_guide.py"
    testo = guida.read_text(encoding="utf-8")

    assert "verimem_document_semantic_search" in testo, (
        "precondizione: la guida deve ancora descrivere la ricerca sui documenti "
        "(se il nome dello strumento cambia, aggiorna QUESTO test, non toglierlo)"
    )
    assert "(exact citations)." not in testo, (
        "la guida promette di nuovo «exact citations» senza dire su cosa: "
        "misurato l'84,9% dei chunk punta a file spariti"
    )
    for atteso in ("indexed text", "no longer opens"):
        assert atteso in testo, (
            f"la guida non dichiara piu' il limite della citazione: manca «{atteso}»"
        )
