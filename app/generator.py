"""Сборка теста: 30 заданий нарастающей сложности, новые при каждом прохождении.

Числовые ряды и визуальные матрицы строятся по правилам со случайными параметрами,
вербальные и логические задания берутся из банка (bank.py). Правильные ответы и
пояснения хранятся вместе с прохождением на сервере и клиенту не отдаются.
"""
from random import Random

from . import bank

CATEGORIES = {
    "pattern": "Визуальные паттерны",
    "num": "Числовые закономерности",
    "logic": "Логические выводы",
    "verbal": "Вербальная логика",
}

# Сколько заданий каждой сложности (1–5) даёт категория. Всего 30.
BLUEPRINT = {
    "pattern": [1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5],
    "num": [1, 1, 2, 2, 3, 3, 4, 5],
    "logic": [1, 2, 3, 4, 5],
    "verbal": [1, 2, 3, 4, 5],
}
TOTAL = sum(len(v) for v in BLUEPRINT.values())
MINUTES = 15


# ---------- числовые ряды ----------
def _num_rule(rng: Random, d: int) -> tuple[list[int], str]:
    """Возвращает ряд (последний элемент — ответ) и пояснение."""
    r = rng.randint
    if d == 1:
        if rng.random() < 0.5:
            a, k = r(1, 9), r(2, 9)
            return [a + k * i for i in range(6)], f"Каждое число больше предыдущего на {k}."
        a, q = r(1, 4), rng.choice([2, 3])
        return [a * q**i for i in range(5)], f"Каждое число в {q} раза больше предыдущего."
    if d == 2:
        kind = rng.choice(["alt", "grow", "sq"])
        if kind == "alt":
            a, up, down = r(5, 15), r(3, 6), r(1, 2)
            seq = [a]
            for i in range(6):
                seq.append(seq[-1] + (up if i % 2 == 0 else -down))
            return seq, f"Шаги чередуются: +{up}, −{down}, +{up}, −{down}…"
        if kind == "grow":
            a, k = r(1, 6), r(1, 3)
            seq = [a]
            for i in range(5):
                seq.append(seq[-1] + k + i)
            return seq, f"Прибавка каждый раз растёт на 1: +{k}, +{k + 1}, +{k + 2}…"
        n = r(1, 4)
        return [(n + i) ** 2 for i in range(6)], f"Это квадраты чисел подряд: {n}², {n + 1}², {n + 2}²…"
    if d == 3:
        kind = rng.choice(["dbl", "fib", "mix"])
        if kind == "dbl":
            a, k = r(1, 5), r(1, 3)
            seq = [a]
            for i in range(5):
                seq.append(seq[-1] + k * 2**i)
            return seq, f"Прибавка каждый раз удваивается: +{k}, +{2 * k}, +{4 * k}, +{8 * k}…"
        if kind == "fib":
            seq = [r(1, 4), r(2, 5)]
            for _ in range(5):
                seq.append(seq[-1] + seq[-2])
            return seq, "Каждое число равно сумме двух предыдущих."
        a, b, p, q = r(1, 5), r(10, 20), r(2, 4), r(5, 7)
        seq = [a + p * (i // 2) if i % 2 == 0 else b + q * (i // 2) for i in range(9)]
        return seq, (f"Чередуются два ряда: числа на нечётных местах растут на {p}, на чётных — на {q}. "
                     f"Следующее число — из первого ряда.")
    if d == 4:
        kind = rng.choice(["rec", "second", "triple"])
        if kind == "rec":
            a, c = r(1, 4), rng.choice([1, 3, -1])
            a = max(a, 2) if c == -1 else a
            seq = [a]
            for _ in range(5):
                seq.append(seq[-1] * 2 + c)
            return seq, f"Каждое число — это предыдущее, умноженное на 2, {'плюс' if c > 0 else 'минус'} {abs(c)}."
        if kind == "second":
            a, first, step = r(1, 5), r(2, 5), r(2, 4)
            seq = [a]
            for i in range(5):
                seq.append(seq[-1] + first + step * i)
            return seq, f"Прибавка растёт на {step}: +{first}, +{first + step}, +{first + 2 * step}…"
        a, k = r(2, 3), r(1, 2)
        seq = [a]
        for _ in range(4):
            seq.append(seq[-1] * 3 - k)
        return seq, f"Каждое число — это предыдущее, умноженное на 3, минус {k}."
    kind = rng.choice(["ops", "fact", "trib", "sqd"])
    if kind == "ops":
        a, k = r(1, 3), r(2, 4)
        seq = [a]
        for i in range(6):
            seq.append(seq[-1] * 2 if i % 2 == 0 else seq[-1] + k)
        return seq, f"Действия чередуются: ×2, +{k}, ×2, +{k}…"
    if kind == "fact":
        seq = [r(1, 3)]
        for i in range(2, 7):
            seq.append(seq[-1] * i)
        return seq, "Множитель каждый раз растёт на 1: ×2, ×3, ×4, ×5, ×6."
    if kind == "trib":
        seq = rng.choice([[1, 1, 2], [1, 2, 3], [2, 2, 3], [1, 3, 4]])[:]
        for _ in range(4):
            seq.append(sum(seq[-3:]))
        return seq, "Каждое число равно сумме трёх предыдущих."
    a = r(1, 6)
    seq = [a]
    for i in range(1, 6):
        seq.append(seq[-1] + i * i)
    return seq, "Прибавляются квадраты подряд: +1, +4, +9, +16, +25."


def _numeric(rng: Random, d: int) -> dict:
    seq, explain = _num_rule(rng, d)
    answer, last_step = seq[-1], seq[-1] - seq[-2]
    wrong = [answer + 1, answer - 1, answer + 2, seq[-2] + (seq[-2] - seq[-3]), answer - 2,
             answer + last_step // 2 or answer + 3, answer + 10, answer - 10, answer + 5]
    options, right = bank._numeric(rng, answer, wrong)
    return {"prompt": "Какое число продолжает ряд?", "series": ", ".join(map(str, seq[:-1])) + ", ?",
            "options": [{"text": o} for o in options], "correct": right,
            "explain": f"{explain} Ответ: {answer}."}


# ---------- визуальные матрицы ----------
SHAPES = ["circle", "square", "triangle", "diamond", "cross"]
FILLS = ["none", "light", "solid"]
SIZES = [0.5, 0.75, 1]
ATTR_NAME = {"shape": "форма", "fill": "заливка", "count": "количество фигур", "size": "размер"}
RULE_TEXT = {
    "row": "одинаково во всей строке и меняется от строки к строке",
    "col": "одинаково во всём столбце и меняется от столбца к столбцу",
    "latinA": "в каждой строке и в каждом столбце встречается по одному разу",
    "latinB": "в каждой строке и в каждом столбце встречается по одному разу",
    "sum": "в третьей клетке столько фигур, сколько в первых двух вместе",
}
INDEX = {"row": lambda r, c: r, "col": lambda r, c: c,
         "latinA": lambda r, c: (r + c) % 3, "latinB": lambda r, c: (r - c) % 3}
# Какие правила на каких признаках — по уровням сложности.
MATRIX_RULES = {
    1: ["col", "row"],
    2: ["latinA", "row"],
    3: ["latinA", "latinB"],
    4: ["latinA", "latinB", "col"],
    5: ["sum", "latinA", "latinB"],
}
SUM_ROWS = [(1, 1, 2), (1, 2, 3), (2, 1, 3), (1, 3, 4), (3, 1, 4), (2, 2, 4)]


def _fig(shape="circle", count=1, fill="solid", rot=0, size=1) -> dict:
    return {"shape": shape, "count": count, "fill": fill, "rot": rot, "size": size}


def _matrix(rng: Random, d: int) -> dict:
    rules = MATRIX_RULES[d][:]
    if "sum" in rules:  # сложение работает только с количеством; форма и заливка — латинские квадраты
        attrs = ["count"] + rng.sample(["shape", "fill"], 2)
    else:  # количество и размер не меняем одновременно — фигуры стали бы нечитаемыми
        attrs = rng.sample(["shape", "fill", rng.choice(["count", "size"])], len(rules))
        rng.shuffle(rules)
    values = {"shape": rng.sample(SHAPES, 3), "fill": rng.sample(FILLS, 3),
              "count": rng.sample([1, 2, 3], 3), "size": rng.sample(SIZES, 3)}
    sums = rng.sample(SUM_ROWS, 3)
    base = {"shape": rng.choice(SHAPES), "fill": rng.choice(["solid", "light"]), "count": 1, "size": 1}

    def cell(r: int, c: int) -> dict:
        fig = dict(base)
        for attr, rule in zip(attrs, rules):
            fig[attr] = sums[r][c] if rule == "sum" else values[attr][INDEX[rule](r, c)]
        return _fig(fig["shape"], fig["count"], fig["fill"], 0, fig["size"])

    cells = [cell(r, c) for r in range(3) for c in range(3)]
    answer = cells[8]
    wrong = []
    for attr in attrs:  # отвлекающие варианты отличаются от ответа одним-двумя признаками
        pool = [1, 2, 3, 4] if attr == "count" else {"shape": SHAPES, "fill": FILLS, "size": SIZES}[attr]
        for value in pool:
            if value != answer[attr]:
                wrong.append({**answer, attr: value})
    rng.shuffle(wrong)
    extra = [{**w, attrs[0]: v} for w in wrong for v in values[attrs[0]] if w[attrs[0]] == answer[attrs[0]]]
    options = _unique(rng, answer, wrong + extra, 6)
    explain = "; ".join(f"{ATTR_NAME[a]} — {RULE_TEXT[rule]}" for a, rule in zip(attrs, rules))
    return {"prompt": "Какая фигура должна стоять на месте знака вопроса?",
            "figure": {"cols": 3, "cells": cells[:8] + [None]},
            "options": [{"fig": o} for o in options], "correct": options.index(answer),
            "explain": f"Правила: {explain}."}


def _arrows(rng: Random, d: int) -> dict:
    start = rng.randrange(8) * 45
    if d <= 2:
        step = rng.choice([45, 90, 135])
        steps, explain = [step] * 4, f"Стрелка каждый раз поворачивается на {step}° по часовой стрелке."
    else:
        first = rng.choice([45, 90])
        steps = [first + 45 * i for i in range(4)]
        explain = ("Угол поворота каждый раз увеличивается на 45°: "
                   + ", ".join(f"+{s}°" for s in steps) + ".")
    angles = [start]
    for s in steps:
        angles.append((angles[-1] + s) % 360)
    answer = _fig("arrow", rot=angles[-1])
    options = _unique(rng, answer, [_fig("arrow", rot=a) for a in rng.sample(range(0, 360, 45), 8)], 6)
    return {"prompt": "Стрелка поворачивается по правилу. Какой будет следующая?",
            "figure": {"cols": 5, "cells": [_fig("arrow", rot=a) for a in angles[:4]] + [None]},
            "options": [{"fig": o} for o in options], "correct": options.index(answer), "explain": explain}


def _unique(rng: Random, answer: dict, wrong: list[dict], n: int) -> list[dict]:
    picked: list[dict] = []
    for w in wrong:
        if w != answer and w not in picked:
            picked.append(w)
    assert len(picked) >= n - 1, "мало отвлекающих вариантов"
    options = picked[: n - 1] + [answer]
    rng.shuffle(options)
    return options


def _pattern(rng: Random, d: int, slot: int) -> dict:
    # В части слотов вместо матрицы — ряд со стрелкой: разнообразие форматов.
    return _arrows(rng, d) if (d, slot) in {(2, 4), (4, 9)} else _matrix(rng, d)


def _text(rng: Random, d: int, source) -> dict:
    prompt, options, right, explain = source(rng, d)
    return {"prompt": prompt, "options": [{"text": o} for o in options], "correct": right, "explain": explain}


def build_test(seed: int) -> list[dict]:
    """Детерминированно по seed собирает тест; порядок — от простых заданий к сложным."""
    rng = Random(seed)
    questions = []
    for cat, difficulties in BLUEPRINT.items():
        for slot, d in enumerate(difficulties):
            if cat == "pattern":
                q = _pattern(rng, d, slot)
            elif cat == "num":
                q = _numeric(rng, d)
            else:
                q = _text(rng, d, bank.logic if cat == "logic" else bank.verbal)
            questions.append({**q, "cat": cat, "difficulty": d, "_order": rng.random()})
    questions.sort(key=lambda q: (q["difficulty"], q.pop("_order")))
    for n, q in enumerate(questions, 1):
        q["id"] = f"q{n}"
    return questions


PUBLIC_FIELDS = ("id", "prompt", "series", "figure", "options")


def public_questions(questions: list[dict]) -> list[dict]:
    """Вопросы для клиента: без ответов, сложности и пояснений."""
    return [{**{k: q[k] for k in PUBLIC_FIELDS if k in q}, "category": CATEGORIES[q["cat"]]} for q in questions]
