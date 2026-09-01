# Repro-pack C10 — ambiente minimo per rieseguire «che tasso di falsita' serviamo».
#
# ⚠️ NON E' STATO COSTRUITO NE' ESEGUITO: e' scritto leggendo le dipendenze
# reali del banco (02/09, ws7) e va provato prima di offrirlo a terzi. Le righe
# che seguono dichiarano perche' ognuna e' li'.

# Il banco gira su 3.13 sulla macchina dove i numeri sono stati prodotti
# (`python 3.13.12`, letto). Una minor diversa non e' un problema noto, ma
# non e' stata provata.
FROM python:3.13-slim

# `git` non e' un vezzo: il banco chiama `git log -1 --format=%h` e SCRIVE il
# commit dentro il json di risultato (campo `commit`). Senza git l'artefatto
# perde la sua provenienza — e sarebbe uno dei 128 artefatti nudi su 372 che
# abbiamo censito (`LANT-150`).
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /repro

# Il banco stesso importa SOLO libreria standard (argparse, json, os, re,
# subprocess, sys, tempfile, pathlib): verificato leggendo gli import. Tutto
# cio' che serve davvero arriva da verimem, e da li' il torch/transformers che
# il giudice locale carica pigramente.
# ⚠️ Pinnare la versione ESATTA: i numeri pubblicati sono della 0.7.6.
RUN pip install --no-cache-dir "verimem==0.7.6"

# Il moat ha bisogno del suo cross-encoder locale (~746 MB: model.safetensors
# 737.7 + tokenizer.json 8.3). SENZA, il gate parte in stato «warming» e
# AMMETTE TUTTO, producendo numeri puliti e privi di significato — e' la
# trappola registrata in `W7-87`, scoperta sbattendoci contro, non cercandola.
# ⚠️ Il flag esatto va confermato con `verimem warmup --help`: non l'ho
# eseguito, e preferisco una riga da correggere a una inventata.
RUN verimem warmup || echo "ATTENZIONE: warmup fallito, reproduce.sh si fermera' allo step 2"

COPY . /repro

# Non fa nulla da solo: lo script dice PASS/FAIL confrontando con l'artefatto
# versionato, e ci mette ~70 minuti.
ENTRYPOINT ["bash", "repro/c10/reproduce.sh"]
