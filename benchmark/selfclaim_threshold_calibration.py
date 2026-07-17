"""Calibrazione soglia per il detector semantico L1.20 (self-claim multilingua).

Il fix del buco 8/10 lingue (gate L1 = keyword EN/IT-only, riprodotto
2026-07-09): confrontare la claim in ingresso con ESEMPLARI di self-claim
hype in inglese via embedding multilingue — il cross-lingua del ranking è
1.00 (multilingual_recall.py), quindi l'esemplare EN deve attrarre la stessa
claim in de/zh/ar/...

Questo script misura la SEPARAZIONE (max-cosine vs esemplari) tra:
  * positivi — claim non supportate in 10 lingue (4 famiglie L1:
    deploy-works, tests-passed, production-ready, bug-fixed);
  * negativi — fatti legittimi (20 EN del bench multilingua + 40 tradotti),
    inclusi i casi trappola con lessico da deploy ("the production database
    password...").

Output: distribuzioni, best threshold precision-first (zero FP sui negativi,
massimo recall sui positivi) e margine. Riusabile per confrontare encoder:
    python benchmark/selfclaim_threshold_calibration.py --models intfloat/multilingual-e5-base Qwen/Qwen3-Embedding-0.6B
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# SINGLE SOURCE: gli esemplari/àncore di PRODUZIONE (verimem.semantic_selfclaim).
# La calibrazione deve misurare esattamente ciò che il detector userà — un set
# duplicato qui andrebbe fuori sync alla prima modifica. I primi 12 esemplari
# sono gli EN storici (la lista base delle prime run); --ml-exemplars aggiunge
# il resto (full set di produzione).
from verimem.semantic_selfclaim import ANCHORS as _PROD_ANCHORS  # noqa: E402
from verimem.semantic_selfclaim import EXEMPLARS as _PROD_EXEMPLARS  # noqa: E402

EXEMPLARS = _PROD_EXEMPLARS[:12]  # blocco EN

# Positivi: la stessa sostanza in 10 lingue (famiglie diverse per riga).
POSITIVES = {
    "en": ["the deployment works and is verified in production",
           "all the tests passed successfully",
           "the feature is complete and production-ready",
           "the bug is fixed and everything is resolved"],
    "it": ["il deployment funziona ed è verificato in produzione",
           "tutti i test sono passati con successo",
           "la funzionalità è completa e pronta per la produzione",
           "il bug è risolto e tutto funziona"],
    "es": ["el despliegue funciona y está verificado en producción",
           "todas las pruebas pasaron con éxito",
           "la funcionalidad está completa y lista para producción",
           "el error está corregido y todo funciona"],
    "fr": ["le déploiement fonctionne et est vérifié en production",
           "tous les tests sont passés avec succès",
           "la fonctionnalité est complète et prête pour la production",
           "le bug est corrigé et tout fonctionne"],
    "de": ["das Deployment funktioniert und ist in der Produktion verifiziert",
           "alle Tests wurden erfolgreich bestanden",
           "das Feature ist fertig und produktionsreif",
           "der Fehler ist behoben und alles funktioniert"],
    "pt": ["o deployment funciona e está verificado em produção",
           "todos os testes passaram com sucesso",
           "a funcionalidade está completa e pronta para produção",
           "o bug foi corrigido e tudo funciona"],
    "ru": ["развертывание работает и проверено в продакшене",
           "все тесты успешно пройдены",
           "функция завершена и готова к продакшену",
           "ошибка исправлена и все работает"],
    "zh": ["部署可以正常工作并且已在生产环境中验证",
           "所有测试都成功通过了",
           "该功能已完成并可以投入生产",
           "错误已修复，一切正常"],
    "ja": ["デプロイは動作しており、本番環境で検証済みです",
           "すべてのテストが正常に合格しました",
           "機能は完成しており、本番環境の準備ができています",
           "バグは修正され、すべて正常に動作しています"],
    "ar": ["النشر يعمل وتم التحقق منه في بيئة الإنتاج",
           "اجتازت جميع الاختبارات بنجاح",
           "الميزة مكتملة وجاهزة للإنتاج",
           "تم إصلاح الخطأ وكل شيء يعمل"],
}

# Negativi: fatti legittimi — memoria personale/di lavoro, con trappole
# lessicali (production, tests, works nel senso innocuo).
NEGATIVES_EN = [
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
    "The company switched from AWS to a self-hosted Kubernetes cluster in 2025.",
    "Elena's wedding anniversary is on the 14th of February; she married Tom in 2019.",
    "The insurance policy number for the car is IT-4482-9917-B, renewed each July.",
    "Project Falcon's codebase is written in Rust with a PostgreSQL storage layer.",
    "The dentist appointment for the root canal is on Monday the 20th at 4:30 PM.",
    "Karim's favourite dish is his mother's couscous with seven vegetables.",
    "The tax deadline for the VAT quarterly filing is the 16th of the month.",
    "The hiking trip to the Dolomites is planned for the last week of August.",
    "The office wifi password changed last Tuesday; it is now on the intranet page.",
    "The team works from the Milan office on Tuesdays and Thursdays.",
    "Test results from the lab arrive within three business days.",
]

NEGATIVES_ML = [
    # it
    "Alice si è trasferita a Berlino a marzo 2024 per il nuovo lavoro.",
    "La password del database di produzione viene ruotata ogni 90 giorni.",
    "Il team lavora dall'ufficio di Milano il martedì e il giovedì.",
    "Il contratto d'affitto in Via Roma 12 scade il 31 dicembre 2026.",
    # de
    "Alice ist im März 2024 für ihren neuen Job nach Berlin gezogen.",
    "Das Passwort der Produktionsdatenbank wird alle 90 Tage geändert.",
    "Das Team arbeitet dienstags und donnerstags im Mailänder Büro.",
    "Der Mietvertrag in der Via Roma 12 läuft am 31. Dezember 2026 aus.",
    # ru
    "Алиса переехала в Берлин в марте 2024 года ради новой работы.",
    "Пароль производственной базы данных меняется каждые 90 дней.",
    "Команда работает из миланского офиса по вторникам и четвергам.",
    # zh
    "Alice于2024年3月为了新工作搬到了柏林。",
    "生产数据库的密码每90天轮换一次。",
    "团队周二和周四在米兰办公室工作。",
    # ar
    "انتقلت أليس إلى برلين في مارس 2024 من أجل عملها الجديد.",
    "يتم تغيير كلمة مرور قاعدة بيانات الإنتاج كل 90 يومًا.",
    "يعمل الفريق من مكتب ميلانو أيام الثلاثاء والخميس.",
    # es / fr / pt / ja
    "El equipo trabaja desde la oficina de Milán los martes y jueves.",
    "L'équipe travaille depuis le bureau de Milan les mardis et jeudis.",
    "A equipe trabalha do escritório de Milão às terças e quintas.",
    "チームは火曜日と木曜日にミラノのオフィスで働いています。",
]


# Derivati dalla SINGLE SOURCE di produzione (vedi import in testa):
# EXEMPLARS_ML = blocco multilingua degli esemplari di produzione;
# le àncore di produzione coprono già EN+ML (split per parità storica dei flag).
EXEMPLARS_ML = _PROD_EXEMPLARS[12:]
NEUTRAL_ANCHORS = _PROD_ANCHORS[:10]      # blocco EN
NEUTRAL_ANCHORS_ML = _PROD_ANCHORS[10:]   # blocco multilingua


def _prefixes(model_name: str):
    low = model_name.lower()
    if "e5" in low:
        return None, "query: ", "passage: "
    if "qwen3-embedding" in low:
        return "query", "", ""
    return None, "", ""


def run_model(model_name: str, *, contrastive: bool = False,
              symmetric: bool = False, ml_exemplars: bool = False) -> dict:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    prompt_name, qpre, ppre = _prefixes(model_name)
    if symmetric:  # STS-style: nessuna asimmetria query/passage
        prompt_name, qpre, ppre = None, "", ""
    exemplars = EXEMPLARS + (EXEMPLARS_ML if ml_exemplars else [])
    anchor_texts = NEUTRAL_ANCHORS + (NEUTRAL_ANCHORS_ML if ml_exemplars else [])
    # gli esemplari giocano il ruolo di "passage" (indice fisso), la claim
    # in ingresso quello di "query" — stessa asimmetria del recall reale.
    ex = model.encode([ppre + e for e in exemplars],
                      normalize_embeddings=True, show_progress_bar=False)
    anchors = model.encode([ppre + a for a in anchor_texts],
                           normalize_embeddings=True, show_progress_bar=False)
    kw = {"prompt_name": prompt_name} if prompt_name else {}

    def score2d(texts):
        """(max_cos_hype, delta_vs_neutral) per testo — le due dimensioni
        del dual-check."""
        vecs = model.encode([qpre + t for t in texts],
                            normalize_embeddings=True,
                            show_progress_bar=False, **kw)
        hype = (vecs @ ex.T).max(axis=1)
        delta = hype - (vecs @ anchors.T).max(axis=1)
        return hype, delta

    def score(texts):
        hype, delta = score2d(texts)
        return delta if contrastive else hype

    pos_by_lang = {lang: score(claims).tolist()
                   for lang, claims in POSITIVES.items()}
    neg = score(NEGATIVES_EN + NEGATIVES_ML)
    all_pos = np.array([s for v in pos_by_lang.values() for s in v])

    # soglia precision-first: sopra il max dei negativi, con margine
    neg_max = float(neg.max())
    candidates = sorted(set(round(t, 3) for t in all_pos) | {round(neg_max + 0.005, 3)})
    best = None
    for t in candidates:
        fp = int((neg >= t).sum())
        if fp == 0:
            rec = float((all_pos >= t).mean())
            if best is None or rec > best["recall"]:
                best = {"threshold": t, "recall": round(rec, 3), "fp": 0}
    per_lang_at_best = {
        lang: round(sum(1 for s in v if s >= best["threshold"]) / len(v), 2)
        for lang, v in pos_by_lang.items()} if best else {}

    # ---- DUAL-CHECK: hype >= T1 AND delta >= T2 (griglia 2D) ---------------
    pos_h, pos_d = score2d([c for v in POSITIVES.values() for c in v])
    neg_h, neg_d = score2d(NEGATIVES_EN + NEGATIVES_ML)
    dual_best = None
    for t1 in [round(x, 3) for x in np.arange(0.78, 0.90, 0.005)]:
        for t2 in [round(x, 3) for x in np.arange(0.0, 0.12, 0.005)]:
            fp = int(((neg_h >= t1) & (neg_d >= t2)).sum())
            if fp:
                continue
            rec = float(((pos_h >= t1) & (pos_d >= t2)).mean())
            # margine = distanza minima dei negativi dalla frontiera accettata
            margin = float(min(
                (t1 - neg_h[neg_d >= t2]).min() if (neg_d >= t2).any() else 1.0,
                (t2 - neg_d[neg_h >= t1]).min() if (neg_h >= t1).any() else 1.0))
            key = (rec, margin)
            if dual_best is None or key > (dual_best["recall"], dual_best["margin"]):
                dual_best = {"t_hype": t1, "t_delta": t2,
                             "recall": round(rec, 3), "fp": 0,
                             "margin": round(margin, 3)}
    return {
        "model": model_name,
        "mode": ("contrastive" if contrastive else "absolute")
                + ("+symmetric" if symmetric else "")
                + ("+ml_exemplars" if ml_exemplars else ""),
        "positives_min": round(float(all_pos.min()), 3),
        "positives_mean": round(float(all_pos.mean()), 3),
        "negatives_max": round(neg_max, 3),
        "negatives_mean": round(float(neg.mean()), 3),
        "separation": round(float(all_pos.min()) - neg_max, 3),
        "best": best,
        "recall_per_lang_at_best": per_lang_at_best,
        "dual_best": dual_best,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--contrastive", action="store_true")
    ap.add_argument("--symmetric", action="store_true")
    ap.add_argument("--ml-exemplars", action="store_true")
    ap.add_argument("--out",
                    default="benchmark/results/selfclaim_threshold_calibration.json")
    args = ap.parse_args()
    results = []
    for name in args.models:
        print(f"== {name}")
        r = run_model(name, contrastive=args.contrastive,
                      symmetric=args.symmetric, ml_exemplars=args.ml_exemplars)
        results.append(r)
        print(f"  pos min/mean {r['positives_min']}/{r['positives_mean']}  "
              f"neg max/mean {r['negatives_max']}/{r['negatives_mean']}  "
              f"separation {r['separation']}")
        print(f"  best {r['best']}  per-lang {r['recall_per_lang_at_best']}")
        print(f"  DUAL {r['dual_best']}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps({"exemplars": len(EXEMPLARS),
                    "positives": sum(len(v) for v in POSITIVES.values()),
                    "negatives": len(NEGATIVES_EN) + len(NEGATIVES_ML),
                    "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
