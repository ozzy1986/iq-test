"""Банк вопросов. Правильные ответы и пояснения живут только на сервере.

Фигуры описаны данными (shape/count/fill/rot) — фронтенд рисует их в SVG.
"""

CATEGORIES = {
    "num": "Числовые закономерности",
    "verbal": "Вербальная логика",
    "logic": "Логические выводы",
    "pattern": "Визуальные паттерны",
}


def _f(shape: str, count: int = 1, fill: str = "solid", rot: int = 0) -> dict:
    return {"shape": shape, "count": count, "fill": fill, "rot": rot}


def _t(*texts: str) -> list[dict]:
    return [{"text": t} for t in texts]


# difficulty: 1 — лёгкий, 2 — средний, 3 — сложный (вес вопроса в итоговом балле)
QUESTIONS: list[dict] = [
    {
        "id": "n1", "cat": "num", "difficulty": 1,
        "prompt": "Какое число продолжает ряд?",
        "series": "2, 4, 8, 16, ?",
        "options": _t("24", "30", "32", "36"), "correct": 2,
        "explain": "Каждое число вдвое больше предыдущего: 16 × 2 = 32.",
    },
    {
        "id": "v1", "cat": "verbal", "difficulty": 1,
        "prompt": "Какое слово лишнее?",
        "options": _t("Яблоко", "Груша", "Морковь", "Слива"), "correct": 2,
        "explain": "Морковь — овощ, остальные — фрукты.",
    },
    {
        "id": "p1", "cat": "pattern", "difficulty": 1,
        "prompt": "Какая фигура должна стоять на месте знака вопроса?",
        "figure": {"cols": 3, "cells": [
            _f("circle", 1), _f("circle", 2), _f("circle", 3),
            _f("square", 1), _f("square", 2), _f("square", 3),
            _f("triangle", 1), _f("triangle", 2), None,
        ]},
        "options": [{"fig": _f("triangle", 2)}, {"fig": _f("triangle", 3)},
                    {"fig": _f("square", 3)}, {"fig": _f("circle", 3)}],
        "correct": 1,
        "explain": "В строке фигура одна и та же, а количество растёт: 1, 2, 3. Нужны три треугольника.",
    },
    {
        "id": "l1", "cat": "logic", "difficulty": 1,
        "prompt": "Аня выше Бори. Боря выше Вики. Кто самый низкий?",
        "options": _t("Аня", "Боря", "Вика", "Нельзя определить"), "correct": 2,
        "explain": "Аня > Боря > Вика, значит самая низкая — Вика.",
    },
    {
        "id": "v2", "cat": "verbal", "difficulty": 2,
        "prompt": "Книга относится к чтению так же, как вилка — к…",
        "options": _t("кухне", "еде", "металлу", "тарелке"), "correct": 1,
        "explain": "Книга — предмет для чтения, вилка — предмет для еды.",
    },
    {
        "id": "n2", "cat": "num", "difficulty": 2,
        "prompt": "Какое число продолжает ряд?",
        "series": "7, 10, 8, 11, 9, 12, ?",
        "options": _t("10", "13", "14", "15"), "correct": 0,
        "explain": "Шаги чередуются: +3, −2, +3, −2… После 12 идёт 12 − 2 = 10.",
    },
    {
        "id": "p2", "cat": "pattern", "difficulty": 2,
        "prompt": "Какая фигура должна стоять на месте знака вопроса?",
        "figure": {"cols": 3, "cells": [
            _f("circle", fill="none"), _f("square", fill="solid"), _f("triangle", fill="light"),
            _f("square", fill="light"), _f("triangle", fill="none"), _f("circle", fill="solid"),
            _f("triangle", fill="solid"), _f("circle", fill="light"), None,
        ]},
        "options": [{"fig": _f("square", fill="solid")}, {"fig": _f("circle", fill="none")},
                    {"fig": _f("square", fill="none")}, {"fig": _f("triangle", fill="light")}],
        "correct": 2,
        "explain": "В каждой строке и столбце — по одной фигуре каждого вида и по одной заливке каждого вида. "
                   "Не хватает квадрата без заливки.",
    },
    {
        "id": "l2", "cat": "logic", "difficulty": 3,
        "prompt": "Все розы — цветы. Некоторые цветы быстро вянут. Что из этого следует наверняка?",
        "options": _t("Все розы быстро вянут", "Некоторые розы быстро вянут",
                      "Ни одна роза не вянет быстро", "Ничего из перечисленного"),
        "correct": 3,
        "explain": "Быстро вянущие цветы могут оказаться не розами, поэтому о розах ничего утверждать нельзя.",
    },
    {
        "id": "v3", "cat": "verbal", "difficulty": 2,
        "prompt": "Термометр относится к температуре так же, как компас — к…",
        "options": _t("северу", "направлению", "карте", "магниту"), "correct": 1,
        "explain": "Термометр измеряет температуру, компас показывает направление.",
    },
    {
        "id": "n3", "cat": "num", "difficulty": 3,
        "prompt": "Какое число продолжает ряд?",
        "series": "2, 3, 5, 9, 17, ?",
        "options": _t("25", "31", "33", "34"), "correct": 2,
        "explain": "Разница удваивается: +1, +2, +4, +8, +16. Получаем 17 + 16 = 33.",
    },
    {
        "id": "l3", "cat": "logic", "difficulty": 3,
        "prompt": "5 станков за 5 минут делают 5 деталей. За сколько минут 100 станков сделают 100 деталей?",
        "options": _t("100", "20", "5", "1"), "correct": 2,
        "explain": "Один станок делает одну деталь за 5 минут. 100 станков за те же 5 минут сделают 100 деталей.",
    },
    {
        "id": "p3", "cat": "pattern", "difficulty": 3,
        "prompt": "Стрелка поворачивается по правилу. Какой будет следующая?",
        "figure": {"cols": 5, "cells": [
            _f("arrow", rot=0), _f("arrow", rot=45), _f("arrow", rot=135), _f("arrow", rot=270), None,
        ]},
        "options": [{"fig": _f("arrow", rot=0)}, {"fig": _f("arrow", rot=315)},
                    {"fig": _f("arrow", rot=180)}, {"fig": _f("arrow", rot=90)}],
        "correct": 3,
        "explain": "Угол поворота каждый раз растёт на 45°: +45°, +90°, +135°, затем +180°. "
                   "Из положения «влево» стрелка разворачивается вправо.",
    },
]

BY_ID = {q["id"]: q for q in QUESTIONS}
PUBLIC_FIELDS = ("id", "prompt", "series", "figure", "options")


def public_questions() -> list[dict]:
    """Вопросы для клиента: без ответов, сложности и пояснений."""
    return [
        {**{k: q[k] for k in PUBLIC_FIELDS if k in q}, "category": CATEGORIES[q["cat"]]}
        for q in QUESTIONS
    ]
