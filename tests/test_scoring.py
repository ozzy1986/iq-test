"""Модульные тесты генератора, шкалы и правила доступа — без HTTP и базы."""
from datetime import timedelta
from random import Random

import pytest

from app import bank, scoring
from app.generator import BLUEPRINT, CATEGORIES, TOTAL, build_test, public_questions
from app.main import has_access
from app.models import Subscription, now

QUESTIONS = build_test(7)


def answers(correct_ids, questions=QUESTIONS):
    return {q["id"]: q["correct"] if q["id"] in correct_ids else (q["correct"] + 1) % len(q["options"])
            for q in questions}


@pytest.mark.parametrize("seed", range(200))
def test_generated_test_is_well_formed(seed):
    questions = build_test(seed)
    assert len(questions) == TOTAL == 30
    assert [q["difficulty"] for q in questions] == sorted(q["difficulty"] for q in questions)  # от простого к сложному
    for cat, difficulties in BLUEPRINT.items():
        assert sorted(q["difficulty"] for q in questions if q["cat"] == cat) == sorted(difficulties)
    for q in questions:
        options = [str(o) for o in q["options"]]
        assert len(set(options)) == len(options) >= 4, f"повторяющиеся варианты: {q}"
        assert 0 <= q["correct"] < len(options) and q["explain"]


def test_same_seed_same_test_and_different_seeds_differ():
    assert build_test(5) == build_test(5)
    assert len({str(build_test(s)) for s in range(50)}) == 50


def test_public_questions_hide_server_fields():
    for q in public_questions(QUESTIONS):
        assert set(q) <= {"id", "prompt", "series", "figure", "options", "category"}
        assert q["category"] in CATEGORIES.values()


@pytest.mark.parametrize("seed", range(100))
def test_number_series_has_exactly_one_right_option(seed):
    for q in build_test(seed):
        if "series" in q:
            right = q["options"][q["correct"]]["text"]
            assert q["explain"].endswith(f"Ответ: {right}.")
            assert [o["text"] for o in q["options"]].count(right) == 1


def test_matrix_answer_fits_the_row_pattern():
    """Форма и заливка в строке матрицы либо одинаковы, либо все разные — ответ это правило не нарушает."""
    for seed in range(100):
        for q in build_test(seed):
            if q.get("figure", {}).get("cols") == 3:
                cells = q["figure"]["cells"]
                answer = q["options"][q["correct"]]["fig"]
                for attr in ("shape", "fill"):
                    assert len({c[attr] for c in cells[6:8]} | {answer[attr]}) in (1, 3)


def test_bank_items_are_valid_for_every_difficulty():
    for seed in range(200):
        rng = Random(seed)
        for d in range(1, 6):
            for source in (bank.verbal, bank.logic):
                _, options, right, explain = source(rng, d)
                assert len(set(options)) == len(options) >= 4 and 0 <= right < len(options) and explain


def test_iq_grows_with_every_correct_answer():
    ids = [q["id"] for q in QUESTIONS]
    iqs = [scoring.score(QUESTIONS, answers(ids[:n]))["iq"] for n in range(len(ids) + 1)]
    assert iqs == sorted(iqs)
    assert iqs[0] < 70 and iqs[-1] >= 135


def test_scale_is_centred_like_a_standard_iq_scale():
    """Шкала девиационная: 100 ± 15. Решивший лёгкую половину заданий — около среднего."""
    ids = [q["id"] for q in QUESTIONS]
    middle = scoring.score(QUESTIONS, answers(ids[:17]))
    assert 92 <= middle["iq"] <= 108
    assert scoring.percentile_of(100) == 50 and scoring.percentile_of(115) == 84 and scoring.percentile_of(130) == 98


def test_a_missed_easy_question_costs_more_than_a_missed_hard_one():
    """Ошибка в простом задании говорит об уровне больше, чем ошибка в самом сложном."""
    ids = [q["id"] for q in QUESTIONS]
    without_easiest = scoring.score(QUESTIONS, answers(ids[1:]))["iq"]
    without_hardest = scoring.score(QUESTIONS, answers(ids[:-1]))["iq"]
    assert without_easiest <= without_hardest < scoring.score(QUESTIONS, answers(ids))["iq"]


def test_solving_only_hard_questions_looks_like_guessing():
    """Провалить все простые задания и «решить» сложные — модель считает это угадыванием."""
    hard = [q["id"] for q in QUESTIONS if q["difficulty"] >= 4][:8]
    assert scoring.score(QUESTIONS, answers(hard))["iq"] < 80


def test_guessing_does_not_produce_an_average_score():
    rng = Random(1)
    scores = [scoring.score(QUESTIONS, {q["id"]: rng.randrange(len(q["options"])) for q in QUESTIONS})["iq"]
              for _ in range(200)]
    assert sum(scores) / len(scores) < 75


def test_margin_reflects_measurement_error():
    result = scoring.score(QUESTIONS, answers([q["id"] for q in QUESTIONS][:15]))
    assert 4 <= result["margin"] <= 9


def test_missing_answers_count_as_wrong():
    assert scoring.score(QUESTIONS, {})["correct"] == 0


@pytest.mark.parametrize("iq, title", [(60, "Ниже среднего"), (89, "Ниже среднего"), (90, "Средний"),
                                       (109, "Средний"), (110, "Выше среднего"), (120, "Высокий"),
                                       (130, "Очень высокий"), (140, "Очень высокий")])
def test_level_thresholds(iq, title):
    assert scoring.level_for(iq)["title"] == title


def test_insights_name_strength_and_growth_area():
    breakdown = scoring.score(QUESTIONS, answers([q["id"] for q in QUESTIONS if q["cat"] != "num"]))["breakdown"]
    texts = scoring.insights(breakdown, duration_sec=600, total=30)
    assert len(texts) == 3 and scoring.GROWTH["num"] in texts
    assert scoring.insights(breakdown, duration_sec=60, total=30)[-1].startswith("Вы отвечали очень быстро")


def test_access_follows_paid_period():
    def sub(status, days):
        return Subscription(profile_id="x", plan="monthly", status=status, started_at=now(),
                            current_period_end=now() + timedelta(days=days))

    assert has_access(None) is False
    assert has_access(sub("active", 30)) is True
    assert has_access(sub("canceled", 5)) is True  # отменена, но период оплачен
    assert has_access(sub("active", -1)) is False  # период истёк
