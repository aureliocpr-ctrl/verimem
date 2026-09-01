"""Conta i verdetti di `docs/stato-reale/00-ESAME.md`.

Esiste perche' il conto a occhio ha sbagliato: una cella che dice
«🟢 sì, dopo cura (era 🔴)» contiene entrambi i simboli, e un `grep` che
cerca «contiene 🔴» la conta rossa. Il 28/08 tre celle su 69 erano
classificate cosi', e il conto pubblicato nel registro era sbagliato.

Il verdetto di una cella e' il PRIMO simbolo della sua colonna verdetto,
non un simbolo qualsiasi nel testo.

Quando la legenda del registro guadagna uno stato, va aggiunto QUI: il 28/08
e' stato introdotto `RITIRATA` e per qualche minuto lo script ha continuato a
segnalare quelle celle come «senza verdetto» — lo strumento che verifica una
convenzione invecchia insieme a lei.

    python scripts/conta_celle_esame.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

REGISTRO = Path(__file__).resolve().parent.parent / "docs" / "stato-reale" / "00-ESAME.md"

#: una riga-cella: `| <id> | <domanda> | ... |` con almeno le nove colonne.
RIGA_CELLA = re.compile(r"^\| [\w-]+ \|")
#: la sigla VERA di una cella del registro: `LANT-n` o `Wn-n`, con l'eventuale
#: suffisso di lettera. Serve a separare le celle dalle righe delle altre
#: tabelle che vivono nello stesso file.
RIGA_CELLA_VERA = re.compile(r"^\| (?:LANT|W\d)-\d+[a-z]? \|")
#: 🔴 31/08 02:40 — SEPARARE LE COLONNE CON `split("|")` E' SBAGLIATO.
#: @ws2 (02:32) ha trovato che un `|` NON escapato dentro una cella la TRONCA
#: alla scrittura, senza errore. Il complemento: un `\|` ESCAPATO **non**
#: tronca — il markdown lo rende — ma per `split("|")` e' comunque un
#: separatore. Misurato sul registro: **10 celle su 573** hanno un escape
#: (2 mie, 7 di ws2, 1 di ws8) e una arriva a **20 colonne contare invece di
#: 16**. ⚠️ In tutte e 10 la colonna 6 risulta IDENTICA coi due criteri: il
#: difetto **oggi non morde** — ma e' una TRAPPOLA ARMATA, innocua solo
#: perche' gli escape stanno DOPO il verdetto. Il giorno che uno finisce
#: prima, questo script legge come verdetto un pezzo di frase, **e non emette
#: alcun segnale**.
COLONNE = re.compile(r"(?<!\\)\|")
#: il verdetto e' il PRIMO simbolo, non uno qualsiasi: vedi il docstring.
SIMBOLO = re.compile(r"[🔴🟢🟡⛔🚫📋]")   # 📋 = cella di metodo (30/08)
#: i simboli che NON sono verdetti ma vengono usati come tali: servono a dire
#: all'autrice cosa ha scritto, non a indovinare cosa intendeva. Il 28/08 cinque
#: celle usavano ✅ o ⚠️ — la terza volta in un giorno che qualcuno prende il
#: simbolo piu' naturale invece di uno dei cinque, e ogni volta il difetto era
#: della legenda, non di chi la usava.
ALTRI_SIMBOLI = re.compile(r"[✅⚠️❌⚪🆕🔧🚨]")   # 📋 e' uscito da qui: ora e' in legenda


def verdetto(riga: str) -> str:
    trovato = SIMBOLO.search(COLONNE.split(riga)[6])
    return trovato.group(0) if trovato else "?"


def main() -> int:
    testo = REGISTRO.read_text(encoding="utf-8")
    celle = [
        r for r in testo.splitlines()
        if RIGA_CELLA.match(r) and len(COLONNE.split(r)) >= 10
    ]
    conto = Counter(verdetto(r) for r in celle)

    #: ⚠️ il pattern LARGO accetta qualunque riga che apra con una parola fra
    #: barre, e nel file ci sono ALTRE TABELLE (liste numerate di cancelli, di
    #: comandi, di verifiche) che hanno un verdetto nella stessa colonna: quelle
    #: righe finivano nel semaforo. Stesso difetto curato il 01/09 alle 20:28 in
    #: `celle_load_bearing.py` — era una COPIA dello stesso pattern, e curarne
    #: una sola avrebbe lasciato in piedi il numero che pubblico piu' spesso.
    #: Stampo il vecchio ACCANTO al nuovo: la differenza dev'essere leggibile.
    strette = [r for r in celle if RIGA_CELLA_VERA.match(r)]
    if len(strette) != len(celle):
        spurie = Counter(verdetto(r) for r in celle if not RIGA_CELLA_VERA.match(r))
        print(f"⚠️  il pattern largo contava {len(celle)} righe, quelle con una "
              f"sigla vera sono {len(strette)} — {len(celle)-len(strette)} "
              f"venivano da ALTRE TABELLE del file")
        print(f"     e portavano con se' questi verdetti: "
              f"{dict(sorted(spurie.items(), key=lambda kv: -kv[1]))}")
    celle, conto = strette, Counter(verdetto(r) for r in strette)

    ids = [RIGA_CELLA.match(r).group(0).strip("| ") for r in celle]
    doppi = sorted(k for k, v in Counter(ids).items() if v > 1)

    print(
        f"🔴 rossi {conto['🔴']} · 🟢 verdi {conto['🟢']} · "
        f"🟡 parziali {conto['🟡']}"
        + (f" · ⛔ non misurabili {conto['⛔']}" if conto["⛔"] else "")
        + (f" · 🚫 ritirate {conto['🚫']}" if conto["🚫"] else "")
        + (f" · 📋 di metodo {conto['📋']}" if conto["📋"] else "")
        + f"   (su {len(celle)} celle)"
    )
    if conto["?"]:
        #: 30/08 (LANT-98): queste NON sono tutte difettose. Guardando i verdetti
        #: veri invece del solo simbolo, 16 su 16 avevano un verdetto PIENO, di
        #: un tipo diverso: 🔑 chiave · ✅ verificato · 🔁 replica · 🎯 causa
        #: isolata · 🪞 autocritica · 📊 bilancio · 🗳️ voto.
        #: ⇒ **La legenda ha sei simboli per lo STATO della misura; noi ne usiamo
        #: altri per la NATURA del risultato. Sono DUE DIMENSIONI e la legenda ne
        #: copre una sola.** Chiamarle «senza simbolo di legenda» gonfiava il
        #: referto di 16 righe che non c'era niente da sistemare — ed e' la
        #: regola che avevo scritto io: *non segnalare come difetto cio' che e'
        #: legittimo; gonfiare il proprio referto e' lo stesso errore che
        #: smontiamo negli altri*.
        #: ⇒ La cura NON e' allargare la legenda — una legenda che cresce a ogni
        #: simbolo nuovo non e' piu' una legenda: e' lo STRUMENTO che smette di
        #: chiamarli difetti. Restano difetti solo i verdetti VUOTI.
        NATURA = re.compile(r"[🔑🔁🎯🪞📊🗳✅]")
        di_natura, vuoti = [], []
        for riga in celle:
            if verdetto(riga) != "?":
                continue
            col6 = COLONNE.split(riga)[6]
            (di_natura if NATURA.search(col6) else vuoti).append(riga)

        if di_natura:
            print(f"ℹ️  {len(di_natura)} celle con un verdetto di NATURA "
                  f"(🔑 chiave · 🔁 replica · 🎯 causa · 🪞 autocritica · 📊 bilancio "
                  f"· 🗳 voto · ✅ verificato) — **non sono difetti**:")
            print("     la legenda copre lo STATO della misura, questi dicono la NATURA")
            print("     del risultato. Due dimensioni diverse; nessuna cella da sistemare.")
        if vuoti:
            print(f"⚠️  {len(vuoti)} celle con la colonna verdetto VUOTA — queste si':")
            for riga in vuoti:
                ident = RIGA_CELLA.match(riga).group(0).strip("| ")
                altri = "".join(dict.fromkeys(ALTRI_SIMBOLI.findall(COLONNE.split(riga)[6])))
                autrice = COLONNE.split(riga)[7].strip()[:12]
                print(f"     {ident:9} (di {autrice or '?'}) usa «{altri or '—'}»"
                      f" — la legenda ha 🔴🟢🟡⛔🚫📋")
            print("   ⇒ il difetto e' della LEGENDA se il simbolo usato e' quello naturale:"
                  " chiedi all'autrice quale dei cinque intendeva, non cambiarlo tu.")
    # 29/08: una cella che contiene un blocco di codice (```) o un a-capo SPEZZA
    # la riga della tabella markdown: le righe di continuazione non fanno piu'
    # parte della tabella e la colonna non si allinea. Trovato addosso a me:
    # 19 celle su 20 rotte erano mie, e i due righelli che avevo usato per
    # cercarle si contraddicevano, perche' il primo filtrava su `count("|") >= 9`
    # e cosi' SALTAVA proprio le celle spezzate. Il controllo giusto e' banale:
    # una riga di tabella comincia con `|` e DEVE finire con `|`.
    testo = REGISTRO.read_text(encoding="utf-8")
    # 🔴 30/08: questo blocco chiamava tutto «SPEZZATE» e concludeva «difetto di
    # FORMA, nessun numero cambia». ERA FALSO, e la diagnosi sbagliata e' rimasta
    # per giorni davanti a chiunque eseguisse lo script. Sono DUE difetti:
    #   A  la cella e' su piu' righe fisiche e una continuazione la chiude
    #      -> vera resa rotta, il contenuto c'e'
    #   B  la riga e' SOLA, ha 8 pipe invece di 9 e la riga dopo e' gia' un'altra
    #      cella -> il testo e' TRONCATO, e cio' che manca e' l'ULTIMA colonna:
    #      il REGIME. Cioe' proprio il campo che rende la misura ripetibile.
    # ⇒ La differenza decide la cura: A si unisce, B NON si puo' riparare
    #   aggiungendo un `|` — lo si farebbe sembrare completo mentendo.
    righe_t = testo.splitlines()
    # 🔴 31/08 05:27 — IL NUMERO ROBUSTO VA STAMPATO PER PRIMO, e la
    # classificazione A/B dichiarata INDICATIVA. Misurato: le celle che non
    # chiudono con la barra sono **10** in quattro commit consecutivi
    # (5209dabe, 39b9ec0b, 108dd620, HEAD) — STABILE. Ma il referto e' passato
    # da «3 su piu' righe + 2 troncate» a «2 + 8» senza che nessuna di quelle
    # celle fosse toccata.
    # ⇒ La causa e' QUI: A e B si distinguono guardando la riga SUCCESSIVA, e
    #   in un file scritto da otto istanze in parallelo basta che qualcuno
    #   inserisca una cella vicino perche' la stessa riga cambi classe.
    # ⇒ 🔑 **Un criterio che guarda il CONTESTO e' instabile dove il contesto
    #   e' scritto da altri.** Il numero che non dipende dal vicinato — «la
    #   riga non chiude» — e' quello su cui si puo' ragionare.
    non_chiuse = [RIGA_CELLA.match(r).group(0).strip("| ")
                  for r in righe_t
                  if RIGA_CELLA.match(r) and not r.rstrip().endswith("|")]
    if non_chiuse:
        print(f"📏 {len(non_chiuse)} celle NON CHIUDONO con la barra "
              f"(numero robusto, non dipende dalle righe vicine)")
    A, B = [], []
    for i, r in enumerate(righe_t):
        if not (RIGA_CELLA.match(r) and not r.rstrip().endswith("|")):
            continue
        ident = RIGA_CELLA.match(r).group(0).strip("| ")
        dopo = righe_t[i + 1] if i + 1 < len(righe_t) else ""
        (B if (RIGA_CELLA.match(dopo) or not dopo.strip()) else A).append(ident)
    if A:
        # 🔴 31/08 03:55 — IL CONTEGGIO NON DICEVA LA MOLE, e «3 celle» suona
        # piccolo: sotto LANT-64 ci sono **407 righe consecutive** senza una
        # sola riga che cominci con la barra e senza righe vuote, cioe' un
        # blocco che il markdown NON rende come tabella. Un conteggio di celle
        # e una quantita' di righe raccontano cose diverse, e il referto
        # riportava solo la prima.
        # ⚠️ Il primo righello per la mole era troppo largo: contava «prosa in
        # mezzo alle celle» su tutto il documento e dava 9168 righe, il 65% —
        # ma quel 65% e' il documento, che alterna sezioni narrative e tabelle.
        # **Un numero implausibilmente grande e' un segnale sul righello, non
        # sul mondo**: il criterio giusto conta solo cio' che segue una cella
        # spezzata, fino alla prima riga vuota o alla prossima cella.
        def _continua(ident: str) -> int:
            k = next((x for x, r in enumerate(righe_t)
                      if r.startswith(f"| {ident} |")), None)
            if k is None:
                return 0
            j = k + 1
            while j < len(righe_t) and righe_t[j].strip() \
                    and not righe_t[j].startswith(("|", "#")):
                j += 1
            return j - k - 1

        mole = {i: _continua(i) for i in A}
        tot = sum(mole.values())
        print(f"⚠️  {len(A)} celle su PIU' RIGHE (resa rotta, contenuto integro) "
              f"— e sono {tot} RIGHE non rese come tabella:")
        print("     " + " · ".join(f"{i} ({n} righe)" for i, n in mole.items()))
        print("   ⇒ un blocco ``` dentro una cella va reso su una riga sola.")
        print("   ⇒ il CONTEGGIO delle celle non dice la MOLE: leggere entrambi.")
    if B:
        print(f"🔴 {len(B)} celle TRONCATE (manca l'ultima colonna, il REGIME):")
        print(f"     {' '.join(B[:14])}{' …' if len(B) > 14 else ''}")
        print("   ⚠️ la separazione fra le due classi guarda la riga SUCCESSIVA:")
        print("      in un file scritto in parallelo la stessa cella puo' cambiare")
        print("      classe senza essere toccata. Il numero sopra e' quello robusto.")
        print("   ⇒ NON e' un difetto di forma: il testo e' stato tagliato in scrittura")
        print("     e con esso il regime. Chiudere la riga con un `|` la fa sembrare")
        print("     completa e MENTE. O si recupera il regime, o si dichiara che manca.")
    print(f"id duplicati: {', '.join(doppi) if doppi else 'nessuno'}")
    return 1 if doppi or conto["?"] else 0


if __name__ == "__main__":
    sys.exit(main())
