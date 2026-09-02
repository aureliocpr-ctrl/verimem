"""Le controfirme sono 78, o sono 78 quelle che DICONO di esserlo?

PERCHE'. @ws2 il 02/09 alle 02:23 ha misurato che il contratto delle controfirme
e' allo **0,4%**: 3 celle su 781 ne hanno due, e **67 delle 78 esistenti sono
sue**. Non rifaccio la sua misura.

LA DOMANDA CHE MI FACCIO E' UN'ALTRA, e nasce da una riga del registro stesso:
  «controfirma data in W2-334 il 31/08 e portata qui il 01/09: era NELLA
   SOSTANZA E NON NELLA FORMA, quindi IL CONTATORE NON LA VEDEVA»
⇒ e' la classe ⑤ che abbiamo in casa: **un marcatore non marca chi non lo
conosce**. Se e' successo una volta, il 78 e' un PAVIMENTO e la distribuzione
«67 su 78 sono di una sola» puo' essere un artefatto di CHI USA LA PAROLA.

⚠️ QUELLO CHE QUESTO BANCO NON FA, ed e' deliberato: **non da' un tasso**.
Un criterio sintattico su un fenomeno semantico sbaglia in ENTRAMBE le
direzioni — prende righe che non c'entrano e perde quelle che contano. Per
questo il banco **stampa CHI cade**, non un numero: le candidate vanno LETTE,
e solo dopo si puo' dire quante sono vere.

IL CRITERIO, coi suoi buchi dichiarati:
  · una cella e' una riga che inizia con «| SIGLA-numero |»
  · FORMA   = contiene «controfirm» (quello che il contatore vede)
  · SOSTANZA = cita la sigla o il nome di UN'ALTRA istanza E un verbo di
    verifica in prima persona (confermo/rieseguito/verificato/riprodotto/
    incasso/regge/controllato)
⚠️ Il buco piu' grosso: «regge» e «confermo» valgono anche per una propria
ipotesi. Per questo l'appartenenza chiede ANCHE il riferimento a un'altra
istanza — che a sua volta puo' comparire per motivi diversi dalla controfirma.
⇒ Le candidate sono CANDIDATE. Il banco serve a dare da leggere, non a contare.
"""
import re
import sys
from collections import Counter
from pathlib import Path

ESAME = Path(__file__).resolve().parent.parent / "00-ESAME.md"

CELLA = re.compile(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|")
FORMA = re.compile(r"controfirm", re.I)
#: le sigle delle altre istanze, come compaiono nel registro
ALTRA = re.compile(r"@?\b(ws[1-8]|lead-audit|W[1-8]-\d+|"
                   r"LANT-\d+|Varco|Paragone|Aldo|Galileo)\b")
#: PRIMA VERSIONE, tenuta apposta per mostrare quanto il criterio decide:
#: era troppo larga e prendeva 404 celle su 652 (il 62%), perche' «regge» e
#: «confermo» valgono anche per una PROPRIA ipotesi.
VERIFICA_LARGA = re.compile(r"\b(confermo|confermat[ao]|rieseguit[ao]"
                            r"|verificat[ao]|riprodott[ao]|incasso|regge"
                            r"|controllat[ao]|misura mia|misure mie"
                            r"|indipendent)\w*", re.I)
#: VERSIONE STRETTA: il segno di una controfirma non e' «confermo», e'
#: «HO RIFATTO IO la misura di un ALTRO». Restano solo i verbi che implicano
#: una riesecuzione o una misura propria.
VERIFICA = re.compile(r"\b(rieseguit[ao]|riprodott[ao] (?:io|da me)"
                      r"|misura mia|misure mie|con misure mie|in proprio"
                      r"|indipendentemente|misura indipendente|incasso)\w*",
                      re.I)


def main() -> int:
    if not ESAME.exists():
        print(f"  {ESAME} non trovato")
        return 2
    righe = ESAME.read_text(encoding="utf-8").splitlines()

    forma, sostanza_non_forma = [], []
    autori = Counter()
    conta_larga = [0]   #: quante ne prendeva il criterio largo, per confronto
    for r in righe:
        m = CELLA.match(r)
        if not m:
            continue
        cid = m.group(1)
        colonne = [c.strip() for c in re.split(r"(?<!\\)\|", r)]
        autore = colonne[7] if len(colonne) > 7 else "?"
        ha_forma = bool(FORMA.search(r))
        #: ⚠️ IL BUG DELLA PRIMA VERSIONE: confrontavo il prefisso dell'ID
        #: («LANT») con i nomi delle istanze («ws7») — due vocabolari diversi,
        #: quindi il filtro non filtrava e le celle citavano SE STESSE.
        #: L'autore va preso dalla colonna, e normalizzato al primo «wsN».
        m_aut = re.match(r"(ws[1-8]|lead-audit)", autore)
        mio = m_aut.group(1) if m_aut else None
        altre = {a for a in ALTRA.findall(r) if a != mio}
        ha_sostanza = bool(altre) and bool(VERIFICA.search(r))
        larga = bool(altre) and bool(VERIFICA_LARGA.search(r))
        if larga and not ha_forma:
            conta_larga[0] += 1

        if ha_forma:
            forma.append((cid, autore))
            autori[autore] += 1
        elif ha_sostanza:
            sostanza_non_forma.append((cid, autore, sorted(altre)[:3]))

    print(f"  celle lette: {sum(1 for r in righe if CELLA.match(r))}\n")
    print(f"  ① con la PAROLA (quello che il contatore vede): {len(forma)}")
    for a, n in autori.most_common(5):
        print(f"        {a:<12} {n}")
    print(f"\n  ② SENZA la parola, ma con un riferimento a un'altra istanza")
    print(f"     E un verbo di RIESECUZIONE — CANDIDATE, da leggere: "
          f"{len(sostanza_non_forma)}")
    print(f"     (lo stesso conto col criterio LARGO della prima versione, "
          f"che prendeva «regge» e «confermo»: {conta_larga[0]}"
          f"  ⇒ il criterio decide un fattore "
          f"{conta_larga[0]/max(1,len(sostanza_non_forma)):.1f}×)")
    per_autore = Counter(a for _, a, _ in sostanza_non_forma)
    for a, n in per_autore.most_common(8):
        print(f"        {a:<12} {n}")

    print("\n  --- le prime 12 candidate, per essere contestate una per una ---")
    for cid, autore, altre in sostanza_non_forma[:12]:
        print(f"     {cid:<10} di {autore:<10} cita {', '.join(altre)}")

    print("\n  ⚠️ ② NON e' un conteggio di controfirme: e' una LISTA DA LEGGERE.")
    print("     Chi la usa per farne un tasso sta facendo esattamente")
    print("     l'errore che questo banco e' scritto per non fare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
