# -*- coding: utf-8 -*-
"""F1 · SIMULAZIONE del predicato `L4.3` — FUORI dal prodotto.

⚠️ COSA QUESTO FILE NON E': non e' la cura, non e' un layer, non tocca NESSUN
file di `verimem/`, non registra niente, non cambia nessuna ricevuta. E' un
banco come gli altri, in `docs/stato-reale/banchi/`. La modifica al prodotto
resta bloccata dalla review doppia, come da ordine di @lead-audit.

PERCHE' ESISTE: nel design doc ho scritto che le verifiche del meccanismo sono
«fatte A MANO SU CARTA, non eseguite: possono essere sbagliate, ed e' il PRIMO
posto dove guardare in review». Non voglio far rivedere a due sorelle un
ragionamento che magari non torna. Quindi lo eseguo.

LA REGOLA SIMULATA (design doc §1, col passo 3 gia' emendato dal §6):
  1. v non e' fra i valori della fonte        -> NON E' AFFARE NOSTRO (e' L4.1)
  2. le ancore del claim non stanno nella fonte -> ASTIENITI
  3. le ancore toccano una frase che contiene v
     ...E quella frase NON porta >=2 valori della stessa unita'  -> OK
     (l'emendamento: una frase con due valori della stessa unita' NON e' una
      finestra utilizzabile, quindi si cade ai passi 4/5. Nasce dalla misura
      dei grounding_span: 28,7% delle frasi con un valore ne portano due.)
  4. una frase con un'ancora porta un valore DIVERSO, stessa unita' -> SEGNALA
  5. altrimenti                                -> ASTIENITI (la fonte TACE)

CIO' CHE MI ASPETTO, scritto prima di eseguire:
  · i 12 SCAMBI          -> SEGNALA su >=7   (e' la predizione del design doc)
  · i falsi in CIFRA     -> 0 segnalazioni   (passo 1: il valore non c'e')
  · i falsi a PAROLE     -> 0 segnalazioni   (nessun valore estraibile)
  · le 3 OMISSIONI       -> 0 segnalazioni
  · i claim VERI         -> 0 segnalazioni
  · il caso «metformina / dosaggio» (gia' pubblicato nel design doc, non e'
    materiale nuovo) -> ASTIENITI: e' il falso positivo che la regola ingenua
    produrrebbe, ed e' il test del passo 5.

⚠️ SE le omissioni dessero 0 segnalazioni SOLO perche' i loro claim non
   contengono numeri, il test sarebbe VUOTO — non proverebbe niente sul passo
   5. Il banco lo dichiara invece di spacciarlo per una conferma.

⚠️ NON e' un banco sui VERI: la popolazione B e' di @ws5 e non la conosco. Qui
   ci sono solo i veri che erano gia' nei miei file pubblicati.

    python docs/stato-reale/banchi/ws3-F1-simulazione-del-predicato-fuori-dal-prodotto.py
"""

from __future__ import annotations

import re
import sys
import unicodedata

# ── estrazione, tutta deterministica ─────────────────────────────────────
_VAL = re.compile(
    r"(?P<num>\d[\d.]*)\s*(?P<uni>%|euro|eur|mg|ml|kg|giorni|mesi|anni|"
    r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|"
    r"ottobre|novembre|dicembre)",
    re.I,
)
_FRASE = re.compile(r"(?<=[.;!?])\s+")

# ⚠️ STOPWORD: lista MINIMA e DICHIARATAMENTE INCOMPLETA. E' la domanda ① del
# design doc, aperta e di @ws5: una stoplist monolingue in un prodotto mondiale
# e' la classe ③ dei nostri errori ricorrenti. Qui serve solo a far girare la
# simulazione, NON e' una proposta di lista.
_STOP = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da",
    "in", "con", "su", "per", "tra", "fra", "del", "dello", "della", "dei",
    "degli", "delle", "al", "allo", "alla", "ai", "agli", "alle", "dal",
    "dalla", "nel", "nella", "sul", "sulla", "e", "ed", "o", "che", "non",
    "e'", "essere", "sono", "art", "pari", "ogni", "come", "piu", "presente",
}


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _unita(u: str) -> str:
    u = _norm(u)
    if u in ("euro", "eur"):
        return "valuta"
    if u in ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
             "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"):
        return "data"
    return u


def _valori(t: str) -> set[tuple[str, str]]:
    return {(m.group("num"), _unita(m.group("uni"))) for m in _VAL.finditer(t)}


def _ancore(t: str) -> set[str]:
    puliti = _VAL.sub(" ", t)
    tok = re.findall(r"[a-zA-Zà-ùÀ-Ù']{3,}", puliti)
    return {_norm(x) for x in tok if _norm(x) not in _STOP}


def l43(claim: str, fonte: str) -> tuple[str, str]:
    """Ritorna (esito, motivo). Esiti: SEGNALA · OK · ASTIENITI · L4.1."""
    v_claim = _valori(claim)
    if not v_claim:
        return "ASTIENITI", "il claim non porta valori"
    v_fonte = _valori(fonte)
    frasi = [f for f in _FRASE.split(fonte) if f.strip()]
    A = _ancore(claim) & _ancore(fonte)

    for num, uni in sorted(v_claim):
        if (num, uni) not in v_fonte:                                  # passo 1
            return "L4.1", f"«{num} {uni}» non e' nella fonte: e' L4.1"
        if not A:                                                      # passo 2
            return "ASTIENITI", "nessuna ancora del claim esiste nella fonte"

        # ── passo 2-bis, TROVATO ESEGUENDO (28/08 ~20:10) ──────────────
        # La prima stesura accettava al passo 3 su UNA QUALSIASI ancora
        # condivisa, e sbagliava 6 scambi su 12. Il motivo, letto nei referti:
        # «penale per il ritardo ... 5%» condivide {penale, importo,
        # contrattuale} con la frase del 5% — ma quelle parole stanno in
        # ENTRAMBI gli articoli. Cio' che distingue e' «ritardo» contro
        # «difformita'», «consegna» contro «contestazione», il nome del farmaco
        # contro «prescritto».
        # 🔑 UN'ANCORA PRESENTE IN PIU' FRASI CANDIDATE NON IDENTIFICA NIENTE.
        #   Contano solo le ancore DISCRIMINANTI: quelle che compaiono in UNA
        #   SOLA delle frasi che portano un valore di quell'unita'.
        cand = [f for f in frasi if any(u == uni for _n, u in _valori(f))]
        occ: dict[str, int] = {}
        for f in cand:
            for a in _ancore(f):
                occ[a] = occ.get(a, 0) + 1
        A_disc = {a for a in A if occ.get(a, 0) == 1}
        if not A_disc:
            return ("ASTIENITI",
                    f"nessuna ancora DISCRIMINANTE in {uni}: le ancore del claim "
                    f"{sorted(A)} compaiono in piu' frasi candidate")

        # passo 3, EMENDATO due volte: ancore discriminanti + finestra non ambigua
        for f in frasi:
            if (num, uni) in _valori(f) and A_disc & _ancore(f):
                stessa_unita = [n for n, u in _valori(f) if u == uni]
                if len(set(stessa_unita)) >= 2:
                    break  # finestra ambigua: cade ai passi 4/5
                return "OK", (f"«{num} {uni}» sta in una frase con l'ancora "
                              f"discriminante {sorted(A_disc & _ancore(f))}")
        for f in frasi:                                                # passo 4
            if A_disc & _ancore(f):
                altri = [(n, u) for n, u in _valori(f) if u == uni and n != num]
                if altri:
                    return ("SEGNALA",
                            f"la fonte lega {sorted(A_disc & _ancore(f))} a "
                            f"«{altri[0][0]} {uni}», il claim dice «{num} {uni}»")
        return "ASTIENITI", f"la fonte tace sul valore in {uni} di {sorted(A_disc)}"
    return "ASTIENITI", "nessun valore da giudicare"


# ── i casi, tutti gia' pubblicati nei miei file ──────────────────────────
CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
REFERTO = (
    "Terapia in atto. Il paziente assume metformina 850 mg due volte al giorno. "
    "Il ramipril e' prescritto a 5 mg al mattino. "
    "L'acido acetilsalicilico e' prescritto a 100 mg alla sera. "
    "Controllo previsto a tre mesi."
)
OMI = ("L'affidamento al fornitore Bertani e' subordinato all'approvazione "
       "preventiva del collegio dei revisori.")

CASI = [
    ("SCAMBIO", CONTRATTO, "La penale per il ritardo e' pari al 5% dell'importo contrattuale.", "SEGNALA"),
    ("SCAMBIO", CONTRATTO, "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale.", "SEGNALA"),
    ("SCAMBIO", CONTRATTO, "Il termine di consegna e' fissato al 30 aprile 2027.", "SEGNALA"),
    ("SCAMBIO", CONTRATTO, "Il termine per la contestazione dei vizi e' fissato al 12 marzo 2027.", "SEGNALA"),
    ("SCAMBIO", CONTRATTO, "La cauzione definitiva e' pari a 148000 euro.", "SEGNALA"),
    ("SCAMBIO", CONTRATTO, "L'importo contrattuale e' di 22000 euro.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "Il ramipril e' prescritto a 850 mg al mattino.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "Il paziente assume metformina 5 mg due volte al giorno.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "L'acido acetilsalicilico e' prescritto a 850 mg alla sera.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "Il paziente assume metformina 100 mg due volte al giorno.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "Il ramipril e' prescritto a 100 mg al mattino.", "SEGNALA"),
    ("CIFRA",   CONTRATTO, "L'importo contrattuale e' di 391000 euro.", "L4.1"),
    ("CIFRA",   CONTRATTO, "La cauzione definitiva e' pari a 70000 euro.", "L4.1"),
    ("CIFRA",   REFERTO, "Il ramipril e' prescritto a 73 mg al mattino.", "L4.1"),
    ("PAROLE",  CONTRATTO, "L'importo contrattuale e' di trecentonovantunomila euro.", "ASTIENITI"),
    ("PAROLE",  REFERTO, "Il ramipril e' prescritto a settantatre mg al mattino.", "ASTIENITI"),
    ("OMISSIONE", OMI, "Il consiglio ha disposto l'affidamento al fornitore Bertani.", "ASTIENITI"),
    ("VERO",    CONTRATTO, "La penale per il ritardo e' pari al 2% dell'importo contrattuale.", "OK"),
    ("VERO",    REFERTO, "Il ramipril e' prescritto a 5 mg al mattino.", "OK"),
    ("VERO",    CONTRATTO, "L'importo contrattuale e' di 148000 euro.", "OK"),
    # il test del PASSO 5, gia' pubblicato nel design doc:
    ("VERO-p5", "Il paziente assume metformina. Il dosaggio e' 850 mg.",
     "Il paziente assume metformina 850 mg.", "ASTIENITI"),
]


def main() -> int:
    print("  ⚠️ SIMULAZIONE FUORI DAL PRODOTTO — nessun file di verimem/ toccato,")
    print("     nessun layer registrato. La modifica al prodotto resta bloccata")
    print("     dalla review doppia. Questo verifica solo se il ragionamento TORNA.\n")
    print(f"  {'famiglia':<10} {'atteso':<10} {'ottenuto':<10} claim")
    print("  " + "-" * 92)
    ok = 0
    for fam, fonte, claim, atteso in CASI:
        esito, motivo = l43(claim, fonte)
        buono = esito == atteso
        ok += buono
        print(f"  {fam:<10} {atteso:<10} {esito:<10} "
              f"{'✓' if buono else '✗'} {claim[:52]}")
        if not buono:
            print(f"  {'':<32} └─ {motivo[:78]}")

    print(f"\n  ══ IL RAGIONAMENTO TORNA SU {ok} CASI SU {len(CASI)} ══")
    seg = sum(1 for f, s, c, _a in CASI if f == "SCAMBIO" and l43(c, s)[0] == "SEGNALA")
    print(f"     SCAMBI segnalati: {seg} su 12   (la predizione del design doc"
          f" chiedeva >= 7 dei 10 che entrano)")
    fp = [(f, c) for f, s, c, _a in CASI if f.startswith("VERO")
          and l43(c, s)[0] == "SEGNALA"]
    print(f"     VERI segnalati per errore: {len(fp)}  "
          f"{'← nessun falso positivo sui veri che ho' if not fp else '← FALSI POSITIVI'}")
    for f, c in fp:
        print(f"        {f}: {c[:60]}")

    print("\n  ⚠️ LIMITI, e sono grossi:")
    print("     · e' una SIMULAZIONE del predicato, non il prodotto: il gate vero")
    print("       ha clausole, span troncati, normalizzazioni che qui non ci sono.")
    print("     · le OMISSIONI danno 0 segnalazioni anche solo perche' i loro")
    print("       claim NON CONTENGONO NUMERI ⇒ quel test e' VUOTO, non prova")
    print("       niente sul passo 5. L'unico test vero del passo 5 e' VERO-p5.")
    print("     · la lista di stopword e' MINIMA e DICHIARATAMENTE INCOMPLETA:")
    print("       e' la domanda ① del design doc, aperta, e di @ws5.")
    print("     · i VERI qui sono solo quelli gia' nei miei file: la popolazione B")
    print("       e' di @ws5 e NON la conosco. Questo banco non puo' approvare.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
