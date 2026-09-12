#!/usr/bin/env python3
"""CHI SIAMO — l'elenco delle sessioni, in UN posto solo, e la regola per cercarlo.

    python scripts/nomi_delle_sessioni.py --autotest    # prova che il criterio regge
    python scripts/nomi_delle_sessioni.py --elenco      # stampa chi c'e' dentro

PERCHE' ESISTE. Il 12/09 lo stesso elenco viveva in QUATTRO posti con TRE
contenuti diversi, e ognuno sbagliava in modo suo:

    scripts/nomi_nei_documenti.py            9 nomi, senza i soprannomi
    scripts/messaggio_pulito.py              8 nomi, senza `Curie`
    docs/stato-reale/banchi/…controfirme…    `Varco|Paragone|Aldo|Galileo`
    docs/stato-reale/banchi/…indice-di-colonna…  `ws\\d|lead-audit|Lanterna|Galileo`

⇒ Un messaggio che nominava `Curie` passava pulito dal primo; una pulizia che
arrivava a «zero nomi» ne lasciava 495, perche' il righello non conosceva
`Varco`. **L'elenco E' il criterio**: due elenchi sono due criteri, e divergono
il giorno in cui nascono. Questo file e' la superficie unica; chi cerca nomi lo
importa e non ne riscrive un altro.

    # da scripts/
    from nomi_delle_sessioni import trova
    # da docs/stato-reale/banchi/
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
    from nomi_delle_sessioni import trova

────────────────────────────────────────────────────────────────────────────
LE DUE CLASSI, e perche' non e' una questione di gusto.

Un nome che e' ANCHE una parola italiana comune non si puo' cercare ignorando
le maiuscole, o il righello boccia la prosa: misurato il 12/09, cercando
`\\btara\\b` senza distinguere maiuscole si bocciano

    «se la guardia si tara sulla somiglianza»      (verbo tarare)
    «con UN solo vero positivo non si tara una soglia»

che non nominano nessuno. E' la stessa famiglia della sostituzione cieca che ha
scritto `cDati` al posto di `caldo` in 200+ punti.

⚠️ E NON SI DECIDE CONTANDO. Il primo criterio che avevo provato era «se la
forma minuscola compare >= 3 volte allora e' una parola comune»: dava AMBIGUO a
`galileo` (4) e `iris` (25) — che in minuscolo compaiono solo dentro nomi di
ramo e prefissi temporanei — e SICURO a `tara` (2), le cui due occorrenze sono
tutt'e due il verbo. **Contare le occorrenze non dice se una parola e' una
parola.** La classificazione e' scritta qui sotto una per una, con la ragione.
"""
from __future__ import annotations

import argparse
import re
import sys

#: Le sigle. Per decisione del 12/09 RESTANO nei nomi dei file: rinominare 447
#: banchi costa piu' di quel che rende e rompe i riferimenti. Restano un nome:
#: chi misura il CONTENUTO le conta, chi misura i PERCORSI no.
SIGLE = ("ws1", "ws2", "ws3", "ws4", "ws5", "ws6", "ws7", "ws8")

#: I ruoli interni. `lead-audit` e' un indirizzo sul canale, non una persona,
#: ma da fuori non significa niente: vale come nome.
RUOLI = ("lead-audit",)

#: Nomi propri che in italiano NON sono nient'altro: si cercano ignorando le
#: maiuscole, cosi' si prendono anche `MARIE` e `marie`. Il confine di parola
#: basta a non prenderli dentro altre parole (`caldo` non contiene `\\baldo\\b`,
#: `marieterapia` non contiene `\\bmarie\\b`).
UMANI_SICURI = ("Marie", "Corrado", "Galileo", "Nadia", "Aldo", "Giano", "Vega")

#: Nomi che sono ANCHE parole italiane comuni: si cercano SOLO nella forma
#: maiuscola (`Tara`, `TARA`) e mai in quella minuscola. La ragione accanto a
#: ciascuno, perche' fra sei mesi sembrera' una scelta arbitraria.
AMBIGUI = {
    "Tara": "il verbo «tarare» (si tara, tarare) e il nome comune «tara»",
    "Iris": "il fiore, e il prefisso `iris-…` dei percorsi temporanei di un run",
    "Curie": "l'unita' di misura della radioattivita'",
    "Varco": "il nome comune «varco» (apertura)",
    "Paragone": "il nome comune «paragone» (confronto)",
    "Lanterna": "il nome comune «lanterna»",
    "Riscontro": "il nome comune «riscontro» e il verbo «riscontrare»",
    "Ester": "la classe di composti chimici",
    "Saggiatore": "«Il Saggiatore» di Galileo, e il nome comune (chi saggia)",
}

# ⚠️ L'ELENCO E' CRESCIUTO DUE VOLTE NELLO STESSO GIORNO, dopo che due volte
# l'avevo dichiarato completo. E' il fatto piu' importante di questo file.
#
#   14:20  aggiunti Varco, Paragone, Lanterna — trovati leggendo i CONTESTI
#          dei file che restavano, non cercandoli
#   14:35  aggiunti Vega, Riscontro, Ester — trovati con la forma canonica
#          `ws<N> «Nome»`
#   15:15  aggiunto Saggiatore — nominato da una PR di un altro, e la mia
#          ricerca non lo trovava: sta scritto `# ws3 Saggiatore`, SENZA le
#          caporali, e io cercavo `ws<N> «Nome»`. Il righello descriveva la
#          FORMA che avevo in mente, non l'oggetto.
#
# ⇒ Un elenco di nomi non e' mai finito: le sessioni cambiano soprannome (ws2
# e' stata «Vega» e poi «Varco»). Non e' un argomento per rinunciare — e'
# l'argomento per tenerlo in UN posto: cosi' aggiungerne uno cura tutti i
# righelli insieme, invece di curarne uno e lasciare gli altri a mentire.
FORME_CERCATE = (
    "@Nome", "firma @Nome", "Agent: Nome", "ws<N> «Nome»", "ws<N> Nome",
)

#: ⚠️ QUESTI NON SONO NOMI, SONO I RUOLI CON CUI SI SOSTITUISCONO — «ws3
#: «Ricerca»», «ws5 «Piattaforma»». Compaiono nella stessa forma dei soprannomi
#: e sono la CURA, non il difetto: metterli qui dentro farebbe bocciare le
#: parole «ricerca», «dati», «porte», «release». Stanno scritti per chi un
#: giorno li trovera' con la stessa interrogazione e si chiedera' perche'
#: mancano.
NON_SONO_NOMI = ("Ricerca", "Piattaforma", "Dati", "Porte", "Release",
                 "Product Owner", "Riscontro")

#: File esclusi per decisione (12/09 14:12 e 14:34): sono DATI DI PROVA, e
#: riscriverli falsifica un reperto registrato invece di ripulire un documento.
ESCLUSI_DI_DIRITTO = ("00-ESAME.md",)

_SICURI = re.compile(
    r"\b(?:" + "|".join(SIGLE + RUOLI + UMANI_SICURI) + r")\b", re.IGNORECASE)
_AMBIGUI = re.compile(
    r"\b(?:" + "|".join(f"{n}|{n.upper()}" for n in AMBIGUI) + r")\b")
#: Un nome attaccato a `-` o `_` dentro un token piu' lungo e' un
#: IDENTIFICATORE, non prosa: `iris-ub-jivzor1t`, `"misura-iris"`,
#: `prefix="iris-uc-"`. Per decisione del 12/09 non si toccano: cambiarli
#: falsifica i dati di una misura. `lead-audit` non passa di qui: e' gia' una
#: voce intera dell'elenco.
_IDENTIFICATORE = re.compile(r"[A-Za-z0-9]+[-_]|[-_][A-Za-z0-9]+")


def _e_un_identificatore(testo: str, inizio: int, fine: int) -> bool:
    prima = testo[max(0, inizio - 1):inizio]
    dopo = testo[fine:fine + 1]
    if prima in "-_" and testo[max(0, inizio - 2):inizio - 1].isalnum():
        return True
    return dopo in "-_" and testo[fine + 1:fine + 2].isalnum()


def trova(testo: str, *, con_identificatori: bool = False) -> list[tuple[str, int]]:
    """I nomi di sessione nel testo, come (nome trovato, posizione).

    `con_identificatori=True` include anche le occorrenze dentro un
    identificatore generato, che per decisione sono escluse dalla pulizia.
    """
    esiti: list[tuple[str, int]] = []
    for regola in (_SICURI, _AMBIGUI):
        for m in regola.finditer(testo):
            if not con_identificatori and _e_un_identificatore(testo, m.start(), m.end()):
                continue
            esiti.append((m.group(0), m.start()))
    return sorted(esiti, key=lambda x: x[1])


CASI: list[tuple[str, str, bool]] = [
    # (nome del caso, testo, ci aspettiamo che TROVI qualcosa)
    ("una sigla", "rilievo di ws5", True),
    ("un ruolo interno", "chiesto da lead-audit", True),
    ("un nome sicuro, minuscolo", "trovato da marie", True),
    ("un nome sicuro, MAIUSCOLO", "firmato TARA", True),
    ("dentro un'altra parola NON conta", "il parser marieterapia", False),
    ("«caldo» non contiene «Aldo»", "il percorso caldo e il freddo", False),
    # I due che hanno fatto nascere questo file.
    ("il verbo «tarare» NON e' un nome", "se la guardia si tara sulla somiglianza", False),
    ("«non si tara una soglia» NON e' un nome", "con un vero positivo non si tara una soglia", False),
    ("ma «Tara» maiuscolo SI'", "misurato da Tara il 04/09", True),
    ("«varco» minuscolo NON e' un nome", "il varco fra le due porte era largo", False),
    ("«Varco» maiuscolo SI'", "CONTROFIRMATA da ws2 «Varco»", True),
    ("«paragone» minuscolo NON e' un nome", "per paragone la porta vecchia", False),
    ("«riscontro» minuscolo NON e' un nome", "un riscontro sul corpus vero", False),
    # Il decimo nome, trovato il 15:15 perche' l'ha nominato la PR di un altro:
    # sta scritto senza caporali e la mia ricerca cercava solo `ws<N> «Nome»`.
    ("il nome scritto SENZA caporali", "# ws3 Saggiatore — gli aperti del giorno", True),
    ("«saggiatore» minuscolo NON e' un nome", "chi saggia il metallo e' il saggiatore", False),
    # La classe che il 12/09 e' stata esclusa per decisione.
    ("un identificatore generato NON e' prosa", 'prefix="iris-ub-jivzor1t"', False),
    ("«misura-iris» NON e' prosa", '{"name": "misura-iris", "version": "0"}', False),
    ("ma «Iris» in prosa SI'", "il reperto e' di Iris, letto stamattina", True),
    # I ruoli con cui si sostituisce: non devono accendersi MAI.
    ("«ricerca» e' un ruolo, non un nome", "la ricerca sui sei muri", False),
    ("«piattaforma» idem", "la piattaforma regge sei sessioni", False),
]


def autotest() -> int:
    esiti = []
    for nome, testo, atteso in CASI:
        trovati = trova(testo)
        ok = bool(trovati) == atteso
        esiti.append(ok)
        print(f"  [{'OK ' if ok else 'ROSSO'}] {nome:44s} -> "
              f"{[t for t, _ in trovati] or 'niente'}")
    # Il controllo che impedisce all'elenco di svuotarsi senza che nessuno
    # se ne accorga: un elenco vuoto passerebbe tutti i casi negativi.
    pieno = len(SIGLE) + len(RUOLI) + len(UMANI_SICURI) + len(AMBIGUI)
    esiti.append(pieno >= 20)
    print(f"  [{'OK ' if pieno >= 20 else 'ROSSO'}] {'l elenco non si e svuotato':44s} -> "
          f"{pieno} voci")
    print()
    if all(esiti):
        print(f"AUTOTEST VERDE: {len(esiti)} casi su {len(esiti)} — i nomi si "
              "trovano, le parole comuni no.")
        return 0
    print(f"AUTOTEST ROSSO: {esiti.count(False)} casi sbagliati su {len(esiti)}.")
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--autotest", action="store_true")
    p.add_argument("--elenco", action="store_true")
    a = p.parse_args(argv)
    if a.autotest:
        return autotest()
    if a.elenco:
        print(f"  sigle          : {', '.join(SIGLE)}")
        print(f"  ruoli          : {', '.join(RUOLI)}")
        print(f"  nomi sicuri    : {', '.join(UMANI_SICURI)}   (maiuscole ignorate)")
        print("  nomi ambigui   : (solo nella forma maiuscola)")
        for n, perche in AMBIGUI.items():
            print(f"      {n:12s} {perche}")
        print(f"  NON sono nomi  : {', '.join(NON_SONO_NOMI)}")
        print(f"  esclusi        : {', '.join(ESCLUSI_DI_DIRITTO)}")
        return 0
    p.error("serve --autotest o --elenco")
    return 2


if __name__ == "__main__":
    sys.exit(main())
