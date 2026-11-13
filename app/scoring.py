"""Подсчёт результата. Это развлекательная оценка, не психометрический инструмент.

Балл = сумма весов (сложностей) верных ответов. Доля от максимума линейно
отображается в шкалу 72–140, процентиль берётся из нормального распределения
N(100, 15) — так же, как это подают массовые IQ-сервисы.
"""
import math

from .questions import BY_ID, CATEGORIES, QUESTIONS

IQ_MIN, IQ_MAX = 72, 140

LEVELS = [
    (130, "Очень высокий", "Вы справились почти со всеми заданиями, включая самые сложные. "
                           "Такой результат показывает небольшая доля участников."),
    (120, "Высокий", "Вы уверенно решаете задачи повышенной сложности и быстро находите закономерности."),
    (110, "Выше среднего", "Вы решаете большинство задач и ошибаетесь в основном на сложных."),
    (90, "Средний", "Результат в диапазоне, в который попадает большинство людей."),
    (0, "Ниже среднего", "Часть заданий далась тяжело. На результат сильно влияют усталость, спешка и "
                         "непривычный формат — стоит попробовать ещё раз в спокойной обстановке."),
]

STRENGTH = {
    "num": "Вы хорошо видите числовые закономерности — это основа аналитических и количественных задач.",
    "verbal": "Вы точно улавливаете связи между понятиями — это помогает быстро разбираться в новой информации.",
    "logic": "Вы аккуратно делаете выводы из условий и не поддаётесь на интуитивно «очевидные» ответы.",
    "pattern": "Вы легко замечаете визуальные правила и удерживаете в голове несколько признаков сразу.",
}
GROWTH = {
    "num": "Числовые ряды: полезно выписывать разницу между соседними числами — правило часто спрятано в ней.",
    "verbal": "Аналогии: сформулируйте связь первой пары одной фразой и подставьте её ко второй паре.",
    "logic": "Логические выводы: проверяйте, следует ли ответ из условий, а не просто звучит правдоподобно.",
    "pattern": "Визуальные паттерны: разбирайте признаки по отдельности — форма, количество, заливка, поворот.",
}


def score(answers: dict) -> dict:
    raw = 0
    breakdown = {key: {"correct": 0, "total": 0} for key in CATEGORIES}
    for q in QUESTIONS:
        ok = answers.get(q["id"]) == q["correct"]
        breakdown[q["cat"]]["total"] += 1
        if ok:
            breakdown[q["cat"]]["correct"] += 1
            raw += q["difficulty"]
    score_max = sum(q["difficulty"] for q in QUESTIONS)
    iq = round(IQ_MIN + (IQ_MAX - IQ_MIN) * raw / score_max)
    cdf = 0.5 * (1 + math.erf((iq - 100) / (15 * math.sqrt(2))))
    percentile = min(99, max(1, round(cdf * 100)))
    return {"score_raw": raw, "score_max": score_max, "iq": iq, "percentile": percentile, "breakdown": breakdown}


def level_for(iq: int) -> dict:
    for threshold, title, text in LEVELS:
        if iq >= threshold:
            return {"title": title, "text": text}
    raise AssertionError("unreachable")


def insights(breakdown: dict, duration_sec: int) -> list[str]:
    ratio = {k: v["correct"] / v["total"] for k, v in breakdown.items()}
    best = max(ratio, key=ratio.get)
    worst = min(ratio, key=ratio.get)
    out = []
    if ratio[best] > 0:
        out.append(STRENGTH[best])
    if ratio[worst] < 1 and worst != best:
        out.append(GROWTH[worst])
    per_q = duration_sec / len(QUESTIONS)
    if per_q < 12:
        out.append("Вы отвечали очень быстро — в среднем меньше 12 секунд на вопрос. "
                   "Если дать себе больше времени на сложные задания, результат обычно растёт.")
    elif per_q > 75:
        out.append("Вы не торопились и обдумывали ответы — это снижает число случайных ошибок.")
    else:
        out.append("Темп прохождения ровный: вы не спешили и не застревали на отдельных вопросах.")
    return out


def review(answers: dict) -> list[dict]:
    """Разбор ответов для платного отчёта."""
    out = []
    for n, q in enumerate(QUESTIONS, 1):
        chosen = answers.get(q["id"])
        out.append({
            "n": n,
            "category": CATEGORIES[q["cat"]],
            "prompt": q["prompt"],
            "series": q.get("series"),
            "your": q["options"][chosen] if isinstance(chosen, int) else None,
            "right": q["options"][q["correct"]],
            "is_correct": chosen == q["correct"],
            "explain": q["explain"],
        })
    return out


assert all(0 <= q["correct"] < len(q["options"]) for q in QUESTIONS)
assert len(BY_ID) == len(QUESTIONS)
