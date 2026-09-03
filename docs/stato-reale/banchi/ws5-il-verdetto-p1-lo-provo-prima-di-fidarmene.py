r"""Il misuratore prima della misura: `verdetto_p1` dice il vero su casi che conosco?

⚠️ **Perche' questo banco esiste.** Il 02/09 ho consegnato «pool a 2 worker, -47%» da UNA
esecuzione. Ora il banco del pool sa fare tre ripetizioni con l'ordine alternato e
stampare P1.a/P1.b/P1.d — ma **un giudice nuovo che non e' stato giudicato e' esattamente
il difetto che questo prodotto esiste per non fare**. Se `verdetto_p1` sbagliasse, non me
ne accorgerei: stamperebbe un verdetto plausibile su numeri veri, ed e' la forma peggiore
di errore che conosca.

⇒ Qui i dati sono FINTI e le risposte sono NOTE. Il banco vero gira dopo, e solo se
questo e' verde.

I quattro casi, scelti perche' ognuno puo' rompere il verdetto in un modo diverso::

    A  «2» vince in tutte e tre le ripetizioni, a ordini diversi   -> P1.a REGGE
    B  vince un braccio diverso ogni volta                          -> P1.a CADE
    C  «2» vince sempre MA il range copre la differenza             -> P1.a regge, P1.d CADE
    D  il rapporto p95(1)/p95(2) e' 1,02                            -> P1.b CADE

⚠️ Il caso C e' il piu' importante ed e' quello che un misuratore ingenuo sbaglia: «2»
vince ogni volta, il verdetto sembra solido, e invece la dispersione entro il braccio e'
piu' larga della differenza fra i bracci. Un banco che stampasse solo «vince 2» sarebbe
d'accordo con se stesso e in disaccordo coi dati.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-il-verdetto-p1-lo-provo-prima-di-fidarmene.py
"""
import importlib.util
import io
import contextlib
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
BANCO = os.path.join(QUI, "ws5-il-pool-del-giudice-porta-il-p95-sotto-il-secondo.py")


def carica_banco():
    """Importa il banco SENZA eseguirlo (per questo main() e' sotto __main__)."""
    spec = importlib.util.spec_from_file_location("banco_pool", BANCO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def esito(worker, ripetizione, posizione, p95):
    """Un esito finto con la forma di quelli veri.

    `pct(lat, .95)` sull'elenco deve dare esattamente `p95`: se la lista e' tutta uguale
    a p95, qualunque percentile e' p95. Cosi' il caso di prova non dipende da come il
    banco calcola i percentili — che e' codice suo, non oggetto di questa verifica.
    """
    return {"worker": worker, "ripetizione": ripetizione, "posizione": posizione,
            "lat": [p95] * 20, "durata": 10.0, "rss": 1900.0, "ok": 80}


CASI = {
    # A — «2» vince ovunque, a ordini diversi, con range stretto
    "A": ([esito(1, 1, 1, 2.60), esito(2, 1, 2, 1.40), esito(4, 1, 3, 1.80),
           esito(4, 2, 1, 1.82), esito(2, 2, 2, 1.42), esito(1, 2, 3, 2.64),
           esito(2, 3, 1, 1.41), esito(4, 3, 2, 1.79), esito(1, 3, 3, 2.62)],
          {"P1.a": "REGGE", "P1.d": "REGGE"}),
    # B — vincitore diverso a ogni ripetizione
    "B": ([esito(1, 1, 1, 1.20), esito(2, 1, 2, 1.90), esito(4, 1, 3, 2.10),
           esito(4, 2, 1, 1.10), esito(2, 2, 2, 2.00), esito(1, 2, 3, 2.20),
           esito(2, 3, 1, 1.15), esito(4, 3, 2, 2.05), esito(1, 3, 3, 2.15)],
          {"P1.a": "CADE"}),
    # C — «2» vince sempre ma la dispersione entro braccio copre la differenza
    #
    # ⚠️ IL PRIMO CASO C CHE HO SCRITTO NON FALSIFICAVA NIENTE, e credevo di si'.
    # Avevo messo: worker1 = 3,60/3,00/4,90 (mediana 3,60, range 1,90)
    #              worker2 = 1,40/2,90/1,45 (mediana 1,45, range 1,50)
    # differenza fra le mediane 2,15, range piu' largo 1,90 -> 1,90 < 2,15, e P1.d
    # REGGEVA a ragione. Ho accusato il misuratore per un errore mio, e me ne sono
    # accorto solo rifacendo l'aritmetica a mano.
    # ⇒ Costruire un caso che faccia cadere P1.d e' piu' difficile di quanto pensassi:
    #   serve che la dispersione ENTRO un braccio superi la distanza FRA i bracci, e
    #   con bracci ben separati non basta «sparpagliare un po'». Questo dice qualcosa
    #   sul criterio: P1.d non e' una soglia severa, e' una soglia MITE. Se cade, il
    #   guadagno e' davvero indistinguibile.
    # Qui: worker1 = 3,00/3,10/5,00 (mediana 3,10, range 2,00)
    #      worker2 = 1,40/2,90/1,45 (mediana 1,45, range 1,50)
    #      differenza 1,65 < range 2,00 -> CADE, e «2» vince comunque ogni ripetizione.
    "C": ([esito(1, 1, 1, 3.00), esito(2, 1, 2, 1.40), esito(4, 1, 3, 3.20),
           esito(4, 2, 1, 3.30), esito(2, 2, 2, 2.90), esito(1, 2, 3, 3.10),
           esito(2, 3, 1, 1.45), esito(4, 3, 2, 3.25), esito(1, 3, 3, 5.00)],
          {"P1.a": "REGGE", "P1.d": "CADE"}),
    # D — il guadagno di «2» e' del 2%: rumore
    "D": ([esito(1, 1, 1, 1.42), esito(2, 1, 2, 1.39), esito(4, 1, 3, 1.80),
           esito(4, 2, 1, 1.82), esito(2, 2, 2, 1.40), esito(1, 2, 3, 1.43),
           esito(2, 3, 1, 1.41), esito(4, 3, 2, 1.79), esito(1, 3, 3, 1.44)],
          {"P1.b": "CADE"}),
}


def leggi(testo, criterio):
    """REGGE / CADE / assente per un criterio, dal testo che il verdetto stampa."""
    riga = [ln for ln in testo.splitlines() if criterio in ln and ("REGGE" in ln or "CADE" in ln)]
    if not riga:
        return "assente"
    return "REGGE" if "REGGE" in riga[0] else "CADE"


def main():
    mod = carica_banco()
    print("  banco caricato senza eseguirlo: %s\n" % os.path.basename(BANCO))
    sbagliati = 0
    for nome, (esiti, attese) in CASI.items():
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mod.verdetto_p1(esiti, 3)
        testo = buf.getvalue()
        print("  --- caso %s ---" % nome)
        for criterio, atteso in attese.items():
            letto = leggi(testo, criterio)
            ok = (letto == atteso)
            sbagliati += 0 if ok else 1
            print("     %s %-6s atteso %-6s letto %-7s"
                  % ("✅" if ok else "🔴", criterio, atteso, letto))
        # il controllo positivo: il verdetto deve aver stampato QUALCOSA di leggibile
        if "P1 — IL VERDETTO" not in testo:
            print("     🔴 il verdetto non ha nemmeno stampato la sua intestazione")
            sbagliati += 1

    print("\n" + "=" * 70)
    if sbagliati:
        print("  🔴 IL MISURATORE SBAGLIA su %d criteri: NON usarlo per misurare."
              % sbagliati)
        print("     Un verdetto plausibile su numeri veri e' l'errore peggiore che ci sia.")
    else:
        print("  ✅ il misuratore dice il vero su tutti e quattro i casi noti.")
        print("     ⚠️ Questo NON dice che il pool funzioni: dice che il righello legge.")
    print("=" * 70)
    return 1 if sbagliati else 0


if __name__ == "__main__":
    sys.exit(main())
