"""Калибровка сложности: проверяем на смоделированных участниках, что метод работает.

Сценарий из жизни: эксперт ошибся, и часть заданий на деле труднее, чем он думал. До калибровки
шкала занижает всех; после — возвращается к среднему 100 и восстанавливает настоящие сложности.
"""
import math
from random import Random

import pytest

from app import calibrate, scoring
from app.generator import build_test

SHIFT = 0.8  # настолько задания «на самом деле» труднее экспертной оценки


def true_difficulty(question: dict) -> float:
    return scoring.DIFFICULTY[question["difficulty"]] + SHIFT


def simulate(people: int, seed: int = 1) -> list[tuple[list[dict], dict]]:
    """Участники со способностью θ ~ N(0, 1) отвечают по той же модели, что заложена в оценку."""
    rng = Random(seed)
    sessions = []
    for person in range(people):
        theta = rng.gauss(0, 1)
        questions = build_test(seed * 1_000_000 + person)
        answers = {}
        for q in questions:
            guess = 1 / len(q["options"])
            p = guess + (1 - guess) / (1 + math.exp(-scoring.DISCRIMINATION * (theta - true_difficulty(q))))
            wrong = (q["correct"] + 1) % len(q["options"])
            answers[q["id"]] = q["correct"] if rng.random() < p else wrong
        sessions.append((questions, answers))
    return sessions


@pytest.fixture(scope="module")
def population():
    return simulate(3000)


@pytest.fixture(scope="module")
def calibrated(population):
    return calibrate.calibrate(calibrate.collect(population))


def test_pass_rate_and_difficulty_are_inverse():
    for guess in (1 / 4, 1 / 5, 1 / 6):
        for b in (-2.5, -1, 0, 1.3, 2.5):
            rate = calibrate.expected_pass_rate(b, guess)
            assert guess < rate < 1
            assert calibrate.difficulty_from_pass_rate(rate, guess) == pytest.approx(b, abs=0.01)
    assert calibrate.expected_pass_rate(-1, 0.2) > calibrate.expected_pass_rate(1, 0.2)  # труднее — решают реже


def test_every_question_has_a_kind_to_calibrate_by():
    kinds = {q["kind"] for seed in range(300) for q in build_test(seed)}
    assert all(k.count(":") == 2 for k in kinds)
    assert {k.split(":")[0] for k in kinds} == {"pattern", "num", "logic", "verbal"}
    assert len(kinds) >= 45  # матрицы и стрелки по уровням, 15 типов рядов, 14 логических шаблонов, 15 аналогий


def test_calibration_recovers_true_difficulty(calibrated):
    """Для часто встречающихся типов найденная сложность близка к настоящей."""
    frequent = {kind: row for kind, row in calibrated.items() if row["responses"] >= 800}
    assert len(frequent) >= 15
    error = {kind: abs(row["difficulty"] - (row["prior"] + SHIFT)) for kind, row in frequent.items()}
    assert sum(error.values()) / len(error) < 0.15
    # Задания верхнего уровня в этой модели решают почти так же редко, как угадывают, — доля решивших
    # почти не несёт информации о сложности, и оценка там шумная. Точность проверяем на остальных.
    assert max(e for kind, e in error.items() if frequent[kind]["prior"] < 2) < 0.45


def test_calibration_removes_the_bias_of_the_scale(population, calibrated):
    """До калибровки средний IQ занижен; после — возвращается к 100."""
    sample = population[:500]
    difficulties = {kind: row["difficulty"] for kind, row in calibrated.items()}
    before = sum(scoring.score(q, a)["iq"] for q, a in sample) / len(sample)
    after = sum(scoring.score(q, a, difficulties)["iq"] for q, a in sample) / len(sample)
    assert before < 94
    assert after == pytest.approx(100, abs=3)


def test_small_samples_keep_the_expert_estimate():
    few = simulate(20, seed=2)
    assert all(row["responses"] >= calibrate.MIN_RESPONSES for row in calibrate.calibrate(calibrate.collect(few)).values())

    stats = {"num:3:fib": {"total": 30, "correct": 3, "guess": 30 / 5, "prior": 0.0}}
    blended = calibrate.calibrate(stats)["num:3:fib"]["difficulty"]
    alone = calibrate.difficulty_from_pass_rate(0.1, 1 / 5)
    assert 0 < blended < alone  # сдвиг есть, но экспертная оценка его сдерживает


def test_uncalibrated_kinds_fall_back_to_expert_difficulty():
    questions = build_test(3)
    answers = {q["id"]: q["correct"] for q in questions[:15]}
    assert scoring.score(questions, answers, {}) == scoring.score(questions, answers)
    assert scoring.score(questions, answers, {"нет:такого:типа": 3.0}) == scoring.score(questions, answers)
    harder = {q["kind"]: scoring.DIFFICULTY[q["difficulty"]] + 1 for q in questions}
    assert scoring.score(questions, answers, harder)["iq"] > scoring.score(questions, answers)["iq"]


def test_sessions_without_kinds_are_ignored():
    legacy = [({k: v for k, v in q.items() if k != "kind"}) for q in build_test(4)]
    assert calibrate.collect([(legacy, {})]) == {}
