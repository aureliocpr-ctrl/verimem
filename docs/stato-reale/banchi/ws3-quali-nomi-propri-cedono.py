# -*- coding: utf-8 -*-
"""Dentro l'entita' sostituita, il NOME PROPRIO cede e l'attributo no. Quali nomi?

Misurato il 26/08 (`ws3-l-entita-a-batteria-l-ultima-delle-tre.py`)::

    forma          IT      EN
    attributo     0/5     0/5     perfetto
    nome proprio  1/5     2/5     cede

Cinque casi per forma bastavano a vedere la differenza, non a spiegarla. Questo
banco chiede QUALI nomi propri passano, con dodici casi su tre tipi::

    PERSONA        Anselmi -> Boveri, Dr Merli -> Dr Fabbri
    LUOGO          Mestre -> Treviso, Rovigo -> Padova
    ORGANIZZAZIONE Baldini -> Corsini (fornitori), Postgres -> MySQL (prodotti)

Perche' i tipi: il ramo `_proper` di `_entita_diverse` (59fb0862, mio) tratta i
nomi propri come classe unica, ma un cognome, un toponimo e un nome di prodotto
hanno frequenze e forme diversissime nel vocabolario di un modello. Se cede un
tipo solo, la cura e' diversa da quella che serve se cedono tutti.

⚖️ Ogni caso porta il suo VERO. ⛔ Nessun numero cambia fra fonte e claim: la
sostituzione e' SOLO il nome, altrimenti misurerei L4.1.
🔑 IT/EN appaiati sulla stessa fonte.
📌 Il layer viene stampato per ogni riga: sui casi che si FERMANO dice chi li ha
fermati, ed e' l'informazione che serve per sapere se il merito e' del ramo
`_proper` o del giudice.

MISURATO 26/08::

    falsita' ammesse  IT  persona 0/4 · luogo 0/4 · organizzaz 1/4   -> 1/12
    falsita' ammesse  EN  persona 0/4 · luogo 1/4 · organizzaz 1/4   -> 2/12
    VERI rifiutati    IT 2/12   EN 1/12

    CHI HA FERMATO i 21 casi fermati:
      L3-coexistence + L4-grounding            15
      L1.16 + L4-grounding                      3
      L4-grounding                              2
      L1 + L1.16 + L3-coexistence + L4-grounding 1

① IL TASSO E' CONFERMATO su una popolazione piu' larga: 1/12 e 2/12 contro 1/5
e 2/5 del banco precedente. La forma «nome proprio» sbaglia intorno al 10%
mentre la forma «attributo» era 0/5 e 0/5.
② I TIPI NON SONO EQUIVALENTI. Il tipo debole e' ORGANIZZAZIONE/PRODOTTO —
cede in entrambe le lingue (Ferraris->Malaspina, Kubernetes->Docker Swarm). Il
tipo PERSONA regge sempre, 0/4 e 0/4. Il LUOGO cede solo in EN.
⚠️ Quattro casi per cella: e' un segnale, non una tesi. Serve per sapere DOVE
guardare, non per dichiarare un tasso per tipo.
🔑 ③ NON E' IL RAMO `_proper` DA SOLO, ed e' la risposta che cercavo: i casi che
si fermano sono fermati da `L3-coexistence` INSIEME a `L4-grounding` in 15 casi
su 21. `L3-coexistence` passa da `_entita_diverse` (e quindi dal ramo), ma da
solo non compare mai: il merito e' condiviso col giudice. Chi volesse curare il
ramo deve sapere che nei casi riusciti non agisce da solo.
④ E IL GATE SBAGLIA IN ENTRAMBE LE DIREZIONI su questa forma: 3 falsita'
ammesse su 24 e 3 VERI rifiutati su 24 (`L1.16` compare in 4 dei fermati). ⇒ I
nomi propri sono la zona piu' RUMOROSA della matrice, non solo la piu' debole:
un intervento che alzasse la severita' peggiorerebbe i veri.

Regime: porta pubblica `verimem remember --source`, store temporaneo, FUORI
pytest.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_nomi_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (tipo, fonte_IT, vero_IT, falso_IT, fonte_EN, vero_EN, falso_EN)
CASI = [
    ("persona",
     "Atto: il magazzino di Rovigo e' stato venduto al signor Anselmi.",
     "Il magazzino di Rovigo e' stato venduto al signor Anselmi.",
     "Il magazzino di Rovigo e' stato venduto al signor Boveri.",
     "Deed: the Rovigo warehouse was sold to Mr Anselmi.",
     "The Rovigo warehouse was sold to Mr Anselmi.",
     "The Rovigo warehouse was sold to Mr Boveri."),
    ("persona",
     "Verbale: la relazione e' stata presentata dalla dottoressa Merli.",
     "La relazione e' stata presentata dalla dottoressa Merli.",
     "La relazione e' stata presentata dalla dottoressa Fabbri.",
     "Minutes: the report was presented by Dr Merli.",
     "The report was presented by Dr Merli.",
     "The report was presented by Dr Fabbri."),
    ("persona",
     "Nota: la pratica e' stata istruita dall'ingegner Salviati.",
     "La pratica e' stata istruita dall'ingegner Salviati.",
     "La pratica e' stata istruita dall'ingegner Torricelli.",
     "Note: the file was prepared by engineer Salviati.",
     "The file was prepared by engineer Salviati.",
     "The file was prepared by engineer Torricelli."),
    ("persona",
     "Registro: il collaudo e' stato firmato dal geometra Pacini.",
     "Il collaudo e' stato firmato dal geometra Pacini.",
     "Il collaudo e' stato firmato dal geometra Renzi.",
     "Registry: the inspection was signed off by surveyor Pacini.",
     "The inspection was signed off by surveyor Pacini.",
     "The inspection was signed off by surveyor Renzi."),
    ("luogo",
     "Rapporto: il cantiere di Mestre e' stato consegnato a novembre.",
     "Il cantiere di Mestre e' stato consegnato a novembre.",
     "Il cantiere di Treviso e' stato consegnato a novembre.",
     "Report: the Mestre site was handed over in November.",
     "The Mestre site was handed over in November.",
     "The Treviso site was handed over in November."),
    ("luogo",
     "Nota: la merce e' partita dal deposito di Rovigo il 3 marzo.",
     "La merce e' partita dal deposito di Rovigo il 3 marzo.",
     "La merce e' partita dal deposito di Padova il 3 marzo.",
     "Note: the goods left the Rovigo depot on 3 March.",
     "The goods left the Rovigo depot on 3 March.",
     "The goods left the Padova depot on 3 March."),
    ("luogo",
     "Verbale: la riunione si e' tenuta nella sede di Bologna.",
     "La riunione si e' tenuta nella sede di Bologna.",
     "La riunione si e' tenuta nella sede di Firenze.",
     "Minutes: the meeting was held at the Bologna office.",
     "The meeting was held at the Bologna office.",
     "The meeting was held at the Firenze office."),
    ("luogo",
     "Referto: il paziente e' stato trasferito all'ospedale di Verona.",
     "Il paziente e' stato trasferito all'ospedale di Verona.",
     "Il paziente e' stato trasferito all'ospedale di Vicenza.",
     "Report: the patient was transferred to the Verona hospital.",
     "The patient was transferred to the Verona hospital.",
     "The patient was transferred to the Vicenza hospital."),
    ("organizzaz",
     "Comunicazione: il fornitore Baldini ha consegnato il lotto il 9 giugno.",
     "Il fornitore Baldini ha consegnato il lotto il 9 giugno.",
     "Il fornitore Corsini ha consegnato il lotto il 9 giugno.",
     "Notice: supplier Baldini delivered the batch on 9 June.",
     "Supplier Baldini delivered the batch on 9 June.",
     "Supplier Corsini delivered the batch on 9 June."),
    ("organizzaz",
     "Nota: la migrazione a Postgres e' stata approvata il 9 giugno.",
     "La migrazione a Postgres e' stata approvata il 9 giugno.",
     "La migrazione a MySQL e' stata approvata il 9 giugno.",
     "Note: the migration to Postgres was approved on 9 June.",
     "The migration to Postgres was approved on 9 June.",
     "The migration to MySQL was approved on 9 June."),
    ("organizzaz",
     "Verbale: il contratto e' stato aggiudicato alla ditta Ferraris.",
     "Il contratto e' stato aggiudicato alla ditta Ferraris.",
     "Il contratto e' stato aggiudicato alla ditta Malaspina.",
     "Minutes: the contract was awarded to Ferraris.",
     "The contract was awarded to Ferraris.",
     "The contract was awarded to Malaspina."),
    ("organizzaz",
     "Nota tecnica: il servizio e' stato spostato su Kubernetes a settembre.",
     "Il servizio e' stato spostato su Kubernetes a settembre.",
     "Il servizio e' stato spostato su Docker Swarm a settembre.",
     "Technical note: the service was moved to Kubernetes in September.",
     "The service was moved to Kubernetes in September.",
     "The service was moved to Docker Swarm in September."),
]

_L = re.compile(r"\b(L1(?:\.\d+)?|L3[\w-]*|L4(?:\.\d+)?[\w-]*|store-screen)\b")


def esegui(claim: str, source: str):
    buf = io.StringIO()
    sys.argv = ["verimem", "remember", claim, "--source", source]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            main()
    except SystemExit:
        pass
    except Exception as e:                                    # noqa: BLE001
        return "ECCEZIONE", None, type(e).__name__
    o = buf.getvalue()
    esito = ("admitted" if re.search(r"\badmitted\b", o)
             else "quarantined" if re.search(r"\bquarantined\b", o) else "?")
    m = re.search(r"grounding ([\d.]+)", o)
    return esito, (float(m.group(1)) if m else None), (
        "+".join(sorted(set(_L.findall(o)))) or "-")


def main_banco() -> None:
    print("%-11s %-3s %-6s %-12s %7s  %s"
          % ("tipo", "lg", "caso", "esito", "g", "layer"))
    amm = {}
    tot = {}
    veri_rif = {"IT": 0, "EN": 0}
    fermati_da = {}
    for (tipo, s_it, v_it, f_it, s_en, v_en, f_en) in CASI:
        for lg, src, vero, falso in (("IT", s_it, v_it, f_it),
                                     ("EN", s_en, v_en, f_en)):
            e_v, g_v, l_v = esegui(vero, src)
            if e_v != "admitted":
                veri_rif[lg] += 1
            e_f, g_f, l_f = esegui(falso, src)
            k = (lg, tipo)
            tot[k] = tot.get(k, 0) + 1
            if e_f != "quarantined":
                amm[k] = amm.get(k, 0) + 1
            else:
                fermati_da[l_f] = fermati_da.get(l_f, 0) + 1
            print("%-11s %-3s %-6s %-12s %7s  %-22s %s"
                  % (tipo, lg, "VERO", e_v,
                     ("%.1f" % g_v) if g_v is not None else "-", l_v,
                     "" if e_v == "admitted" else "<<< VERO RIFIUTATO"))
            print("%-11s %-3s %-6s %-12s %7s  %-22s %s"
                  % ("", lg, "falso", e_f,
                     ("%.1f" % g_f) if g_f is not None else "-", l_f,
                     "" if e_f == "quarantined" else "<<< AMMESSA"))
        print()
    print("=" * 84)
    for lg in ("IT", "EN"):
        for tipo in ("persona", "luogo", "organizzaz"):
            k = (lg, tipo)
            print("  falsita' ammesse  %s  %-11s %d/%d"
                  % (lg, tipo, amm.get(k, 0), tot.get(k, 0)))
    it = sum(v for (lg, _), v in amm.items() if lg == "IT")
    en = sum(v for (lg, _), v in amm.items() if lg == "EN")
    print()
    print("  TOTALE ammesse   IT %d/%d   EN %d/%d"
          % (it, len(CASI), en, len(CASI)))
    print("  VERI rifiutati   IT %d/%d   EN %d/%d"
          % (veri_rif["IT"], len(CASI), veri_rif["EN"], len(CASI)))
    print()
    print("  CHI HA FERMATO i casi che si fermano:")
    for lay, n in sorted(fermati_da.items(), key=lambda x: -x[1]):
        print("    %-28s %d" % (lay, n))


if __name__ == "__main__":
    main_banco()
