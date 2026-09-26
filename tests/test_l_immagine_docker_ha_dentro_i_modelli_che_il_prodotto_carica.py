"""README:618 — Docker «embedding models **baked in** — runs fully offline».

IL CLAIM, testuale dal README pubblicato:

    Docker (embedding models baked in — runs fully offline):

    ```bash
    docker compose -f docker-compose.gateway.yml up -d --build
    ```

Sono DUE promesse:
  ① **baked in** — i modelli stanno DENTRO l'immagine, scaricati a build time;
  ② **runs fully offline** — all'avvio non c'e' nessun giro all'HF Hub.

E' VERO, verificato il 10/09: il `Dockerfile` fa il pre-fetch a build time
(`RUN python -c "…SentenceTransformer…"`) e fissa `HF_HOME`, e il suo commento
spiega anche perche' due modelli e non uno.

LA ② HA GIA' UN PRESIDIO, ED E' BUONO: `tests/test_airgap_no_egress.py` prova
EMPIRICAMENTE che un encode reale in modalita' offline non apre nessuna
connessione non locale.

⚠️ MISURATO, non supposto: in questo ambiente quel file e' **rosso comunque**
(`EXIT=1`), per `EncodeDelegateUnavailable: encode daemon unavailable and
in-process cold-load is disabled (HIPPO_ENCODE_DELEGATE_ONLY=1)` — l'incidente
del daemon, non un difetto suo. Quindi **non posso dire se sarebbe cieco al
difetto che questo file sorveglia**: e' gia' rosso per altro, e un rosso che
c'era gia' non si attribuisce al proprio difetto. Lo scrivo cosi' invece di
dargli un verdetto che non ho.

LA ① NON HA NESSUN PRESIDIO, ed e' quella che questo file tiene ferma. E copre
un caso che la ② non puo' coprire per costruzione: la ② parte dal modello che
trova in cache, la ① chiede se quel modello e' QUELLO CHE IL PRODOTTO CARICA.

IL DIFETTO CHE SORVEGLIA, e non e' teorico. I modelli sono **due stringhe
scritte in due file diversi** senza nessun legame meccanico:

    Dockerfile      S('intfloat/multilingual-e5-base')
                    S('sentence-transformers/all-MiniLM-L6-v2')
    config.py:74    _DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
    config.py:66    _LEGACY_EMBEDDING_MODEL  = "sentence-transformers/all-MiniLM-L6-v2"

Oggi combaciano. Il giorno che `config.py` cambia il default e il Dockerfile
resta indietro, l'immagine ha in cache un modello e ne carica un altro: **scarica
all'avvio**, e in un ambiente air-gapped — l'unico posto dove «fully offline» e'
una promessa che conta — non parte affatto. Il README continuerebbe a prometterlo.

🔑 E' LA CLASSE CHE ABBIAMO GIA' PAGATO IERI NOTTE: il daemon rinato con il
modello a 384 invece di 768, 14 fatti entrati senza vettore, in silenzio. Stessa
forma — *un modello diverso da quello atteso, e nessuno che se ne accorga* —
qui nella variante dell'immagine pubblicata.

Costo: due `open()`. Nessuna esecuzione, nessun Docker, nessun modello.

ws7 «Iris», 10/09/2026. Misurato con:
`python -m pytest tests/test_l_immagine_docker_ha_dentro_i_modelli_che_il_prodotto_carica.py -q -p no:randomly`
"""
from __future__ import annotations

import pathlib

import pytest

from verimem import config as _config

RADICE = pathlib.Path(__file__).resolve().parents[1]
DOCKERFILE = RADICE / "Dockerfile"


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _modelli_del_prodotto() -> dict[str, str]:
    """I nomi che il PRODOTTO dichiara, letti da lui e non ricopiati qui.

    ⚠️ Se li riscrivessi come costanti in questo file, il test confronterebbe la
    mia copia con il Dockerfile e resterebbe verde anche quando il prodotto
    cambia: sarebbe un presidio che sorveglia se stesso.
    """
    return {
        "default": getattr(_config, "_DEFAULT_EMBEDDING_MODEL", ""),
        "legacy": getattr(_config, "_LEGACY_EMBEDDING_MODEL", ""),
    }


# ── I CONTROLLI POSITIVI PER PRIMI ──────────────────────────────────────────


def test_CONTROLLO_il_dockerfile_esiste_ed_e_stato_LETTO():
    """Un file mancante o vuoto renderebbe ogni asserzione sotto senza oggetto."""
    assert DOCKERFILE.is_file(), f"{DOCKERFILE} non esiste"
    testo = _dockerfile()
    assert len(testo) > 500, f"il Dockerfile ha solo {len(testo)} caratteri"
    assert "SentenceTransformer" in testo, (
        "nel Dockerfile non c'e' piu' nessun pre-fetch di SentenceTransformer: "
        "il README:618 promette «embedding models baked in», e senza quel passo "
        "l'immagine li scarica al primo encode. Se il pre-fetch e' stato spostato "
        "altrove (uno script, un layer separato), aggiorna QUESTO test insieme."
    )


def test_CONTROLLO_il_prodotto_dichiara_ancora_i_suoi_due_modelli():
    """Se le costanti sparissero, il confronto sotto sarebbe fra due stringhe vuote."""
    modelli = _modelli_del_prodotto()
    for ruolo, nome in modelli.items():
        assert nome, (
            f"`verimem.config` non dichiara piu' il modello «{ruolo}»: questo test "
            "confronterebbe il Dockerfile con una stringa vuota, e passerebbe."
        )
        assert "/" in nome, f"«{nome}» non sembra un id di modello HF"


# ── LA PROMESSA ①: I MODELLI SONO DENTRO L'IMMAGINE ─────────────────────────


@pytest.mark.parametrize("ruolo", ["default", "legacy"])
def test_il_modello_che_il_prodotto_carica_e_pre_scaricato_nell_immagine(ruolo):
    """README:618 — «baked in»: il Dockerfile mette in cache CIO' CHE SI CARICA.

    Non basta che il Dockerfile scarichi «un» modello: deve scaricare QUELLO che
    il prodotto poi apre. Due stringhe in due file divergono, e quando divergono
    l'immagine ha in cache un modello e ne carica un altro — cioe' scarica
    all'avvio, cioe' NON e' piu' offline.
    """
    nome = _modelli_del_prodotto()[ruolo]
    assert nome in _dockerfile(), (
        f"il modello «{ruolo}» che il prodotto carica e' `{nome}`, e il Dockerfile "
        "non lo pre-scarica. L'immagine lo prenderebbe dall'HF Hub al primo "
        "encode: in un ambiente air-gapped non parte, e README:618 promette "
        "«embedding models baked in — runs fully offline».\n"
        "Cura: aggiungere `S('" + nome + "')` al RUN di pre-fetch, nello stesso "
        "commit che ha cambiato il default."
    )


# ── E IL CONTROLLO CHE PUO' SMENTIRMI ───────────────────────────────────────


def test_CONTROLLO_un_modello_INVENTATO_non_risulta_pre_scaricato():
    """Se questo passasse, «il nome e' nel Dockerfile» sarebbe vero per chiunque.

    Senza questa faccia, un `in` su un testo di qualche migliaio di caratteri
    sembra un controllo e potrebbe non esserlo: qui si pretende che il righello
    sappia dire anche di NO.
    """
    assert "intfloat/questo-modello-non-esiste-davvero" not in _dockerfile()

# FALSIFICATO. Difetto simulato per un minuto a `config.py:74`
# (_DEFAULT_EMBEDDING_MODEL -> "intfloat/multilingual-e5-large", che il
# Dockerfile non pre-scarica):
#
#     EXIT=1  1 failed, 4 passed
#     «il modello «default» che il prodotto carica e' `intfloat/multilingual-e5-large`,
#      e il Dockerfile non lo pre-scarica»
#
# Senza il difetto: EXIT=0, 5 passed. `config.py` ripristinato con
# `git checkout --` e verificato identico al backup.
#
# ⚠️ NON HO POTUTO CONFRONTARLO CON `test_airgap_no_egress.py`, e lo scrivo
# invece di lasciar credere il contrario: quel file e' rosso in questo ambiente
# ANCHE SENZA il difetto (verificato con `config.py` ripristinato: EXIT=1 lo
# stesso), per `EncodeDelegateUnavailable: encode daemon unavailable and
# in-process cold-load is disabled (HIPPO_ENCODE_DELEGATE_ONLY=1)`. Un rosso che
# c'era gia' non si attribuisce al proprio difetto.
