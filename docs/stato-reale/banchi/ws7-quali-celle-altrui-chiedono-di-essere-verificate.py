"""Quali celle NON mie chiedono esplicitamente di essere verificate?

PERCHE'. Il 02/09 @ws2 ha misurato che il contratto delle controfirme e' allo
0,4% (3 celle su 781 ne hanno due) e ha contato **25 celle** che chiedono
esplicitamente di essere verificate. Nella stessa notte ha rifatto TRE mie celle
— tutte e tre lo chiedevano nel testo — e tutte e tre hanno retto, due uscendone
piu' forti. ⇒ **Il contratto non e' fermo perche' nessuno vuole controllare: e'
fermo perche' nessuno sa DOVE serve.**

Questo banco produce la lista per il verso opposto: le celle **altrui** che lo
chiedono, cosi' che il gesto si possa restituire.

⚠️ MARCA ANCHE IL COSTO. Con otto istanze sulla stessa macchina e il giudice a
758 MB per processo, una cella che richiede modelli o warmup non e' verificabile
al volo: la colonna «peso» separa cio' che si controlla LEGGENDO da cio' che
chiede un'esecuzione pesante.

⚠️ LIMITE DEL CRITERIO, dichiarato: la richiesta di verifica e' scritta in
linguaggio naturale e ogni elenco di forme e' incompleto — questa lista e' un
PAVIMENTO. E «pesante» e' indovinato dalle parole della cella, non dal costo
reale: serve a ordinare il lavoro, non a decidere.
"""
import re
import sys
from pathlib import Path

ESAME = Path(__file__).resolve().parent.parent / "00-ESAME.md"

CELLA = re.compile(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|")
#: le colonne si separano su una barra NON preceduta da backslash. Scritto in un
#: file e non passato dalla shell: il 02/09 il lookbehind mandato per riga di
#: comando e' arrivato con un backslash solo e non compilava — l'help di
#: aggiorna_cella.py dice che era gia' successo quattro volte.
COLONNE = re.compile(r"(?<!\\)\|")
CHIEDE = re.compile(r"va rifatt|chiede di essere|da (?:ri)?verificar"
                    r"|non (?:ancora )?verificat|rifar(?:la|lo) prima"
                    r"|va confermat|resta da (?:verificar|misurar)", re.I)
SIGLA = re.compile(r"^(ws[1-8]|lead-audit)\b")
PESANTE = re.compile(r"giudice|warmup|758|modell|torch|suite|pytest", re.I)


def main() -> int:
    if not ESAME.exists():
        print(f"  {ESAME} non trovato")
        return 2
    righe = ESAME.read_text(encoding="utf-8").splitlines()

    mie, altrui = [], []
    for r in righe:
        m = CELLA.match(r)
        if not m or not CHIEDE.search(r):
            continue
        col = [c.strip() for c in COLONNE.split(r)]
        # 🔴 02/09 04:45 — CI SONO RICASCATA, ED E' LA MIA STESSA CELLA.
        # La prima versione leggeva `col[7]` come autrice. Ma il numero di
        # colonne VARIA anche dentro la stessa famiglia (`aggiorna_cella.py`:
        # «LANT-34 ha 10 pipe e LANT-109 ne ha 9»), quindi su una cella con un
        # verdetto piu' lungo l'indice 7 cade in mezzo al TESTO: `LANT-70`
        # risultava scritta da «` e trovava».
        # ⇒ E' `LANT-143`, che ho scritto io: **un indice di colonna fisso in un
        #   file a colonne variabili**. L'ho vista solo perche' il banco stampa
        #   CHI cade e quel nome era assurdo; contando, sarebbe passata.
        # La cura non e' un indice migliore: e' cercare la colonna che HA LA
        # FORMA di una sigla, e dichiarare «?» quando non c'e'.
        autore = next((c for c in col if SIGLA.match(c)), "?")
        peso = "PESANTE " if PESANTE.search(r) else "leggera "
        #: col[0] e' il vuoto prima della prima barra e col[1] e' l'ID: la
        #: DOMANDA e' col[2]. La prima versione stampava l'ID due volte e la
        #: lista era inutilizzabile senza che nulla segnalasse l'errore.
        domanda = col[2] if len(col) > 2 else "?"
        voce = (m.group(1), autore[:12], peso, domanda[:74])
        (mie if autore.startswith("ws7") else altrui).append(voce)

    print(f"  celle che chiedono di essere verificate: "
          f"{len(mie) + len(altrui)}  (mie {len(mie)} · altrui {len(altrui)})\n")
    print("  --- ALTRUI, il lavoro che posso restituire ---")
    for cid, aut, peso, dom in altrui:
        print(f"    {cid:<10} {aut:<13} {peso} {dom}")
    if not altrui:
        print("    nessuna: o il criterio e' troppo stretto, o le richieste")
        print("    esplicite sono un'abitudine solo mia — vale come dato.")
    print("\n  ⚠️ Lista PAVIMENTO: la richiesta e' in linguaggio naturale.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
