"""I casi che devono restare COME SONO quando entra la cura di T175.

T175 insegna al prodotto che «il capannone 7» è un identificatore e non una
quantità. È giusto, e tocca la superficie più affollata del modulo: quella che
decide se un numero afferma una grandezza. Su quella stessa superficie sono
appena atterrate due cure, e questa cella tiene il loro risultato fermo.

  · **#111** — un'unità può finire con una cifra, ma solo otto forme:
    `400 m3` è un volume, e `m3` nudo resta un'unità.
  · **#120** — un numero dentro il nome di un file è un titolo:
    `00-ESAME.md` non afferma `00`.

⚠️ QUESTA CELLA È VERDE OGGI, ed è il suo scopo: non misura un difetto, fissa
   una CONVIVENZA che nessuno ha scritto e che quindi nessuno difende. `m3.txt`
   sta esattamente nell'incrocio — è un nome di file (#120) il cui prefisso è
   un'unità di volume (#111) — e nessun banco lo nomina. Misurato sul tronco
   `42a09da9` prima di scrivere questo file::

       m3.txt  ->  nome di file: True
       m3      ->  nome di file: False
       «Il file m3.txt contiene 400 righe.»  ->  [('righe', 400.0)]
       «Il capannone misura 400 m3.»         ->  [('m3', 400.0)]

   Le due cure non si pestano i piedi. Se una terza le farà litigare, qui
   diventa rosso invece di diventare un'accusa sbagliata in produzione.

⚠️ NIENTE GIUDICE: tutto quello che c'è qui è deterministico, quindi la cella
   non dipende dallo stato del daemon né dallo stub del conftest.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities, norm_unit
from verimem.valore_non_nella_fonte import ESTENSIONI_DI_FILE, _e_un_nome_di_file

# ───────────────────────  l'incrocio fra #111 e #120  ────────────────────────

@pytest.mark.parametrize("nome", ["m1.txt", "m2.txt", "m3.txt"])
def test_un_file_chiamato_come_un_unita_resta_un_file(nome):
    """`m3.txt` è un nome di file, anche se `m3` è un'unità di volume.

    È il caso che sta nell'incrocio delle due cure ed è l'unico per cui questo
    file esiste: `m3` è fra le otto forme che #111 riconosce come unità, e
    `m3.txt` è fra i nomi che #120 esclude. La precedenza giusta è quella del
    nome, perché un file si chiama come vuole.
    """
    assert _e_un_nome_di_file(nome) is True


def test_l_unita_nuda_non_diventa_un_nome_di_file():
    """Il rovescio, e serve quanto l'altro: senza questa riga la cella sopra
    passerebbe anche se la cura di #120 avesse cominciato a mangiarsi tutto."""
    assert _e_un_nome_di_file("m3") is False
    assert _e_un_nome_di_file("400") is False
    assert _e_un_nome_di_file("v2.4.0") is False


def test_un_file_nella_frase_non_porta_la_sua_unita_nella_quantita():
    """Alla superficie che conta: il nome del file non deve produrre una
    grandezza, e la quantità vera della frase deve restare."""
    assert sorted(extract_quantities("Il file m3.txt contiene 400 righe.")) == [
        ("righe", 400.0)]
    assert sorted(extract_quantities("Il file m1.txt contiene 400 righe.")) == [
        ("righe", 400.0)]


def test_la_stessa_grafia_SENZA_il_file_resta_un_volume():
    """⚠️ IL CONTROLLO POSITIVO di questa cella. Senza, «nessuna quantità
    estratta» si otterrebbe anche da un estrattore che ha smesso di funzionare,
    e i tre test qui sopra sarebbero verdi per il motivo sbagliato."""
    quantita = extract_quantities("Il capannone misura 400 m3.")
    assert ("m3", 400.0) in quantita, quantita


def test_norm_unit_non_normalizza_un_nome_di_file_a_una_unita():
    """`m3.txt` non deve collassare su `m3`: se lo facesse, due fatti su file
    diversi si leggerebbero come due misure della stessa grandezza."""
    assert norm_unit("m3") == "m3"
    assert norm_unit("m3.txt") == "m3.txt"
    assert norm_unit("m1.txt") != norm_unit("m3.txt")


# ──────────────────────────  la lista, letta e non copiata  ──────────────────

def test_la_lista_delle_estensioni_si_legge_da_dove_vive():
    """#120 dichiara che la lista sta «in un posto solo» perché una lista
    scritta due volte diverge. Questa cella la LEGGE — e prova che ogni voce
    funziona davvero, invece di fidarsi del fatto che sia scritta."""
    assert ESTENSIONI_DI_FILE, "la lista è vuota: non c'è niente da difendere"
    for est in ESTENSIONI_DI_FILE:
        assert _e_un_nome_di_file(f"07-nota.{est}") is True, est
        assert _e_un_nome_di_file(f"nota.{est}") is False, (
            f"«nota.{est}» non ha cifre: non c'è niente da escludere")
