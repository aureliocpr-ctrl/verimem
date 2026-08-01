"""«di» e «il» non sono un argomento in comune.

Reperto dell'altra istanza (in sola lettura), 2026-08-01, riprodotto sul corpus
vero: alla domanda «quale versione di Kubernetes usa il cluster OnlyPaws» il
tool `hippo_oracle_query` risponde con `n_results: 6` e cita::

    «il colore preferito di Aurelio e' il blu»
    «Il numero magico segreto di Aurelio è 7777»
    «l'animale preferito di Aurelio e' il gatto»

LA CAUSA, misurata e senza margini di interpretazione::

    token query: ['cluster','di','il','kubernetes','onlypaws','quale','usa','versione']
    token fatto: ['aurelio','blu','colore','di','e','il','preferito']
    comuni     : ['di', 'il']
    jaccard    : 0.1538   >=  min_sim 0.1

Le uniche parole in comune sono **due preposizioni**, e bastano a superare la
soglia. `_tokens` non filtra le parole vuote, quindi la similarita' fra una
domanda su Kubernetes e il colore preferito di qualcuno viene dai connettivi
della lingua.

E' la TERZA volta in due giorni che un tool restituisce tutto perche' il suo
criterio non distingue: i documenti che citavano la ricetta della carbonara
(curato contando `query_terms_matched`), il dossier che rispondeva a ogni
domanda (curato accendendo `ce_gate`), e adesso l'oracolo.

LA CURA NON TOCCA LA SOGLIA. Alzare `min_sim` sarebbe un numero scelto a occhio
— l'errore gia' pagato tre volte questa settimana. Si toglie dal conto cio' che
non porta informazione: le parole vuote. Con quelle fuori, «di» e «il» non
contano piu' e la similarita' torna a misurare l'argomento.

E la lista NON si riscrive: `document_index._PAROLE_VUOTE` esiste gia', ha 94
voci, contiene «di» e «il», ed e' stata scritta per lo stesso identico motivo su
un altro tool. Due copie divergono — e questo repo ha gia' pagato quella lezione
tre volte in una settimana.
"""
from __future__ import annotations

from verimem.oracle import _jaccard, _tokens, oracle_query


class _Fatto:
    def __init__(self, fid, prop):
        self.id, self.proposition = fid, prop
        self.topic, self.confidence = "t", 0.9


def test_due_preposizioni_non_fanno_un_argomento_in_comune():
    """Il caso misurato, ridotto all'osso."""
    q = _tokens("quale versione di Kubernetes usa il cluster OnlyPaws")
    f = _tokens("il colore preferito di Aurelio e' il blu")
    assert _jaccard(q, f) < 0.1, (
        f"la similarita' fra una domanda su Kubernetes e il colore preferito "
        f"di qualcuno e' {_jaccard(q, f):.4f}, sopra la soglia 0.1, e viene "
        f"dalle parole in comune {sorted(q & f)}")


def test_l_oracolo_non_cita_fatti_che_non_c_entrano():
    """Lo stesso, attraverso il tool."""
    fatti = [
        _Fatto("f1", "il colore preferito di Aurelio e' il blu"),
        _Fatto("f2", "Il numero magico segreto di Aurelio e' 7777"),
        _Fatto("f3", "l'animale preferito di Aurelio e' il gatto"),
    ]
    out = oracle_query(query="quale versione di Kubernetes usa il cluster",
                       episodes=[], facts=fatti, skills=[])
    assert out["n_results"] == 0, (
        f"l'oracolo ha citato {out['n_results']} fatti che non parlano di "
        f"Kubernetes: {[f.get('proposition', '')[:40] for f in out['facts']]}")


def test_l_oracolo_RISPONDE_quando_l_argomento_c_e_davvero():
    """Controprova: un oracolo che tace sempre passerebbe i due test sopra ed
    e' inutile. La cura toglie le parole vuote, non l'argomento."""
    fatti = [
        _Fatto("f1", "il colore preferito di Aurelio e' il blu"),
        _Fatto("f2", "Il cluster di produzione usa Kubernetes versione 1.29"),
    ]
    out = oracle_query(query="quale versione di Kubernetes usa il cluster",
                       episodes=[], facts=fatti, skills=[])
    assert out["n_results"] >= 1, (
        f"l'oracolo non trova un fatto che nomina Kubernetes, il cluster e la "
        f"versione: la cura ha tolto anche l'argomento. {out}")
    citati = " ".join(f.get("proposition", "") for f in out["facts"]).lower()
    assert "kubernetes" in citati, citati
    assert "colore" not in citati, (
        f"insieme a quello giusto e' tornato anche il colore preferito: "
        f"{citati}")
