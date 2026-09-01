r"""Da quando e' rosso quel test, e perche': non un difetto, DUE PRESIDI IN CONFLITTO.

Chiude il limite che @ws8 ha dichiarato: «*rosso il 28/08 e rosso adesso, **non so
da quando**»*. E risponde alla domanda che veniva prima e che nessuno aveva posto:
`valori_non_nella_fonte` **perdona** il 999, o non lo **vede**?

IL ROSSO: `tests/test_la_fonte_si_legge_intera.py` —
`test_un_numero_che_la_fonte_NON_contiene_resta_assente` fallisce perche'
`valori_non_nella_fonte("...alla riga 999.", FONTE_GIT_GREP)` torna `[]`.

LE DUE MISURE, nessuna delle due deducibile dal codice letto::

    ①  i DUE LATI sulla build corrente: cosa estrae il claim, cosa la fonte
    ②  lo STESSO claim contro `quantity_match.py` alla revisione PRIMA di
       `29ab5544` — la datazione, eseguita e non dedotta

⚠️ CONTROLLO in entrambe: la stessa frase **senza la parola «riga»**. Se il 999
sparisse anche li', a cambiare sarebbe l'estrattore in generale e la lettura
cadrebbe.

🟢 ESITO — **il test e' diventato rosso il 28/08 alle 20:58, con `29ab5544`, e la
causa e' una cura deliberata**::

    ① I DUE LATI, build corrente
       claim                          claim ->        fonte ->              assenti
       A  999 + path                  set()           {100.0, 354.0}        []     🔴
       B  354 + path (CTRL)           set()           {100.0, 354.0}        []     ✔
       C  999 SENZA path              set()           {100.0, 354.0}        []     🔴
       D  999 in frase ordinaria      {999.0}         {354.0}               [999]  ✔

    ② LA DATAZIONE
       claim                          PRIMA (27/08)   ORA (build corrente)
       con «riga 999»                 {999.0}         set()      ← cambia qui
       senza «riga» (CTRL)            {999.0}         {999.0}    ← non cambia

🔑 **PRIMA COSA: la funzione non PERDONA il 999, non lo VEDE.** Il lato claim non
produce nulla — e nemmeno nel caso `C`, dove il path non c'e'. ⇒ Non e' il nome di
file a mangiare il numero, e la cura `b7bc7b77` (che perdona i token presenti nella
fonte) **non c'entra**: e' il candidato ovvio, ed e' innocente.

🔑 **SECONDA: a togliere il numero e' LA PAROLA «riga».** Sta nell'elenco
`_RIFERIMENTO_RE` (`verimem/quantity_match.py:1074`, accanto a `pag|pagina|nota`),
una delle **tre potature** che il lato claim applica e il lato fonte no. Il docstring
di `extract_quantities` la dichiara: «*«art. 15» in un CLAIM e' un puntatore a una
norma, non un valore da confrontare*».

🔑 **TERZA, la datazione**: quella potatura nasce con **`29ab5544`, 28/08 20:58** —
«*«Art. 3» non e' piu' la quantita' 3: curato il falso negativo, RED->GREEN alla
porta*». Il test di @ws8 nasce il **16/08 23:59** (`da6d083e`) e **non e' mai stato
modificato** (un solo commit nella sua storia). ⇒ **E' stato verde dodici giorni, ed
e' diventato rosso il giorno stesso in cui @ws8 lo ha osservato.**

⇒ **NON E' UN DIFETTO: SONO DUE PRESIDI CHE SI CONTRADDICONO**, scritti tutti e due
apposta, a dodici giorni di distanza, da due misure diverse:
    16/08  «un numero che la fonte non dice non e' verificato»  → segnala 999
    28/08  «un riferimento non e' una quantita' da confrontare» → non lo guarda
E `riga 999` **e' tutte e due le cose**: un riferimento *e* un numero che la fonte
non contiene. ⇒ La cura non e' riparare una funzione. **E' decidere quale dei due
presidi vale quando un riferimento e' inventato** — e quella e' una decisione, non
una patch.

📌 **Cosa NON e' cambiato**, e viene dal banco fratello (`8114ce19`): alla porta il
claim con 999 **cade lo stesso**, a grounding 0.3. Il conflitto **non fa entrare un
fatto inventato**; toglie un presidio e ne lascia un altro.

🪞 **Un errore mio, lasciato scritto**: avevo annunciato «un solo candidato colpevole»
guardando `git log` di `valore_non_nella_fonte.py`. La causa stava in
`quantity_match.py`, che quel log non mostra. **Ho contato una porta sola su due** —
la funzione ha una dipendenza, e la storia di una funzione non e' la storia del suo
file.

REGIME: nessuno store, nessun gate, nessun daemon — solo `extract_quantities` e
`valori_non_nella_fonte`. La versione vecchia arriva da `git show`, l'albero **non
viene toccato**.
⚖️ PUNTI DEBOLI: la versione PRIMA e' caricata accanto al package corrente, quindi
misura `quantity_match` vecchio con il resto nuovo — vale per `extract_quantities`,
che e' una funzione di sole regex, non per una catena piu' lunga. E **non ho
eseguito il test di @ws8**: misuro le due funzioni che lui interroga.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-da-quando-il-test-di-ws8-e-rosso.py
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import verimem  # noqa: F401  — il package serve agli import relativi del modulo vecchio
from verimem.quantity_match import extract_quantities as ora
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

#: il commit che introduce la potatura dei riferimenti
CURA = "29ab5544"

#: la fonte del test di @ws8, verbatim
FONTE = ("verimem/cli.py:100:    console.print(intestazione)\n"
         "verimem/cli.py-354-    console.print(riepilogo)\n")

CLAIM_999 = "Il riepilogo viene stampato alla riga 999 di verimem/cli.py."
CLAIM_354 = "Il riepilogo viene stampato alla riga 354 di verimem/cli.py."
CLAIM_NUDO = "Il riepilogo viene stampato alla riga 999 del file."
CLAIM_CTRL = "Il totale dei pezzi consegnati e' 999."
FONTE_CTRL = "Il totale dei pezzi consegnati e' 354."


def _versione_prima():
    """`extract_quantities` alla revisione precedente a CURA, senza toccare l'albero."""
    testo = subprocess.run(["git", "show", "%s^:verimem/quantity_match.py" % CURA],
                           capture_output=True, text=True, encoding="utf-8", check=True).stdout
    tmp = Path(tempfile.mkdtemp()) / "quantity_match_prima.py"
    tmp.write_text(testo, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("verimem.quantity_match_prima", tmp)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verimem.quantity_match_prima"] = mod
    spec.loader.exec_module(mod)
    return mod.extract_quantities


def _riga(nome, claim, fonte, deve_segnalare):
    """`deve_segnalare` dice cosa e' GIUSTO su questa riga: senza, `[]` sul
    controllo B — dove il numero nella fonte c'e' davvero — si stamperebbe rosso."""
    assenti = valori_non_nella_fonte(claim, fonte)
    esito = [v.valore for v in assenti]
    ok = bool(esito) == deve_segnalare
    print("  %-26s %-16s %-26s %s %s" % (
        nome, ora(claim) or "set()", ora(fonte, come_fonte=True) or "set()",
        esito if esito else "[]", "✔" if ok else "🔴"))


def main():
    print("① I DUE LATI, build corrente\n")
    print("  %-26s %-16s %-24s %s" % ("claim", "claim ->", "fonte ->", "assenti"))
    print("  " + "-" * 84)
    _riga("A 999 + path", CLAIM_999, FONTE, True)
    _riga("B 354 + path (CTRL)", CLAIM_354, FONTE, False)
    _riga("C 999 SENZA path", CLAIM_NUDO, FONTE, True)
    _riga("D 999 frase ordinaria", CLAIM_CTRL, FONTE_CTRL, True)

    prima = _versione_prima()
    print("\n② LA DATAZIONE — stesso claim contro %s^\n" % CURA)
    print("  %-26s %-16s %s" % ("claim", "PRIMA", "ORA"))
    print("  " + "-" * 60)
    for nome, testo in (("con «riga 999»", CLAIM_999), ("senza «riga» (CTRL)", CLAIM_CTRL)):
        print("  %-26s %-16s %s" % (nome, prima(testo) or "set()", ora(testo) or "set()"))

    print("\n=== SINTESI ===")
    va_prima = any(v == 999.0 for _, v in prima(CLAIM_999))
    va_ora = any(v == 999.0 for _, v in ora(CLAIM_999))
    ctrl_ok = any(v == 999.0 for _, v in prima(CLAIM_CTRL))
    if not ctrl_ok:
        print("  ⚠️ IL CONTROLLO NON REGGE nella versione vecchia: il confronto non vale.")
    elif va_prima and not va_ora:
        print("  🔑 PROVATO: prima il 999 si vedeva, ORA no ⇒ il test e' diventato rosso")
        print("     con %s, il 28/08 alle 20:58 — e la causa e' una cura deliberata." % CURA)
        print("  ✔ controllo: senza «riga» il 999 si vede in ENTRAMBE ⇒ e' la PAROLA.")
    elif not va_prima and not va_ora:
        print("  ⚠️ non si vedeva nemmeno prima: %s NON e' la causa." % CURA)
    else:
        print("  ⚠️ esito inatteso: prima=%s ora=%s" % (va_prima, va_ora))


main()
