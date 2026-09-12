"""T50 — il verdetto di fiducia chiama ``trusted`` un fatto che il gate ha FERMATO.

Ticket T50 (mappa dell'intera superficie, 09/09): ``compute_trust_signal``
conosce DUE status su sette. Gli altri cinque cadono nel ramo di default
(``verimem/trust_signal.py:154-161``) e tornano ``trusted``, fra cui
``quarantined`` — cioe' esattamente il fatto che l'anti-confab gate ha
fermato in scrittura.

Cosa cambia per l'utente: la parola «trusted» torna a voler dire trusted.
Un fatto fermato dal moat non viene piu' chiamato affidabile.

CLAIM DEL README PRESIDIATI DA QUESTO BANCO
-------------------------------------------
* ``README.md:443-444`` — «stored but OUT of default recall — your agent
  will never repeat it as truth». La seconda meta' della frase e' quella
  che questo banco misura: un verdetto ``trusted`` su un quarantenato E'
  ripeterlo come verita', a chiunque chieda il verdetto.
  Presidio: ``test_un_fatto_fermato_dal_gate_non_si_chiama_trusted``.
  La prima meta' (fuori dal recall di default) e' presidiata da
  ``test_un_quarantenato_non_esce_dal_recall_di_default``.
* ``README.md:462-463`` — «the gate's outcome + provenance are the trust
  signal, not a self-asserted badge». Prima di T50 l'esito del gate NON
  entrava nel trust signal per cinque status su sette.
  Presidio: ``test_ogni_status_riceve_un_verdetto_sensato``.

I DUE LIVELLI, tenuti separati di proposito
-------------------------------------------
* **Livello 1 — la funzione pubblica**: la tabella dei sette status di
  ``_VALID_STATUSES`` (``verimem/semantic.py:566``) contro il verdetto.
  E' il livello a cui il difetto vive.
* **Livello 2 — la porta**: ``recall(trust_signals=True)`` e' l'unico
  punto che attacca il verdetto (``semantic.py:3930``), e da li' arriva
  al tool MCP e a ``hallucination_rate_at_k``. Qui il banco misura anche
  quanto il difetto e' SERVITO, non solo quanto esiste: il recall di
  default nasconde i tre status a rango negativo, e questo ABBASSA la
  gravita' del ticket. E' misurato e scritto perche' abbassarla e' un
  risultato quanto alzarla.

Ogni prova alla porta parte da un CONTROLLO POSITIVO: sotto pytest
l'embedder e' lo stub (``tests/conftest.py:147``), e un recall vuoto si
legge come «nessun fatto sospetto», cioe' come un verde. Se il controllo
positivo non si accende, il banco e' cieco e il test lo dice.

Eseguito il 09/09 su nadia/t50-t53 (base 20257636) con
``env -u HIPPO_ENCODE_DELEGATE_ONLY``.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from verimem.semantic import _VALID_STATUSES, Fact, SemanticMemory
from verimem.trust_signal import compute_trust_signal


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sm.db")


# `provisional` non sopravvive a `store()` senza un ref che passi la whitelist
# URL/arxiv: il gate lo declassa a `model_claim` (`semantic.py:3125`, misurato
# il 09/09). Senza questo ref il banco misurerebbe un `model_claim` credendo di
# misurare un `provisional` — il sensore scollegato, non il difetto.
_REF_WHITELISTED = ["https://arxiv.org/abs/2401.00001"]


def _fatto(
    status: str, *, now: float, fid: str | None = None,
) -> Fact:
    """Un fatto SANO sotto ogni altro aspetto: giovane, non superseduto,
    confidenza alta. Cosi' l'unica variabile che decide il verdetto e'
    lo status — una variabile per volta, o il confronto mente.
    """
    return Fact(
        id=fid or f"f-{status}",
        proposition=f"il capannone 12 misura 900 metri quadri ({status})",
        topic="magazzino",
        confidence=0.9,
        status=status,
        created_at=now,
        verified_by=list(_REF_WHITELISTED) if status == "provisional" else [],
    )


# Il verdetto che ogni status DEVE poter ricevere. Non fissa il nome esatto
# della cura (che puo' introdurre un verdetto nuovo, es. `rejected`): fissa
# la sostanza, cioe' che un fatto fermato o scartato non sia «trusted».
_VERDETTI_AMMESSI: dict[str, set[str]] = {
    "verified": {"trusted"},
    "model_claim": {"trusted"},
    "legacy_unverified": {"unverified"},
    # I quattro del ticket: oggi cadono tutti nel default.
    "provisional": {"unverified", "provisional", "rejected"},
    "orphaned": {"rejected", "unverified"},
    "quarantined": {"rejected", "unverified"},
    "user_belief": {"rejected", "unverified"},
}


class TestLaTabellaDeiSetteStatus:
    """Livello 1 — la funzione pubblica, sui sette status che esistono."""

    def test_la_tabella_del_banco_copre_ogni_status_del_prodotto(self) -> None:
        """Controllo positivo del BANCO, non del prodotto: se domani il
        prodotto aggiunge un ottavo status, questo test cade e la tabella
        qui sopra va aggiornata. Un banco che non sa di essere incompleto
        e' il modo piu' comune di leggere un buco come un verde.
        """
        assert set(_VERDETTI_AMMESSI) == set(_VALID_STATUSES), (
            "la tabella del banco e la lista _VALID_STATUSES del prodotto "
            "sono divergenti"
        )

    @pytest.mark.parametrize("status", sorted(_VERDETTI_AMMESSI))
    def test_ogni_status_riceve_un_verdetto_sensato(
        self, sm: SemanticMemory, status: str,
    ) -> None:
        now = time.time()
        f = _fatto(status, now=now)

        # LIVELLO DICHIARATO: la funzione pura, senza passare da `store()`.
        # E' il livello giusto per questo ticket per un motivo misurato, non
        # per comodita': `store()` DECLASSA due dei sette status quando i ref
        # non superano la verifica (`semantic.py:3114` e `:3125`), quindi
        # scrivendo non si riesce nemmeno a costruire il caso `verified`.
        # Il prodotto dichiara la funzione pura (trust_signal.py:22-24) e
        # promette un verdetto per lo status che riceve: e' quella promessa
        # che questo test misura. Cosa il prodotto sappia SCRIVERE lo misura
        # `test_quali_status_sopravvivono_alla_scrittura`, qui sotto.
        sig = compute_trust_signal(f, sm, now=now)

        assert sig.verdict in _VERDETTI_AMMESSI[status], (
            f"status={status!r} -> verdetto={sig.verdict!r} "
            f"(details={sig.details!r}); ammessi: "
            f"{sorted(_VERDETTI_AMMESSI[status])}"
        )

    def test_un_fatto_fermato_dal_gate_non_si_chiama_trusted(
        self, sm: SemanticMemory,
    ) -> None:
        """La riga che dice il ticket in una frase sola, senza tabelle.

        `quarantined` = «l'anti-confab gate l'ha flaggato AL MOMENTO
        DELLA SCRITTURA» (commento del prodotto, semantic.py:560-566).
        Chiamarlo `trusted` e' la promessa pubblica rovesciata:
        «kept OUT of default recall».
        """
        now = time.time()
        f = _fatto("quarantined", now=now)
        sm.store(f)

        sig = compute_trust_signal(f, sm, now=now)

        assert sig.verdict != "trusted", (
            "un fatto QUARANTENATO dal moat torna con verdetto "
            f"{sig.verdict!r} — details={sig.details!r}"
        )

    def test_quali_status_sopravvivono_alla_scrittura(
        self, sm: SemanticMemory,
    ) -> None:
        """Il dato che RIDIMENSIONA il ticket, misurato il 09/09 e scritto
        qui perche' resti misurato.

        Dei sette status, DUE non si possono nemmeno scrivere senza ref che
        superino una verifica: `verified` (hard-gate v2, `semantic.py:3114`)
        e `provisional` (whitelist URL/arxiv, `semantic.py:3125`) vengono
        declassati a `model_claim`. E `store()` MUTA L'OGGETTO IN PLACE:
        chi passa un Fact se lo ritrova cambiato sotto le mani.

        Conseguenza per T50: la riga `provisional` del ticket e' reale solo
        per i fatti che portano un ref buono; la riga `verified` non era nel
        ticket e infatti non e' un difetto. Le tre righe che restano intere
        — `quarantined`, `orphaned`, `user_belief` — sono anche le tre che
        la scrittura conserva tali e quali.
        """
        now = time.time()
        atteso = {
            "verified": "model_claim",       # declassato: nessun ref verificato
            "provisional": "model_claim",    # declassato: nessun ref whitelisted
            "model_claim": "model_claim",
            "legacy_unverified": "legacy_unverified",
            "orphaned": "orphaned",
            "quarantined": "quarantined",
            "user_belief": "user_belief",
        }
        assert set(atteso) == set(_VALID_STATUSES)

        visto: dict[str, str | None] = {}
        for st in sorted(atteso):
            f = Fact(
                id=f"w-{st}", proposition=f"il capannone 12 e' {st}",
                topic="magazzino", confidence=0.9, status=st,
                created_at=now, verified_by=[],
            )
            sm.store(f)
            letto = sm.get(f"w-{st}")
            visto[st] = getattr(letto, "status", None)

        assert visto == atteso, (
            "la scrittura non conserva piu' gli status come il 09/09: "
            f"visto={visto}"
        )

    def test_i_segnali_piu_forti_restano_intatti(
        self, sm: SemanticMemory,
    ) -> None:
        """Controllo che deve RIMANERE verde dopo la cura: la priorita'
        dei segnali (obsolete > contested > stale > status) non cambia.
        Un banco che vede solo il difetto non accorge la regressione.
        """
        now = time.time()
        vecchio = _fatto("quarantined", now=now - 200 * 86400, fid="f-vecchio")
        sm.store(vecchio)
        sig = compute_trust_signal(vecchio, sm, now=now)
        assert sig.verdict == "stale", (
            "l'eta' deve continuare a vincere sullo status: "
            f"verdetto={sig.verdict!r}"
        )
        assert sig.age_days >= 180.0


class TestAllaPortaDelRecall:
    """Livello 2 — quanto il difetto e' SERVITO, non solo quanto esiste."""

    def test_il_controllo_positivo_si_accende(
        self, sm: SemanticMemory,
    ) -> None:
        """Prima di dire «il recall non rende i quarantenati» bisogna
        provare che il recall rende QUALCOSA con questa query e questo
        embedder. Un'interrogazione vuota si prova su un caso che DEVE
        rispondere, altrimenti il verde e' cecita'.
        """
        now = time.time()
        sm.store(_fatto("model_claim", now=now, fid="f-sano"))

        hits = sm.recall("capannone 12 metri quadri", k=5)

        assert hits, (
            "CONTROLLO POSITIVO SPENTO: nemmeno un fatto model_claim esce "
            "dal recall con questa query — sotto pytest l'embedder e' lo "
            "stub e il banco alla porta e' CIECO: il risultato di "
            "test_un_quarantenato_non_esce_dal_recall non vale."
        )

    def test_un_quarantenato_non_esce_dal_recall_di_default(
        self, sm: SemanticMemory,
    ) -> None:
        """Il dato che ABBASSA la gravita' di questo ticket, e proprio
        per questo va misurato: se il recall di default non serve i
        quarantenati, il difetto di T50 e' latente su questa porta.
        Le porte che LI SERVONO sono quelle di T49 (owner ws2 Giano).
        """
        now = time.time()
        sm.store(_fatto("model_claim", now=now, fid="f-sano"))
        sm.store(_fatto("quarantined", now=now, fid="f-fermato"))

        hits = sm.recall("capannone 12 metri quadri", k=10)
        ids = {h[0].id for h in hits}

        assert "f-sano" in ids, (
            "CONTROLLO POSITIVO SPENTO: il fatto sano non esce, il "
            "confronto non vale"
        )
        assert "f-fermato" not in ids, (
            "il recall di DEFAULT ha servito un fatto quarantenato: "
            f"ids={sorted(ids)}"
        )

    def test_se_una_porta_lo_serve_il_verdetto_non_dice_trusted(
        self, sm: SemanticMemory,
    ) -> None:
        """La via per cui il difetto arriva davvero all'utente: un
        chiamante che riapre la porta ai rank negativi (o una delle sette
        porte di T49) e chiede anche il verdetto. Qui il quarantenato
        esce E si presenta come affidabile.
        """
        now = time.time()
        sm.store(_fatto("model_claim", now=now, fid="f-sano"))
        sm.store(_fatto("quarantined", now=now, fid="f-fermato"))

        hits = sm.recall(
            "capannone 12 metri quadri", k=10,
            min_status="orphaned", trust_signals=True,
        )
        per_id = {h[0].id: h for h in hits}

        assert "f-sano" in per_id, (
            "CONTROLLO POSITIVO SPENTO: il fatto sano non esce nemmeno "
            "con min_status='orphaned', il confronto non vale"
        )
        if "f-fermato" not in per_id:
            pytest.skip(
                "min_status='orphaned' non riapre la porta ai quarantenati "
                "su questo percorso: la prova va rifatta dalla porta di T49"
            )
        _, _, sig = per_id["f-fermato"]
        assert sig.verdict != "trusted", (
            "un fatto quarantenato e' stato servito CON verdetto "
            f"{sig.verdict!r} — details={sig.details!r}"
        )
