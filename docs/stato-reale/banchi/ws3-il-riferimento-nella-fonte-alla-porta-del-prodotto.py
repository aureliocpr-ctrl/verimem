"""Il numero di un riferimento, nella FONTE: che cosa succede ALLA PORTA.

PERCHE'. Due mie cure si contraddicono alla lettera, e i loro presidi lo dicono
con la stessa forma sintattica e l'esito opposto::

    29ab5544 (28/08)   «Articolo 5 del regolamento» come FONTE  ->  5 NON deve esserci
    fb2ff485 (30/08)   «l'art.15 del codice»        come FONTE  -> 15 DEVE esserci

Nessuna riga puo' soddisfare entrambe. La domanda percio' non e' «quale riga»
ma **quale delle due situazioni si presenta DAVVERO alla porta del prodotto** —
ed e' la lezione di casa che avevo gia' pagato: *il livello a cui misuri decide
il verdetto: regex < funzione pubblica < porta del prodotto*. Il 30/08 ho
misurato alla FUNZIONE (5/8 contro 8/8) e ho curato. Questo banco misura dove
il prodotto chiama: `valori_non_nella_fonte(claim, source)`, il produttore
dell'avviso `L4.1`.

LA DISSIMMETRIA CHE IL BANCO SFRUTTA, e che va detta prima: la potatura dei
riferimenti sul lato CLAIM **non e' in discussione** — nessuna delle due cure la
tocca. Quindi un claim che CITA «all'art. 15» non porta 15 nel confronto, e non
puo' chiedere alla fonte di contenerlo. Se cosi' e', il caso che `fb2ff485`
diceva di curare **non e' raggiungibile da questa porta**, e l'esenzione paga
solo il costo.

LA PREDIZIONE, scritta prima di eseguire:
  A  claim che CITA il riferimento          -> nessun avviso, con e senza esenzione
  B  claim che INVENTA la grandezza         -> avviso SOLO senza esenzione
Se A vale, l'esenzione non compra niente su questa porta; se B vale, costa un
falso negativo — cioe' un fatto inventato ammesso.

CONDIZIONE DI FALSIFICAZIONE: se in A l'avviso compare quando l'esenzione e'
revocata, allora l'esenzione serviva davvero e la mia cura del 30/08 va tenuta
(e il conflitto va risolto altrove).

🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: una coppia in cui `L4.1` **deve** parlare
in entrambi i regimi (claim che inventa un numero che la fonte non contiene in
nessuna forma). Se tacesse anche li', il banco misurerebbe un layer spento e i
«nessun avviso» delle altre righe non direbbero niente.

REGIME: chiamata diretta alla funzione del prodotto, nessuno store, nessun
giudice, italiano e inglese. Il confronto fra i due regimi si fa in DUE
esecuzioni (la riga del bivio cambia nel sorgente), e per questo ogni riga
stampa anche lo stato della riga letto dal modulo: un A/B in due esecuzioni
senza quella stampa non e' verificabile.

    python docs/stato-reale/banchi/ws3-il-riferimento-nella-fonte-alla-porta-del-prodotto.py
"""

from __future__ import annotations

import inspect

from verimem.quantity_match import extract_quantities
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

#: (chiave, etichetta, claim, fonte, avviso atteso quando l'esenzione e' REVOCATA)
#: ⚠️ LA CHIAVE E' ESPLICITA, e non e' pedanteria: la prima stesura la
#: ricavava con `etichetta[:4].strip()` e per «B  il claim…» dava «B  i»,
#: cosi' il riepilogo stampava 0 mentre la tabella sopra stampava 1 e 1.
#: Il difetto era nel MISURATORE, e l'ha preso il confronto fra le due righe
#: della stessa corsa.
CASI: list[tuple[str, str, str, str, str]] = [
    ("A", "il claim CITA il riferimento",
     "L'art. 15 del codice prevede la penale.",
     "Il codice civile, l'art.15, disciplina la penale.",
     "nessuno"),
    ("A2", "il claim cita, la fonte abbrevia",
     "Vedi pagina 7 del manuale.",
     "Il manuale, vedi pag.7, riporta la procedura.",
     "nessuno"),
    ("B", "il claim INVENTA la grandezza",
     "Il contratto prevede 5 rate mensili.",
     "Articolo 5 del regolamento: le modalita' sono definite altrove.",
     "L4.1 deve parlare"),
    ("B2", "idem, in inglese",
     "The contract provides for 5 instalments.",
     "Section 5 of the agreement: terms are defined elsewhere.",
     "L4.1 deve parlare"),
    ("CTRL", "il numero non c'e' in nessuna forma",
     "Il contratto prevede 91 rate mensili.",
     "Articolo 5 del regolamento: le modalita' sono definite altrove.",
     "L4.1 deve parlare SEMPRE"),
]


def _stato_della_riga() -> str:
    """La riga del bivio, letta dal sorgente vivo: e' il REGIME di questa corsa."""
    src = inspect.getsource(extract_quantities)
    for riga in src.splitlines():
        if "_riferimenti =" in riga:
            return riga.strip()
    return "(riga non trovata)"


def main() -> int:
    riga = _stato_della_riga()
    esente = "come_fonte" in riga
    print(f"  REGIME (riga letta dal sorgente): {riga}")
    print(f"  esenzione sulla fonte: {'ATTIVA' if esente else 'REVOCATA'}\n")

    print(f"  {'caso':<40} {'valori claim':<18} {'valori fonte':<20} avvisi L4.1")
    print("  " + "-" * 104)
    esiti: dict[str, int] = {}
    for chiave, etichetta, claim, fonte, _atteso in CASI:
        vc = sorted(v for _u, v in extract_quantities(claim))
        vf = sorted(v for _u, v in extract_quantities(fonte, come_fonte=True))
        av = valori_non_nella_fonte(claim, fonte)
        esiti[chiave] = len(av)
        det = ", ".join(f"{getattr(a, 'valore', a)}" for a in av) or "-"
        nome = f"{chiave:<4} {etichetta}"
        print(f"  {nome:<40} {str(vc):<18} {str(vf):<20} {len(av)}  [{det}]")

    print("\n  ATTESO con l'esenzione REVOCATA:")
    for chiave, etichetta, _c, _f, atteso in CASI:
        print(f"     {chiave:<4} {etichetta:<36} {atteso}")

    print("\n  [1] CONTROLLO — il layer parla dove DEVE (numero assente in ogni forma): "
          f"{'SI' if esiti.get('CTRL', 0) > 0 else 'NO'}")
    if not esiti.get("CTRL", 0):
        print("      CONTROLLO CADUTO: `L4.1` tace anche sul caso che deve")
        print("      segnalare ⇒ misuro un layer spento e i «nessun avviso»")
        print("      delle altre righe non dicono niente. NESSUN VERDETTO.")
        return 1

    print("\n  ══ LETTURA DI QUESTA CORSA ══")
    cita = esiti.get("A", 0) + esiti.get("A2", 0)
    inventa = esiti.get("B", 0) + esiti.get("B2", 0)
    print(f"     claim che CITA un riferimento    -> avvisi: {cita}")
    print(f"     claim che INVENTA una grandezza  -> avvisi: {inventa}")
    if esente:
        print("     (esenzione ATTIVA: se `inventa` e' 0, la fonte sta")
        print("      SOSTENENDO un numero inventato — il difetto di 29ab5544)")
    else:
        print("     (esenzione REVOCATA: se `cita` e' 0 e `inventa` > 0, la")
        print("      revoca non costa nulla su questa porta e chiude il buco)")
    print("\n  ⚠️ Il verdetto fra i due regimi si legge confrontando DUE corse:")
    print("     questa stampa il regime nella prima riga apposta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
