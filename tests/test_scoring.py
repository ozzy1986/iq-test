"""Модульные тесты подсчёта и правила доступа — без HTTP и базы."""
from datetime import timedelta

import pytest

from app import scoring
from app.main import has_access
from app.models import Subscription, now
from app.questions import CATEGORIES, QUESTIONS, public_questions


def answers(correct_ids):
    return {q["id"]: q["correct"] if q["id"] in correct_ids else (q["correct"] + 1) % 4 for q in QUESTIONS}


def test_question_bank_is_consistent():
    assert len(QUESTIONS) == 12
    for q in QUESTIONS:
        assert q["cat"] in CATEGORIES and q["difficulty"] in (1, 2, 3)
        assert len(q["options"]) == 4 and 0 <= q["correct"] < 4
        assert len({str(o) for o in q["options"]}) == 4, f"повторяющиеся варианты в {q['id']}"
    for key in CATEGORIES:
        assert sum(q["cat"] == key for q in QUESTIONS) == 3


def test_public_questions_hide_server_fields():
    for q in public_questions():
        assert set(q) <= {"id", "prompt", "series", "figure", "options", "category"}


def test_score_bounds_and_monotonicity():
    ids = [q["id"] for q in QUESTIONS]
    iqs = [scoring.score(answers(ids[:n]))["iq"] for n in range(len(ids) + 1)]
    assert iqs[0] == scoring.IQ_MIN and iqs[-1] == scoring.IQ_MAX
    assert iqs == sorted(iqs) and len(set(iqs)) == len(iqs)


def test_harder_questions_weigh_more():
    easy = next(q["id"] for q in QUESTIONS if q["difficulty"] == 1)
    hard = next(q["id"] for q in QUESTIONS if q["difficulty"] == 3)
    assert scoring.score(answers([hard]))["iq"] > scoring.score(answers([easy]))["iq"]


def test_missing_answers_count_as_wrong():
    result = scoring.score({})
    assert result["score_raw"] == 0 and result["percentile"] >= 1


@pytest.mark.parametrize("iq, title", [(72, "Ниже среднего"), (89, "Ниже среднего"), (90, "Средний"),
                                       (109, "Средний"), (110, "Выше среднего"), (120, "Высокий"),
                                       (130, "Очень высокий"), (140, "Очень высокий")])
def test_level_thresholds(iq, title):
    assert scoring.level_for(iq)["title"] == title


def test_percentile_matches_normal_distribution():
    result = scoring.score(answers([q["id"] for q in QUESTIONS]))
    assert result["percentile"] == 99
    assert scoring.score({})["percentile"] == 3  # IQ 72 ≈ −1.87σ


def test_insights_name_strength_and_growth_area():
    breakdown = scoring.score(answers([q["id"] for q in QUESTIONS if q["cat"] != "num"]))["breakdown"]
    texts = scoring.insights(breakdown, duration_sec=300)
    assert len(texts) == 3 and scoring.GROWTH["num"] in texts
    assert scoring.insights(breakdown, duration_sec=30)[-1].startswith("Вы отвечали очень быстро")


def test_access_follows_paid_period():
    def sub(status, days):
        return Subscription(session_id="x", plan="monthly", status=status, started_at=now(),
                            current_period_end=now() + timedelta(days=days))

    assert has_access(None) is False
    assert has_access(sub("active", 30)) is True
    assert has_access(sub("canceled", 5)) is True  # отменена, но период оплачен
    assert has_access(sub("active", -1)) is False  # период истёк
