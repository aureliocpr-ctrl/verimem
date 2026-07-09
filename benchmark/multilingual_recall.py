"""Multilingual recall micro-bench: misura il buco lingue del retrieval.

Dato di partenza (Aurelio, 2026-07-09): interrogando il motore in lingue
diverse dall'inglese "8 lingue su 10 bucano". Questo bench rende il problema
un NUMERO riproducibile e confrontabile tra encoder: 20 fatti realistici in
inglese nello store, le stesse 10 domande in 10 lingue, recall@1/@5 per
lingua per modello (scenario cross-lingua: memoria scritta in EN, utente che
chiede nella sua lingua).

Fedeltà al path di produzione: i prefissi replicano ``engram.embedding
.as_query/as_passage`` (e5 -> "query: "/"passage: ") ed estendono la stessa
logica ai candidati (Qwen3 -> prompt "query" del modello; bge-m3 -> nessun
prefisso), che è esattamente ciò che il wiring adotterà per il modello scelto.
Niente DB, niente daemon: encode + cosine, il cuore del recall semantico.

Uso:
    python benchmark/multilingual_recall.py --models intfloat/multilingual-e5-base
    python benchmark/multilingual_recall.py --models intfloat/multilingual-e5-base Qwen/Qwen3-Embedding-0.6B BAAI/bge-m3
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

# ---- store: 20 fatti realistici (memoria personale/di lavoro, EN) ----------
FACTS = [
    "Alice moved to Berlin in March 2024 for her new job at a fintech startup.",
    "The production database password is rotated every 90 days by the ops team.",
    "Marco is allergic to peanuts and always carries an epinephrine injector.",
    "The Q3 revenue target was set at 2.4 million euros during the June board meeting.",
    "Sofia's daughter starts primary school in September 2026 in Lisbon.",
    "The deploy pipeline requires two approvals before any release to production.",
    "Grandmother's lasagna recipe uses bechamel instead of ricotta, layered five times.",
    "The client meeting with Nakamura-san is scheduled for Thursday at 9 AM Tokyo time.",
    "Our rental contract in Via Roma 12 expires on the 31st of December 2026.",
    "The medical checkup showed slightly elevated cholesterol; next control in six months.",
    "David prefers window seats and always books the 7:40 morning train to Milan.",
    "The company switched from AWS to a self-hosted Kubernetes cluster in 2025 to cut costs.",
    "Elena's wedding anniversary is on the 14th of February; she married Tom in 2019.",
    "The insurance policy number for the car is IT-4482-9917-B, renewed each July.",
    "Project Falcon's codebase is written in Rust with a PostgreSQL storage layer.",
    "The dentist appointment for the root canal is on Monday the 20th at 4:30 PM.",
    "Karim's favourite dish is his mother's couscous with seven vegetables.",
    "The tax deadline for the VAT quarterly filing is the 16th of the month.",
    "The hiking trip to the Dolomites is planned for the last week of August.",
    "The office wifi password changed last Tuesday; it is now on the intranet page.",
]

# ---- 10 domande, gold = indice del fatto ------------------------------------
# Le stesse domande in 10 lingue (en = controllo). Traduzioni semplici e
# idiomatiche; il gold non cambia con la lingua.
QUERIES: dict[str, list[tuple[str, int]]] = {
    "en": [
        ("Where did Alice move for her new job?", 0),
        ("What is Marco allergic to?", 2),
        ("What was the Q3 revenue target?", 3),
        ("When does the rental contract expire?", 8),
        ("What did the medical checkup show?", 9),
        ("Which seats does David prefer on the train?", 10),
        ("When is Elena's wedding anniversary?", 12),
        ("What language is Project Falcon written in?", 14),
        ("When is the dentist appointment for the root canal?", 15),
        ("Where is the hiking trip planned?", 18),
    ],
    "it": [
        ("Dove si è trasferita Alice per il nuovo lavoro?", 0),
        ("A cosa è allergico Marco?", 2),
        ("Qual era l'obiettivo di fatturato del terzo trimestre?", 3),
        ("Quando scade il contratto d'affitto?", 8),
        ("Cosa ha mostrato il controllo medico?", 9),
        ("Quali posti preferisce David in treno?", 10),
        ("Quand'è l'anniversario di matrimonio di Elena?", 12),
        ("In che linguaggio è scritto il progetto Falcon?", 14),
        ("Quand'è l'appuntamento dal dentista per la devitalizzazione?", 15),
        ("Dove è prevista la gita in montagna?", 18),
    ],
    "es": [
        ("¿A dónde se mudó Alice por su nuevo trabajo?", 0),
        ("¿A qué es alérgico Marco?", 2),
        ("¿Cuál era el objetivo de ingresos del tercer trimestre?", 3),
        ("¿Cuándo vence el contrato de alquiler?", 8),
        ("¿Qué mostró el chequeo médico?", 9),
        ("¿Qué asientos prefiere David en el tren?", 10),
        ("¿Cuándo es el aniversario de boda de Elena?", 12),
        ("¿En qué lenguaje está escrito el proyecto Falcon?", 14),
        ("¿Cuándo es la cita con el dentista para la endodoncia?", 15),
        ("¿Dónde está planeada la excursión a la montaña?", 18),
    ],
    "fr": [
        ("Où Alice a-t-elle déménagé pour son nouveau travail ?", 0),
        ("À quoi Marco est-il allergique ?", 2),
        ("Quel était l'objectif de chiffre d'affaires du troisième trimestre ?", 3),
        ("Quand expire le contrat de location ?", 8),
        ("Qu'a montré le bilan médical ?", 9),
        ("Quelles places David préfère-t-il dans le train ?", 10),
        ("Quand est l'anniversaire de mariage d'Elena ?", 12),
        ("En quel langage le projet Falcon est-il écrit ?", 14),
        ("Quand est le rendez-vous chez le dentiste pour la dévitalisation ?", 15),
        ("Où la randonnée est-elle prévue ?", 18),
    ],
    "de": [
        ("Wohin ist Alice für ihren neuen Job gezogen?", 0),
        ("Wogegen ist Marco allergisch?", 2),
        ("Was war das Umsatzziel für das dritte Quartal?", 3),
        ("Wann läuft der Mietvertrag aus?", 8),
        ("Was hat die ärztliche Untersuchung ergeben?", 9),
        ("Welche Plätze bevorzugt David im Zug?", 10),
        ("Wann ist Elenas Hochzeitstag?", 12),
        ("In welcher Sprache ist Projekt Falcon geschrieben?", 14),
        ("Wann ist der Zahnarzttermin für die Wurzelbehandlung?", 15),
        ("Wo ist die Wanderung geplant?", 18),
    ],
    "pt": [
        ("Para onde Alice se mudou pelo novo emprego?", 0),
        ("A que Marco é alérgico?", 2),
        ("Qual era a meta de receita do terceiro trimestre?", 3),
        ("Quando expira o contrato de aluguel?", 8),
        ("O que o exame médico mostrou?", 9),
        ("Quais assentos David prefere no trem?", 10),
        ("Quando é o aniversário de casamento da Elena?", 12),
        ("Em que linguagem o projeto Falcon foi escrito?", 14),
        ("Quando é a consulta no dentista para o canal?", 15),
        ("Onde está planejada a trilha na montanha?", 18),
    ],
    "ru": [
        ("Куда переехала Алиса ради новой работы?", 0),
        ("На что у Марко аллергия?", 2),
        ("Какова была цель по выручке на третий квартал?", 3),
        ("Когда истекает договор аренды?", 8),
        ("Что показал медицинский осмотр?", 9),
        ("Какие места предпочитает Дэвид в поезде?", 10),
        ("Когда годовщина свадьбы Елены?", 12),
        ("На каком языке написан проект Falcon?", 14),
        ("Когда приём у стоматолога по поводу лечения канала?", 15),
        ("Где запланирован поход в горы?", 18),
    ],
    "zh": [
        ("Alice为了新工作搬到了哪里？", 0),
        ("Marco对什么过敏？", 2),
        ("第三季度的营收目标是多少？", 3),
        ("租房合同什么时候到期？", 8),
        ("体检结果显示了什么？", 9),
        ("David坐火车喜欢什么座位？", 10),
        ("Elena的结婚纪念日是什么时候？", 12),
        ("Falcon项目是用什么语言写的？", 14),
        ("根管治疗的牙医预约是什么时候？", 15),
        ("登山旅行计划在哪里？", 18),
    ],
    "ja": [
        ("アリスは新しい仕事のためにどこへ引っ越しましたか？", 0),
        ("マルコは何のアレルギーがありますか？", 2),
        ("第3四半期の売上目標はいくらでしたか？", 3),
        ("賃貸契約はいつ切れますか？", 8),
        ("健康診断で何がわかりましたか？", 9),
        ("デイビッドは電車でどの席を好みますか？", 10),
        ("エレナの結婚記念日はいつですか？", 12),
        ("ファルコンプロジェクトは何の言語で書かれていますか？", 14),
        ("根管治療の歯医者の予約はいつですか？", 15),
        ("ハイキング旅行はどこで計画されていますか？", 18),
    ],
    "ar": [
        ("إلى أين انتقلت أليس من أجل عملها الجديد؟", 0),
        ("ممَّ يعاني ماركو من الحساسية؟", 2),
        ("ما هو هدف الإيرادات للربع الثالث؟", 3),
        ("متى ينتهي عقد الإيجار؟", 8),
        ("ماذا أظهر الفحص الطبي؟", 9),
        ("أي المقاعد يفضل ديفيد في القطار؟", 10),
        ("متى ذكرى زواج إيلينا؟", 12),
        ("بأي لغة كُتب مشروع فالكون؟", 14),
        ("متى موعد طبيب الأسنان لعلاج قناة الجذر؟", 15),
        ("أين من المقرر رحلة المشي في الجبال؟", 18),
    ],
}


def _prefixes(model_name: str) -> tuple[str | None, str, str]:
    """(query_prompt_name, query_prefix, passage_prefix) per modello — replica
    engram.embedding.as_query/as_passage ed estende ai candidati secondo le
    rispettive model card (e5: 'query: '/'passage: '; qwen3: prompt 'query'
    nativo del modello, documenti nudi; bge-m3: simmetrico, nessun prefisso)."""
    low = model_name.lower()
    if "e5" in low:
        return None, "query: ", "passage: "
    if "qwen3-embedding" in low:
        return "query", "", ""
    return None, "", ""


def run_model(model_name: str) -> dict:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    t0 = time.time()
    model = SentenceTransformer(model_name)
    load_s = round(time.time() - t0, 1)
    prompt_name, qpre, ppre = _prefixes(model_name)

    corpus = model.encode([ppre + f for f in FACTS],
                          normalize_embeddings=True, show_progress_bar=False)
    out: dict = {"model": model_name, "load_s": load_s, "languages": {}}
    r1_all = r5_all = n_all = 0
    for lang, qs in QUERIES.items():
        kw = {"prompt_name": prompt_name} if prompt_name else {}
        vecs = model.encode([qpre + q for q, _ in qs],
                            normalize_embeddings=True,
                            show_progress_bar=False, **kw)
        r1 = r5 = 0
        for vec, (_, gold) in zip(vecs, qs):
            order = np.argsort(-(corpus @ vec))
            if order[0] == gold:
                r1 += 1
            if gold in order[:5]:
                r5 += 1
        out["languages"][lang] = {
            "recall@1": round(r1 / len(qs), 2), "recall@5": round(r5 / len(qs), 2)}
        r1_all += r1; r5_all += r5; n_all += len(qs)
    out["mean"] = {"recall@1": round(r1_all / n_all, 3),
                   "recall@5": round(r5_all / n_all, 3)}
    # "lingua che buca" = recall@5 < 0.8 (2+ domande su 10 perse)
    out["broken_languages"] = sorted(
        lang for lang, m in out["languages"].items() if m["recall@5"] < 0.8)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", default="benchmark/results/multilingual_recall.json")
    args = ap.parse_args()

    results = []
    for name in args.models:
        print(f"== {name}")
        res = run_model(name)
        results.append(res)
        for lang, m in res["languages"].items():
            print(f"  {lang}: r@1={m['recall@1']:.2f} r@5={m['recall@5']:.2f}")
        print(f"  MEAN r@1={res['mean']['recall@1']} r@5={res['mean']['recall@5']}"
              f"  broken(r@5<0.8)={res['broken_languages']}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(
        {"facts": len(FACTS), "queries_per_lang": 10, "results": results},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
