"""`indexed_text[start:end] == passage` — la promessa del README, presidiata.

`README.md:202-207` promette, del tier documenti:

    semantic search returns passages with source, version and character
    offsets, where `indexed_text[start:end] == passage`

E' una delle poche righe della vetrina verificabile con un `==`. Misurata il
2026-08-29 fuori da pytest, con il modello vero, su quattro file scelti per
romperla: 7 chunk su 7 reggono.

PERCHE' LO STUB NON FALSA QUESTO TEST — e va detto, perche' sotto `pytest`
l'embedder e' lo stub SHA-256 di `conftest` e ogni misura che passa da un coseno
sarebbe priva di significato: qui non si misura il RANKING ma la CITAZIONE.
Quali chunk tornino, e in quale ordine, e' irrilevante: di ognuno si verifica
che gli offset ritaglino esattamente il testo restituito. Con un embedder finto
i chunk arrivano lo stesso, ed e' tutto cio' che serve.

I QUATTRO CASI, e perche' ciascuno:
  · testo semplice          — il caso base;
  · accenti italiani        — «citta'», «perche'», «206,6»: un prodotto che
                              normalizza gli accenti sposterebbe gli offset;
  · testo lungo             — produce chunk SOVRAPPOSTI, e la citazione deve
                              restare esatta anche dove due passaggi condividono
                              testo;
  · ideogrammi cinesi       — IL CASO DECISIVO: se gli offset fossero in BYTE
                              invece che in caratteri Unicode, qui fallirebbero
                              (ogni ideogramma pesa 3 byte in UTF-8). E' il caso
                              che una suite scritta in inglese non prova mai.
"""
from __future__ import annotations

import math
import re

import pytest

import verimem.document_index as di

TESTI = {
    "semplice.txt": "Il prezzo del modello A e' 100 euro.\n",
    "accenti.txt": "La citta' di Verona ha una superficie di 206,6 km quadrati. "
                   "Perche' e' cosi' grande? Perche' include le frazioni.\n" * 3,
    "lungo.txt": "Riga di testo con contenuto vario numero 7. " * 60
                 + "La sede di Bolzano contiene 777 pallet.\n",
    "cinese.txt": "罗维戈仓库有 480 个托盘。维罗纳的仓库更大。\n",
}


class _FakeEmbedder:
    DIM = 32

    def encode(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.DIM
            for tok in re.findall(r"[a-z0-9]+", (t or "").lower()):
                v[hash(tok) % self.DIM] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


@pytest.fixture
def indice(tmp_path):
    return di.DocumentIndex(db_path=tmp_path / "docidx.db", embedder=_FakeEmbedder())


@pytest.mark.parametrize("nome", sorted(TESTI))
def test_gli_offset_ritagliano_esattamente_il_passaggio(nome, tmp_path, indice):
    testo = TESTI[nome]
    f = tmp_path / nome
    f.write_text(testo, encoding="utf-8")
    indice.index_file(f)

    hits = [h for h in indice.search("prezzo pallet superficie 托盘", k=20)
            if str(h.get("source_id", "")).endswith(nome)]
    assert hits, f"nessun chunk per {nome}: il banco non sta misurando niente"

    for h in hits:
        start, end, passaggio = h["start"], h["end"], h["text"]
        assert testo[start:end] == passaggio, (
            f"{nome}: gli offset {start}-{end} non ritagliano il passaggio.\n"
            f"  atteso  : {passaggio[:80]!r}\n"
            f"  ottenuto: {testo[start:end][:80]!r}")


def test_il_caso_cinese_esclude_gli_offset_in_byte(tmp_path, indice):
    """LA GUARDIA CHE NOMINA LA CAUSA, non il sintomo.

    Il test sopra fallirebbe se gli offset passassero ai byte, ma direbbe solo
    «non ritagliano». Questo dice PERCHE': la lunghezza in caratteri e quella in
    byte differiscono, e il prodotto deve usare la prima."""
    testo = TESTI["cinese.txt"]
    assert len(testo) != len(testo.encode("utf-8")), (
        "il testo di prova non distingue piu' caratteri da byte: la guardia e' "
        "diventata cieca, sostituiscilo con uno che contenga non-ASCII")

    f = tmp_path / "cinese.txt"
    f.write_text(testo, encoding="utf-8")
    indice.index_file(f)

    for h in indice.search("托盘", k=5):
        if str(h.get("source_id", "")).endswith("cinese.txt"):
            assert testo[h["start"]:h["end"]] == h["text"]
            assert h["end"] <= len(testo), (
                f"offset {h['end']} oltre la lunghezza in CARATTERI ({len(testo)}): "
                f"sembra un offset in byte ({len(testo.encode('utf-8'))})")
