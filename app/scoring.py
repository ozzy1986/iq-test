"""Оценка результата по стандартной шкале IQ.

Шкала — общепринятая девиационная (как в тестах Векслера): среднее 100, стандартное
отклонение 15. Уровень способности θ оценивается методами современной теории
тестирования (IRT, трёхпараметрическая модель): учитывается, какие именно задания
решены, их сложность и вероятность угадать ответ. Берётся апостериорное среднее θ
при нормальном априорном распределении, IQ = 100 + 15·θ; разброс оценки даёт погрешность.

Чего здесь нет: нормировки на выборке. Сложности заданий заданы экспертно (пять уровней),
поэтому результат — ориентировочный. Это честно показано в отчёте.
"""
import math

from .generator import CATEGORIES

DISCRIMINATION = 1.3
DIFFICULTY = {1: -2.0, 2: -1.0, 3: 0.0, 4: 1.0, 5: 2.0}  # в единицах стандартного отклонения
GRID = [-4 + 0.05 * i for i in range(161)]

LEVELS = [
    (130, "Очень высокий", "Вы справились почти со всеми заданиями, включая самые сложные. "
                           "Такой результат показывает около 2% людей."),
    (120, "Высокий", "Вы уверенно решаете задачи повышенной сложности и быстро находите закономерности."),
    (110, "Выше среднего", "Вы решаете большинство задач и ошибаетесь в основном на сложных."),
    (90, "Средний", "Результат в диапазоне, в который попадает примерно половина людей."),
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
    "pattern": "Визуальные паттерны: разбирайте признаки по отдельности — форма, количество, заливка, размер.",
}


def is_correct(question: dict, answers: dict) -> bool:
    return answers.get(question["id"]) == question["correct"]


def estimate(questions: list[dict], answers: dict) -> tuple[float, float]:
    """Апостериорные среднее и стандартное отклонение θ. Пропущенный ответ считается неверным."""
    posterior = [math.exp(-t * t / 2) for t in GRID]
    for q in questions:
        guess = 1 / len(q["options"])
        b, ok = DIFFICULTY[q["difficulty"]], is_correct(q, answers)
        for i, t in enumerate(GRID):
            p = guess + (1 - guess) / (1 + math.exp(-DISCRIMINATION * (t - b)))
            posterior[i] *= p if ok else 1 - p
    total = sum(posterior)
    mean = sum(t * w for t, w in zip(GRID, posterior)) / total
    var = sum((t - mean) ** 2 * w for t, w in zip(GRID, posterior)) / total
    return mean, math.sqrt(var)


def percentile_of(iq: int) -> int:
    cdf = 0.5 * (1 + math.erf((iq - 100) / (15 * math.sqrt(2))))
    return min(99, max(1, round(cdf * 100)))


def score(questions: list[dict], answers: dict) -> dict:
    theta, spread = estimate(questions, answers)
    iq = round(100 + 15 * theta)
    breakdown = {key: {"correct": 0, "total": 0} for key in CATEGORIES}
    for q in questions:
        breakdown[q["cat"]]["total"] += 1
        breakdown[q["cat"]]["correct"] += is_correct(q, answers)
    return {"iq": iq, "margin": round(15 * spread), "percentile": percentile_of(iq), "breakdown": breakdown,
            "correct": sum(c["correct"] for c in breakdown.values()), "total": len(questions)}


def level_for(iq: int) -> dict:
    for threshold, title, text in LEVELS:
        if iq >= threshold:
            return {"title": title, "text": text}
    raise AssertionError("unreachable")


def insights(breakdown: dict, duration_sec: int, total: int) -> list[str]:
    ratio = {k: v["correct"] / v["total"] for k, v in breakdown.items()}
    best = max(ratio, key=ratio.get)
    worst = min(ratio, key=ratio.get)
    out = []
    if ratio[best] > 0:
        out.append(STRENGTH[best])
    if ratio[worst] < 1 and worst != best:
        out.append(GROWTH[worst])
    per_question = duration_sec / total
    if per_question < 10:
        out.append("Вы отвечали очень быстро — в среднем меньше 10 секунд на вопрос. "
                   "Если дать себе больше времени на сложные задания, результат обычно растёт.")
    elif per_question > 60:
        out.append("Вы не торопились и обдумывали ответы — это снижает число случайных ошибок.")
    else:
        out.append("Темп прохождения ровный: вы не спешили и не застревали на отдельных вопросах.")
    return out


def review(questions: list[dict], answers: dict) -> list[dict]:
    """Разбор ответов для платного отчёта."""
    out = []
    for n, q in enumerate(questions, 1):
        chosen = answers.get(q["id"])
        out.append({
            "n": n,
            "category": CATEGORIES[q["cat"]],
            "difficulty": q["difficulty"],
            "prompt": q["prompt"],
            "series": q.get("series"),
            "figure": q.get("figure"),
            "your": q["options"][chosen] if isinstance(chosen, int) else None,
            "right": q["options"][q["correct"]],
            "is_correct": chosen == q["correct"],
            "explain": q["explain"],
        })
    return out
