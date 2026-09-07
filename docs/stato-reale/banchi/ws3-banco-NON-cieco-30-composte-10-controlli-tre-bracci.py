"""IL BANCO DELLE SCRITTURE COMPOSTE SU TESTO NUOVO — NON CIECO, e lo dico prima.

Marie (QA) aveva proposto di scrivere lei 30 scritture composte «<vero> e <coda
falsa>» con verbi fuori dalla lista di atomic_claims e 10 coordinazioni di nomi
o aggettivi come controllo, senza vedere la lista, cosi' che chi ha scritto la
regola non vedesse le frasi (06/09 13:47, predizioni depositate in
5badf97872531c16). Il 07/09 Marie e' sulla misura del P0 (ordine del lead,
5aa2cb071dbbdae2): le frasi le ho scritte IO, che conosco la lista e la regola.
Quindi NON e' cieco. Cosa ho fatto per non ritagliarlo sulla cura, dichiarato:
  · dominio lontano dal corpus (portinerie, scuole, negozi, paesi), nessuna
    cifra, nessuna self-claim;
  · i verbi delle code sono fuori dalla lista, fuori dai nove del 06/09 e fuori
    dai tredici delle 30 code di ieri (lascia, sposta, blocca, cancella, rinvia,
    raddoppia, dimezza, libera, allunga, riduce, riapre, conoscono, cambia): la
    regola non e' stata disegnata su nessuno di questi;
  · CINQUE code sono scritte apposta nella forma che la regola stretta DICHIARA
    di non prendere (verbo in -a/-e seguito da preposizione o aggettivo, verbo
    in -ale): «riesce a», «sembra pieno», «continua a», «basta a», «sale sul»;
  · UN controllo e' scritto apposta nella forma che la regola stretta puo'
    sbagliare (aggettivo in -a seguito da un determinante): «pulita e libera
    ogni mattina»;
  · le teste usano verbi DELLA lista, cosi' i tre bracci differiscono solo sulla
    coda (una variabile);
  · le frasi sono scritte e committate PRIMA di eseguire qualunque braccio.
Per costruzione i bracci A (lista chiusa) e B (lista + nove) non possono
spezzare quasi niente: sono il pavimento, non un confronto. Il confronto vero e'
C contro i controlli (quanti errori) e C contro il giudice (la coda spezzata si
ferma?).

PREDIZIONI (le stesse del 06/09 13:47, riscritte prima di eseguire, 07/09 12:28):
  P-B1  braccio A (main da0f3106, lista chiusa): spezzate <= 50% delle 30
        (attese ~0: nessuna coda ha un verbo della lista);
  P-B2  braccio B (7b4b2542, +nove): spezzate <= 60% (attese ~0);
  P-B3  braccio C (468e9ca6, morfologia + regola -ed): spezzate >= 80% delle 30
        (attese 25/30: le cinque code «dichiarate» restano fuse) e <= 1 dei 10
        controlli spezzato per errore (atteso: «libera ogni mattina»);
  P-B4  col giudice, sulle composte che C spezza: la coda falsa cade sotto la
        soglia del giudice in >= 80%, e la testa vera (con la sua fonte) resta
        sopra in >= 90%;
  P-B5  l'INTERO non spezzato, con la stessa fonte, passa sopra la soglia in
        >= 50% delle 30: e' il muro 1, la coda falsa che entra sulle spalle
        della testa vera. Se P-B5 cade (< 50%), il muro e' piu' basso di quanto
        misurato sul corpus e la decomposizione vale meno.
Argomenti: decomp <wt_A> <wt_B> <wt_C> · giudice <wt_giudice> <wt_C>
(il giudice si importa da un albero solo; atomic_claims si carica per file,
e' autonomo: importa solo re).
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import time

QUI = pathlib.Path(__file__).resolve().parent

# (testa vera, fonte breve che prova SOLO la testa, coda falsa con verbo fuori lista)
COMPOSTE = [
    ("Il custode apre il cancello alle sette.",
     "Registro di portineria: il custode apre il cancello alle sette e lo chiude alle venti.",
     "e aiuta i fornitori a scaricare"),
    ("La segretaria stampa i moduli ogni lunedì.",
     "Nota interna: la segretaria stampa i moduli ogni lunedì mattina.",
     "e spiega la procedura ai nuovi"),
    ("Il tecnico ferma la caldaia in autunno.",
     "Piano di manutenzione: il tecnico ferma la caldaia in autunno per la pulizia.",
     "e ripara il bruciatore da solo"),
    ("Il corriere porta i pacchi entro mezzogiorno.",
     "Accordo con il corriere: porta i pacchi entro mezzogiorno.",
     "e consegna la posta ai piani"),
    ("La biblioteca resta aperta il sabato.",
     "Orari: la biblioteca resta aperta il sabato mattina.",
     "e affitta la sala ai privati"),
    ("Il cuoco usa il forno a legna la domenica.",
     "Menu della domenica: il cuoco usa il forno a legna.",
     "e compra il pane dal fornaio"),
    ("Il maestro legge una favola ogni pomeriggio.",
     "Diario di classe: il maestro legge una favola ogni pomeriggio.",
     "e insegna le tabelline dopo la merenda"),
    ("Il giardiniere passa il venerdì nel parco.",
     "Turni: il giardiniere passa il venerdì nel parco grande.",
     "e toglie le foglie dai vialetti"),
    ("La farmacia chiude alle otto.",
     "Cartello: la farmacia chiude alle otto di sera.",
     "e vende i cerotti a metà prezzo"),
    ("Il treno delle sei parte dal primo binario.",
     "Tabellone: il treno delle sei parte dal primo binario.",
     "e supera la corriera in velocità"),
    ("La mensa serve il pranzo a mezzogiorno.",
     "Avviso: la mensa serve il pranzo a mezzogiorno in punto.",
     "e paga i fornitori ogni mese"),
    ("Il portiere tiene le chiavi nel cassetto.",
     "Regolamento: il portiere tiene le chiavi nel cassetto chiuso.",
     "e ricorda le scadenze ai condomini"),
    ("L'ufficio postale apre alle nove.",
     "Orario: l'ufficio postale apre alle nove.",
     "e manda gli avvisi per posta"),
    ("La palestra chiude ad agosto.",
     "Comunicazione ai soci: la palestra chiude ad agosto.",
     "e riesce a trattenere gli iscritti"),          # DICHIARATA: verbo + preposizione
    ("Il dottore riceve il martedì.",
     "Studio medico: il dottore riceve il martedì pomeriggio.",
     "e visita i pazienti anche a casa"),
    ("Il negozio all'angolo vale come punto di ritiro.",
     "Il negozio all'angolo vale come punto di ritiro dei pacchi.",
     "e accende le luci alle sei"),
    ("Il bar della piazza mette i tavoli fuori in estate.",
     "Il bar della piazza mette i tavoli fuori in estate.",
     "e sembra pieno ogni sera"),                    # DICHIARATA: verbo + aggettivo
    ("La scuola comincia a settembre.",
     "Calendario: la scuola comincia a metà settembre.",
     "e invita i genitori alla festa"),
    ("Il museo apre gratis la prima domenica.",
     "Il museo apre gratis la prima domenica del mese.",
     "e guida i visitatori in tre lingue"),
    ("Il vicino parte per il mare a luglio.",
     "Il vicino del terzo piano parte per il mare a luglio.",
     "e affida il gatto alla portinaia"),
    ("Il sindaco chiama il consiglio ogni mese.",
     "Il sindaco chiama il consiglio comunale ogni mese.",
     "e decide le spese da solo"),
    ("Il fornaio prende la farina dal mulino.",
     "Il fornaio prende la farina dal mulino di valle.",
     "e rompe la tradizione della domenica"),
    ("La corriera passa alle sette.",
     "Fermata: la corriera passa alle sette.",
     "e aspetta gli studenti al bivio"),
    ("Il pittore finisce la facciata a maggio.",
     "Contratto: il pittore finisce la facciata entro maggio.",
     "e sceglie il colore con la commissione"),
    ("Il notaio tiene lo studio in centro.",
     "Il notaio tiene lo studio in centro, sopra la banca.",
     "e capisce il dialetto dei clienti"),
    ("La squadra sta in ritiro a luglio.",
     "La squadra sta in ritiro a luglio in montagna.",
     "e vince il torneo estivo"),
    ("Il falegname porta i mobili a domicilio.",
     "Il falegname porta i mobili a domicilio senza costi.",
     "e continua a lavorare la domenica"),          # DICHIARATA: verbo + preposizione
    ("Il meccanico vede le auto su appuntamento.",
     "Officina: il meccanico vede le auto solo su appuntamento.",
     "e restituisce le chiavi la sera"),
    ("La pasticceria fa i dolci la mattina.",
     "La pasticceria fa i dolci ogni mattina presto.",
     "e basta a servire tutto il paese"),           # DICHIARATA: verbo + preposizione
    ("Il parroco dice la messa alle dieci.",
     "Il parroco dice la messa alle dieci in cattedrale.",
     "e sale sul campanile ogni giorno"),            # DICHIARATA: verbo in -ale
]
CODE_DICHIARATE = {13, 16, 26, 28, 29}  # indici 0-based delle cinque code che la regola dichiara di non prendere

# coordinazioni di nomi o aggettivi: UN claim, non due
CONTROLLI = [
    "La sala e la mensa restano chiuse ad agosto.",
    "Il modulo è stabile e veloce in tutte le prove.",
    "Il corso è breve e intenso per i nuovi assunti.",
    "La pratica è completa e leggibile.",
    "Il tetto e la grondaia perdono acqua.",
    "Una firma e una data mancano sul modulo.",
    "La lettera e la busta pesano poco.",
    "Il piano e la mano sono nel disegno.",
    "La casa è vecchia e umida d'inverno.",
    "La stanza è pulita e libera ogni mattina.",     # DICHIARATO: aggettivo in -a + determinante
]
SOGLIA_DECOMP = {"A": 50, "B": 60, "C": 80}


def carica_atomic_claims(wt: str):
    p = pathlib.Path(wt) / "verimem" / "atomic_claims.py"
    spec = importlib.util.spec_from_file_location(f"ac_{abs(hash(wt))}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def composta(i: int) -> str:
    testa, _f, coda = COMPOSTE[i]
    return testa.rstrip(".") + " " + coda + "."


def parte_decomp(wt_a: str, wt_b: str, wt_c: str) -> int:
    print(f"{len(COMPOSTE)} composte, {len(CONTROLLI)} controlli · dichiarate: {sorted(CODE_DICHIARATE)}")
    esito = {}
    for nome, wt in (("A", wt_a), ("B", wt_b), ("C", wt_c)):
        ac = carica_atomic_claims(wt)
        spezzate = [i for i in range(len(COMPOSTE)) if len(ac.decomponi(composta(i))) >= 2]
        errori = [c for c in CONTROLLI if len(ac.decomponi(c)) >= 2]
        esito[nome] = (spezzate, errori)
        q = 100 * len(spezzate) / len(COMPOSTE)
        verdetto = ("REGGE" if (q <= SOGLIA_DECOMP[nome]) else "FALSIFICATA") if nome != "C" else \
                   ("REGGE" if (q >= 80 and len(errori) <= 1) else "FALSIFICATA")
        print(f"\nbraccio {nome} ({wt.split('/')[-1]}): spezzate {len(spezzate)}/{len(COMPOSTE)} = {q:.0f}% · "
              f"controlli spezzati per errore {len(errori)}/{len(CONTROLLI)} -> P-B{'123'['ABC'.index(nome)]} {verdetto}")
        if nome == "C":
            fuse = [i for i in range(len(COMPOSTE)) if i not in spezzate]
            print(f"   fuse: {fuse} · di cui dichiarate {sorted(set(fuse) & CODE_DICHIARATE)} · NON dichiarate {sorted(set(fuse) - CODE_DICHIARATE)}")
            for i in fuse:
                print(f"     {i:2d} «{composta(i)}»")
            for c in errori:
                print(f"   errore sul controllo: «{c}» -> {ac.decomponi(c)}")
    return 0


def parte_giudice(wt_giudice: str, wt_c: str) -> int:
    sys.path.insert(0, wt_giudice)
    import os
    os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
    import verimem
    from verimem.grounding_gate import LOCAL_CE_MOAT_THRESHOLD, _ce_band_enforced, _ce_band_tau_hi
    from verimem.local_grounding import get_local_judge, try_local_score
    print("IMPORT DA", verimem.__file__)
    t0 = time.perf_counter()
    get_local_judge()._ensure_scorer()
    # LE SOGLIE DEL PRODOTTO, non `judge.threshold` (che e' il «threshold» di
    # gate_config.json, 99,64: la prima esecuzione delle 12:29 lo usava come
    # soglia e diceva che nemmeno le teste vere passavano — errore del banco,
    # dichiarato). Il prodotto ammette a >= tau_hi (80), tiene in REVIEW fra il
    # moat (40) e tau_hi quando la banda e' accesa, quarantina sotto 40.
    lo, hi, banda = float(LOCAL_CE_MOAT_THRESHOLD), float(_ce_band_tau_hi()), _ce_band_enforced()
    print(f"warmup {time.perf_counter() - t0:.1f} s · soglie del prodotto: moat {lo} · tau_hi {hi} · banda {'ON' if banda else 'OFF'}"
          f" (threshold di gate_config, NON usato: {get_local_judge().threshold})")

    def verdetto(g: float | None) -> str:
        if g is None:
            return "none"
        if g >= hi or (not banda and g >= lo):
            return "AMMESSO"
        return "REVIEW" if g >= lo else "QUARANTENA"

    ac = carica_atomic_claims(wt_c)
    from collections import Counter
    v_intero, v_testa, v_coda = Counter(), Counter(), Counter()
    righe = []
    for i in range(len(COMPOSTE)):
        testa, fonte, _coda = COMPOSTE[i]
        tutto = composta(i)
        g_intero = try_local_score(fonte, tutto)
        g_testa = try_local_score(fonte, testa)
        claims = ac.decomponi(tutto)
        g_coda = None
        if len(claims) >= 2:
            r = try_local_score(fonte, claims[-1])
            g_coda = None if r is None else float(r[0])
            v_coda[verdetto(g_coda)] += 1
        gi = None if g_intero is None else float(g_intero[0])
        gt = None if g_testa is None else float(g_testa[0])
        v_intero[verdetto(gi)] += 1
        v_testa[verdetto(gt)] += 1
        righe.append((i, gi, gt, g_coda, claims[-1][:50] if len(claims) >= 2 else "(fusa)"))
    n = len(COMPOSTE)
    n_sp = sum(v_coda.values())
    print(f"\nINTERO (testa vera + coda falsa), stessa fonte: {dict(v_intero)} -> P-B5 (ammesso >= 50%): "
          f"{'REGGE' if v_intero['AMMESSO'] >= n / 2 else 'FALSIFICATA'}")
    print(f"TESTA vera con la sua fonte: {dict(v_testa)} -> P-B4b (ammessa >= 90%): "
          f"{'REGGE' if v_testa['AMMESSO'] >= 0.9 * n else 'FALSIFICATA'}")
    print(f"CODA falsa isolata dal braccio C ({n_sp} spezzate): {dict(v_coda)} -> P-B4a (quarantena >= 80%): "
          f"{'REGGE' if n_sp and v_coda['QUARANTENA'] >= 0.8 * n_sp else 'FALSIFICATA'}"
          f" · non ammessa (quarantena + review): {n_sp - v_coda['AMMESSO']}/{n_sp}")
    print(f"\n{'i':>2}  intero   testa    coda   claim di coda")
    for i, gi, gt, gc, c in righe:
        f = lambda v: "  None" if v is None else f"{v:6.1f}"  # noqa: E731
        print(f"{i:2d}  {f(gi)}  {f(gt)}  {f(gc)}  {c}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "decomp":
        raise SystemExit(parte_decomp(sys.argv[2], sys.argv[3], sys.argv[4]))
    if len(sys.argv) >= 4 and sys.argv[1] == "giudice":
        raise SystemExit(parte_giudice(sys.argv[2], sys.argv[3]))
    print(__doc__)
    raise SystemExit(2)
