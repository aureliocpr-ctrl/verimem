"""Il difetto di @ws2 Giano è un caso isolato o una CLASSE? — quanti parametri
della firma pubblica vengono ingoiati quando `as_of` è attivo.

    python ws7-quanti-parametri-ingoia-as-of.py

━━ DA DOVE VIENE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@ws2 Giano (`9413be3cd9a45507`) ha MISURATO che `include_superseded` funziona da
solo e **viene ignorato in silenzio** quando si combina con `as_of`, perché il
ramo `as_of` di `client.py` chiama `recall_as_of(...)` che non lo accetta.

**La domanda che resta aperta, ed è di prodotto: quanti ALTRI?** Il difetto non
sta in un parametro, sta **nella combinazione di due** — e le combinazioni non le
ha mai esercitate nessuno: abbiamo sempre misurato i parametri uno per uno.

━━ IL PRIMO NUMERO, letto con `inspect` (esecuzione, non lettura del codice) ━━
    Memory.search()   accetta 8 parametri oltre a `query`
    recall_as_of()    ne accetta 2 (piu' query/when/sm)
    ⇒ 5 non hanno DOVE ANDARE: deep · history_hops · include_superseded ·
                               min_relevance · with_history

⚠️ **`5` è un LIMITE SUPERIORE, non il numero dei difetti.** Un parametro può
essere applicato **dopo** il ramo, in `client.py`, e funzionare lo stesso:
`deep` lo dichiara innocuo Giano (`recall_as_of` lo forza a True), e
`with_history`/`history_hops` potrebbero arricchire il risultato a valle. **Solo
il comportamento decide.**

━━ IL CRITERIO, SCRITTO PRIMA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Per ogni parametro si misura la STESSA cosa due volte:

    (1) SENZA as_of, il parametro cambia il risultato?   <- il controllo positivo
    (2) CON  as_of, lo cambia ancora?

    (1) sì e (2) no  ->  🔴 INGOIATO: accettato dalla firma, senza effetto
    (1) sì e (2) sì  ->  ✅ passa
    (1) no           ->  ⚠️ NON MISURATO: se non morde nemmeno da solo, il caso
                          non prova niente — e va detto, non nascosto

🔑 Il controllo positivo è obbligatorio: senza, «non cambia niente» significa sia
«il prodotto lo ingoia» sia «il mio caso era sbagliato», e sono due cose diverse.

📏 Nessun giudice (si scrive senza fonte): nessuno slot occupato.
⚡ Store TEMPORANEO, mai quello di Aurelio.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> None:
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip() or "?"
    ora = subprocess.run(["date", "+%H:%M:%S"],
                         capture_output=True, text=True).stdout.strip() or "?"
    store = Path(tempfile.mkdtemp(prefix="iris-comb-"))
    os.environ["HIPPO_DATA_DIR"] = str(store)
    os.environ["ENGRAM_DATA_DIR"] = str(store)
    print(f"  REGIME: albero {sha} · ora {ora} · store TEMPORANEO · nessun giudice")

    from verimem import Memory                      # dopo le variabili: il path si risolve all'import
    m = Memory()

    m.add("Il fornitore di pagamenti del servizio checkout e' Stripe.", topic="comb")
    m.add("La riunione di infrastruttura si tiene ogni martedi mattina.", topic="comb")
    m.add("Il gatto del vicino si chiama Ottavio e dorme sul davanzale.", topic="comb")

    # ⚠️ `as_of` vuole EPOCH SECONDS, e la docstring lo dice: «as_of (epoch seconds)».
    # Al primo giro gli ho passato un `datetime` -> TypeError, e il banco ha stampato
    # «INGOIATO» su un errore MIO. Non era un difetto del prodotto: era un mio uso
    # sbagliato di un parametro documentato.
    quando = (datetime.now(timezone.utc) + timedelta(days=1)).timestamp()
    q = "fornitore di pagamenti"

    def quanti(**kw) -> int:
        """Il numero di risultati, oppure SystemExit: un'eccezione NON e' uno zero."""
        try:
            return len(m.search(q, k=10, **kw))
        except Exception as e:                      # noqa: BLE001 — qualsiasi cosa
            raise SystemExit(
                f"  ⛔ la chiamata {kw} ha sollevato {type(e).__name__}: {e}\n"
                "     NON MISURATO. Un'eccezione mia non e' un risultato del prodotto,"
                " e contarla come 0 fabbrica un rosso.\n"
                "     🔑 PRESIDIO DI CLASSE: dieci minuti fa ho aggiunto questo stesso"
                " controllo a un ALTRO banco,\n"
                "        e non l'ho messo qui. Curare l'istanza invece della classe:"
                " terzo rosso non valido della notte."
            ) from e

    print()
    print("  === il controllo positivo, e poi la stessa cosa con as_of ===")
    esiti = {}
    for nome, basso, alto in [
        ("min_relevance", {"min_relevance": None}, {"min_relevance": 0.99}),
        ("include_superseded", {"include_superseded": False}, {"include_superseded": True}),
        ("k", {"k": 10}, {"k": 1}),
    ]:
        if nome == "k":       # k si passa a parte: quanti() lo forza
            senza_a = len(m.search(q, k=10))
            senza_b = len(m.search(q, k=1))
            con_a = len(m.search(q, k=10, as_of=quando))
            con_b = len(m.search(q, k=1, as_of=quando))
        else:
            senza_a, senza_b = quanti(**basso), quanti(**alto)
            con_a = quanti(as_of=quando, **basso)
            con_b = quanti(as_of=quando, **alto)

        morde_senza = senza_a != senza_b
        morde_con = con_a != con_b
        print(f"    {nome}:")
        print(f"      SENZA as_of : {senza_a} -> {senza_b}   morde: {morde_senza}")
        print(f"      CON   as_of : {con_a} -> {con_b}   morde: {morde_con}")
        if not morde_senza:
            esiti[nome] = "NON MISURATO (non morde nemmeno da solo: il caso non prova niente)"
        elif morde_con:
            esiti[nome] = "passa"
        else:
            esiti[nome] = "INGOIATO"
        print(f"      ➜ {esiti[nome]}")
        print()

    print("  === ESITO ===")
    ingoiati = [k for k, v in esiti.items() if v == "INGOIATO"]
    nonmis = [k for k, v in esiti.items() if v.startswith("NON MISURATO")]
    print(f"    ingoiati: {len(ingoiati)} {ingoiati}")
    print(f"    non misurati (il mio caso non li faceva mordere): {len(nonmis)} {nonmis}")
    if len(ingoiati) >= 2:
        print("    🔴 NON E' UN CASO ISOLATO: e' una CLASSE — il ramo as_of ingoia")
        print("       piu' di un parametro della firma pubblica.")
    elif len(ingoiati) == 1:
        print("    ⚠️ UNO SOLO fra quelli che ho saputo far mordere: il reperto di")
        print("       Giano regge, ma non ho mostrato che sia una classe.")
    else:
        print("    ⚠️ NESSUNO fra quelli misurati — leggere l'uscita, non dedurla")

    shutil.rmtree(store, ignore_errors=True)


if __name__ == "__main__":
    main()
