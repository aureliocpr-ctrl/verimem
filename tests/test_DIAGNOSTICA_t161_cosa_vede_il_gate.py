"""DIAGNOSTICA T161 — non asserisce niente, STAMPA cosa vede il gate.

⚠️ QUESTO FILE NON ENTRA NELLA RICHIESTA. Serve a una cosa sola: leggere dal log
della CI i valori che in locale non posso ottenere (RAM sotto la soglia), invece
di continuare a dedurli dal codice. Tre ipotesi le ho già escluse leggendo — le
due firme si calcolano allo stesso modo, la `source` è in scope nel gate, i
fratelli arrivano da `SELECT *` — e la quarta la faccio dire al prodotto.

L'IPOTESI DA FALSIFICARE, suggerita dal lead: la firma del candidato si calcola
DENTRO il gate sulla `source` che il gate RICEVE, e quel testo può non essere
quello intero (span ridotto alla finestra del giudice, normalizzato, troncato);
la firma del fratello è stata calcolata alla scrittura sul testo intero. Due
testi diversi, due firme diverse, «conflitto», nessun ritiro. Spiegherebbe
perché cadono solo i casi CON fonte.

Se è così, la cura non è toccare il confronto: è calcolare la firma UNA volta,
alla scrittura, e passarla al gate già fatta invece di ricalcolarla.
"""
from __future__ import annotations

from verimem import Memory
from verimem.supersession_policy import canonical_source_of, source_signature_of

TOPIC = "diagnostica/t161"
FONTE = "Listino ufficiale, revisione unica, riga quattro."


def _mostra(nome, oggetto):
    firma = getattr(oggetto, "source_signature", None)
    print(f"  {nome:22} firma={firma!r}")
    print(f"  {'':22} chiave={canonical_source_of(oggetto)!r}")


def test_DIAGNOSTICA_stampa_cosa_vede_il_gate(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)
    mem = Memory(path=tmp_path / "sem" / "sem.db")

    with capsys.disabled():
        print("\n===== DIAGNOSTICA T161 =====")
        print(f"la fonte passata: len={len(FONTE)}  primi 40: {FONTE[:40]!r}")
        print(f"firma calcolata dal banco: {source_signature_of(FONTE)!r}")

        r1 = mem.add("L'abbonamento costa 100 euro al mese.", topic=TOPIC,
                     source=FONTE, validate="full")
        primo = mem.semantic.get(r1["id"])
        print("\nDOPO LA PRIMA SCRITTURA, il fatto nello store:")
        _mostra("fratello (dal DB)", primo)

        r2 = mem.add("L'abbonamento costa 150 euro al mese.", topic=TOPIC,
                     source=FONTE, validate="full")
        secondo = mem.semantic.get(r2["id"])
        print("\nDOPO LA SECONDA SCRITTURA, stessa fonte:")
        _mostra("nuovo (dal DB)", secondo)

        primo_riletto = mem.semantic.get(r1["id"])
        print(f"\nsuperseded_by del primo: {getattr(primo_riletto, 'superseded_by', None)!r}")
        print(f"atteso                 : {r2['id']!r}")
        print("le due chiavi COINCIDONO?",
              canonical_source_of(primo_riletto) == canonical_source_of(secondo))
        print("===== FINE DIAGNOSTICA =====\n")
