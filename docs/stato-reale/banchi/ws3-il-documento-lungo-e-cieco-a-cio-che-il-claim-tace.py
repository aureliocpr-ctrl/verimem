# -*- coding: utf-8 -*-
"""Su un DOCUMENTO LUNGO il gate trova la contraddizione e perde l'omissione?

Tutte le nostre misure sul gate — ogni riga della vetrina — sono su fonti di
UNA FRASE. Un contratto e' 40 pagine. E sappiamo che la lunghezza sposta i
verdetti (9.6 -> 35.9 contro un taglio di 40; @ws4: una frase estranea porta
`quarantined 1.8` -> `ammesso 98.9`). Questo banco misura quel salto.

⚠️ LA PREDIZIONE NON E' UN'INTUIZIONE: E' LETTA NEL CODICE, e va scritta prima.
`grounding_gate.select_relevant_span` sceglie il pezzo di fonte da dare al
giudice ordinando le unita' per SOVRAPPOSIZIONE DI TOKEN COL CLAIM::

    ft = _span_tokens(fact.lower())                      # i token del CLAIM
    def _overlap(u): return len(_span_tokens(u.lower()) & ft)
    ranked = sorted(units, key=lambda u: (_overlap(u), -order[u]), reverse=True)

«Pure + deterministic — no embeddings». E a valle `local_grounding` riduce a
`max_length=512` TOKEN togliendo righe dal fondo.

⇒ Su una fonte lunga il gate vede **solo i pezzi che condividono PAROLE col
claim**. Da cui la predizione, dichiarata prima di eseguire::

    A. CONTRADDIZIONE — il claim nomina la cosa che la fonte smentisce, quindi
       condivide con essa quasi tutte le parole  ->  il selettore LA TROVA
       ->  l'esito sul lungo deve somigliare a quello sul corto.

    B. OMISSIONE — il claim afferma il fatto principale e TACE la condizione;
       la riga che porta la condizione ha POCHE parole in comune col claim
       ->  il selettore puo' NON SCEGLIERLA  ->  sul lungo passa piu' che sul
       corto.

🔑 E se regge, unifica il lavoro di stasera: `L4.1` guarda i VALORI del claim,
il selettore guarda i TOKEN del claim. **Il gate e' strutturalmente guidato da
cio' che il claim DICE, e cieco a cio' che TACE** — in due punti diversi, per la
stessa ragione.

DISEGNO — quattro regimi sulla stessa coppia, cambia SOLO la fonte:
  · CORTA        la sola frase decisiva                    (il nostro regime storico)
  · LUNGA-INIZIO la frase decisiva in cima al documento
  · LUNGA-META'  la frase decisiva a meta'
  · LUNGA-FONDO  la frase decisiva in fondo
La posizione e' inclusa perche' `_entro_la_finestra` toglie righe DAL FONDO: se
il verdetto cambia con la posizione, il punto cieco e' anche geografico.

CONTROLLI, senza i quali i numeri non si leggono:
  · un VERO per ogni regime, che DEVE essere ammesso (se il gate rifiuta tutto
    sul lungo, «0 ammessi» non significherebbe «regge»);
  · la coppia CORTA e' il riferimento: e' li' che abbiamo i numeri storici.

Regime: porta pubblica `verimem remember --source`, store TEMPORANEO, FUORI
pytest, un processo per caso (il flow-log si aggancia allo stderr reale dopo la
prima main()).

═══════════════════════════════════════════════════════════════════════════
ESITO — meta' predizione confermata, meta' FALSIFICATA. E il titolo di questo
banco e' sbagliato: il documento lungo NON e' il problema.

    regime         CONTRADDIZ   OMISSIONE   VERI rifiutati
    CORTA             0/3          3/3           1/3
    LUNGA-inizio      0/3          3/3           0/3
    LUNGA-meta        0/3          3/3           0/3
    LUNGA-fondo       0/3          3/3           0/3

✅ ① **LA CONTRADDIZIONE REGGE OVUNQUE**: 0 su 12, corta e lunga, in tutte e
tre le posizioni. Il selettore la trova, come predetto — e **la posizione non
conta**: nessun punto cieco geografico, benche' il troncamento tolga righe dal
fondo.

🔴 ② **LA MIA PREDIZIONE SULL'OMISSIONE E' FALSIFICATA, E IL VERO E' PEGGIORE.**
Avevo scritto «sul lungo passa PIU' che sul corto». Falso: passa **uguale** —
**3/3 in tutti e quattro i regimi, 12 su 12, sempre con `layers: -`**, cioe'
**zero controlli che parlano**. ⇒ Non c'e' degrado da misurare perche' **il
pavimento era gia' a terra**: l'omissione non e' mai stata coperta, ne' corta
ne' lunga. **Non e' un difetto del regime: e' una classe senza presidio.**

🟢 ③ **E UN RISULTATO POSITIVO CHE NON AVEVO PREVISTO: sul lungo il gate
sbaglia MENO sui veri.** Un VERO viene rifiutato sulla fonte CORTA
(`affidamento`, fermato da `L4-grounding`) e **nessuno** sulle tre fonti
lunghe: **1/3 contro 0/9**. Piu' contesto aiuta il giudice a riconoscere cio'
che e' vero.

🔑 ④ **COSA NE SEGUE, ed e' il risultato che conta.** Temevamo che il documento
lungo invalidasse meta' della matrice — «tutte le nostre misure sono su fonti di
una frase». **Non la invalida**: su questa coppia di classi il regime lungo da'
gli stessi verdetti sulle falsita' e verdetti *migliori* sui veri.
⇒ **Non ci sono due buchi (documento lungo + omissione): ce n'e' UNO SOLO,
l'omissione.** E il documento lungo, che sembrava il rischio piu' grande, e' il
regime in cui il prodotto si comporta meglio.

⚠️ LIMITI: n=3 per cella (12 per tipo su tutti i regimi) · **una sola coppia di
classi** (condizione taciuta su atto amministrativo) · italiano soltanto · il
«lungo» e' ~15 paragrafi, non 40 pagine — **la cella "documento da 40 pagine
reale" resta scoperta**, e questa volta il limite SOSPENDE l'estensione: non
dico nulla su documenti molto piu' lunghi di cosi'.
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

# ── il documento lungo: prosa amministrativa plausibile, nessun dato reale ────
_RIEMPITIVO = [
    "Il presente verbale raccoglie le determinazioni assunte dal consiglio "
    "direttivo nella seduta ordinaria, alla presenza dei membri effettivi.",
    "La segreteria ha provveduto alla convocazione nei termini previsti dallo "
    "statuto, trasmettendo l'ordine del giorno a tutti gli aventi diritto.",
    "Si da' atto che la documentazione preparatoria e' stata depositata presso "
    "gli uffici e resa consultabile nei sette giorni precedenti la riunione.",
    "Il presidente illustra l'andamento delle attivita' del periodo, "
    "soffermandosi sulle iniziative avviate nel corso del semestre.",
    "Viene richiamata la delibera precedente in materia di affidamenti, che "
    "resta il riferimento per le procedure di selezione dei fornitori.",
    "Il responsabile amministrativo espone la situazione delle disponibilita' "
    "di cassa e delle partite ancora aperte con i creditori.",
    "Si discute delle modalita' di rendicontazione adottate finora e delle "
    "possibili semplificazioni da introdurre nel prossimo esercizio.",
    "Alcuni membri chiedono chiarimenti sulle tempistiche di lavorazione delle "
    "pratiche e sull'organico attualmente impiegato negli uffici periferici.",
    "Viene dato conto delle comunicazioni pervenute dagli enti vigilanti e "
    "delle risposte gia' trasmesse entro i termini assegnati.",
    "Il consiglio prende atto della relazione sulle manutenzioni ordinarie "
    "effettuate presso le sedi operative nel corso dell'anno.",
    "Si registra un intervento sulla necessita' di aggiornare i recapiti "
    "presenti negli elenchi ufficiali, ormai non piu' allineati.",
    "La discussione prosegue sulle iniziative formative destinate al personale "
    "e sulla loro collocazione nel calendario delle attivita'.",
    "Viene ricordato che ogni variazione sostanziale deve essere riportata nel "
    "registro delle deliberazioni a cura della segreteria.",
    "Il presidente ringrazia i presenti per il contributo offerto e dichiara "
    "conclusa la trattazione dei punti all'ordine del giorno.",
]

#: (nome, frase DECISIVA, claim FALSO-per-contraddizione, claim FALSO-per-omissione, claim VERO)
CASI = [
    ("affidamento",
     "L'affidamento al fornitore Bertani e' subordinato all'approvazione "
     "preventiva del collegio dei revisori.",
     "L'affidamento al fornitore Bertani non e' subordinato all'approvazione "
     "del collegio dei revisori.",
     "Il consiglio ha disposto l'affidamento al fornitore Bertani.",
     "L'affidamento al fornitore Bertani richiede il via libera dei revisori."),
    ("rimborso",
     "Il rimborso delle spese di trasferta e' ammesso solo entro il limite "
     "mensile fissato dal regolamento interno.",
     "Il rimborso delle spese di trasferta non ha limiti mensili.",
     "Le spese di trasferta sono rimborsate al personale.",
     "Il rimborso delle trasferte ha un tetto mensile da regolamento."),
    ("proroga",
     "La proroga del contratto di servizio decorre dalla scadenza originaria "
     "ed e' condizionata alla verifica dei requisiti da parte dell'ufficio.",
     "La proroga del contratto di servizio non e' condizionata ad alcuna "
     "verifica dei requisiti.",
     "Il contratto di servizio e' stato prorogato.",
     "La proroga del contratto decorre dalla scadenza originaria."),
]

_MARK = "\n\n"


def _documento(frase: str, dove: str) -> str:
    """La frase decisiva immersa nel riempitivo, in tre posizioni."""
    n = len(_RIEMPITIVO)
    if dove == "inizio":
        blocchi = [frase] + _RIEMPITIVO
    elif dove == "meta":
        blocchi = _RIEMPITIVO[: n // 2] + [frase] + _RIEMPITIVO[n // 2:]
    else:  # fondo
        blocchi = _RIEMPITIVO + [frase]
    return _MARK.join(blocchi)


def _esegui_in_processo(claim: str, source: str) -> tuple[str, str]:
    """Un processo per caso. Ritorna (esito, layer)."""
    env = dict(os.environ)
    d = tempfile.mkdtemp(prefix="ws3_lungo_")
    env["HIPPO_DATA_DIR"] = d
    env["ENGRAM_DATA_DIR"] = d
    env["HIPPO_RERANK_PRELOAD"] = "0"
    env["PYTHONUTF8"] = "1"
    code = (
        "import sys, io, contextlib, re\n"
        "from verimem.cli import main\n"
        "claim = sys.argv[1]; src = sys.argv[2]\n"
        "buf = io.StringIO()\n"
        "sys.argv = ['verimem','remember',claim,'--source',src]\n"
        "try:\n"
        "    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf): main()\n"
        "except SystemExit: pass\n"
        "o = buf.getvalue()\n"
        "esito = 'admitted' if re.search(r'\\badmitted\\b', o) else "
        "('quarantined' if re.search(r'\\bquarantined\\b', o) else '?')\n"
        "lay = re.findall(r'L\\d+(?:\\.\\d+)?(?:-[a-z-]+)?|L4-[a-z-]+|store-screen', o)\n"
        "print('RES', esito, '+'.join(sorted(set(lay))) or '-')\n"
    )
    p = subprocess.run([sys.executable, "-c", code, claim, source],
                       capture_output=True, text=True, env=env, timeout=600)
    for r in (p.stdout or "").splitlines():
        if r.startswith("RES "):
            _, esito, lay = (r.split(" ", 2) + ["-"])[:3]
            return esito, lay
    return "ERRORE", (p.stderr or "")[-60:]


def main() -> None:
    regimi = [("CORTA", None), ("LUNGA-inizio", "inizio"),
              ("LUNGA-meta", "meta"), ("LUNGA-fondo", "fondo")]
    print("%-14s %-12s %-14s %-13s %s" % ("regime", "caso", "tipo", "esito", "layer"))
    print("-" * 78)
    tot: dict[tuple[str, str], int] = {}
    for nome_reg, dove in regimi:
        for nome, frase, falso_contr, falso_omiss, vero in CASI:
            src = frase if dove is None else _documento(frase, dove)
            for tipo, claim in (("CONTRADDIZ", falso_contr),
                                ("OMISSIONE", falso_omiss),
                                ("VERO-ctrl", vero)):
                esito, lay = _esegui_in_processo(claim, src)
                if tipo == "VERO-ctrl":
                    male = esito != "admitted"
                    marca = "  <<< VERO RIFIUTATO" if male else ""
                else:
                    male = esito != "quarantined"
                    marca = "  <<< SFUGGE" if male else ""
                tot[(nome_reg, tipo)] = tot.get((nome_reg, tipo), 0) + (1 if male else 0)
                print("%-14s %-12s %-14s %-13s %s%s"
                      % (nome_reg, nome, tipo, esito, lay, marca))
        print("-" * 78)

    print("\n=== SINTESI — quanti su 3 vanno MALE per regime e tipo ===")
    print("%-14s %-12s %-12s %s" % ("regime", "CONTRADDIZ", "OMISSIONE", "VERI rifiutati"))
    for nome_reg, _ in regimi:
        print("%-14s %-12s %-12s %s"
              % (nome_reg,
                 "%d/3" % tot.get((nome_reg, "CONTRADDIZ"), 0),
                 "%d/3" % tot.get((nome_reg, "OMISSIONE"), 0),
                 "%d/3" % tot.get((nome_reg, "VERO-ctrl"), 0)))
    print("\nPredizione dichiarata PRIMA di eseguire: la CONTRADDIZIONE regge sul")
    print("lungo (il selettore la trova per sovrapposizione di token), l'OMISSIONE")
    print("peggiora rispetto alla CORTA. Se peggiorano uguale, la lettura del")
    print("codice e' sbagliata e va detto.")


if __name__ == "__main__":
    main()
